# ARCHITECTURE.md — Fanthom

> Read when a task touches the data model, API, the processing pipeline, env vars or folder layout.
> Code rules are in `CLAUDE.md`. Feature specs are in `docs/FEATURES.md`.

## 1. Tech stack

**Monorepo:** `web/` (Next.js, UI only) + `api/` (FastAPI, all business logic) + Supabase (Postgres + Storage).

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 15 (App Router) + TypeScript strict** | Fast UI, deploys to Vercel |
| UI | **Tailwind CSS v4 + shadcn/ui** | Tokens from `docs/DESIGN.md` |
| Server state | **TanStack Query** | Caching, polling processing status, optimistic updates |
| API client | **openapi-typescript + openapi-fetch**, generated from FastAPI's `/openapi.json` | Frontend types always match the backend; no hand-written API types |
| Backend | **Python 3.12 + FastAPI** | Async, typed, auto OpenAPI docs |
| Validation | **Pydantic v2** (+ `pydantic-settings` for env) | Every request, response and LLM output is a Pydantic model |
| ORM / migrations | **SQLAlchemy 2.0 (async, asyncpg) + Alembic** | Typed models, versioned migrations |
| Database | **Supabase Postgres** | Managed Postgres, full-text search (`tsvector`) |
| File storage | **Supabase Storage** (private bucket `recordings`) via `supabase-py` | Signed upload/read URLs; files never pass through the API |
| Transcription | **Deepgram** pre-recorded API (`nova-3`, `diarize`, `utterances`, `smart_format`), `deepgram-sdk` | Speakers + timestamps in one call |
| LLM | **Anthropic Claude**, `anthropic` Python SDK (model from env `LLM_MODEL`) | Structured output, long context, streaming |
| Background work | **Postgres job queue** (`jobs` table, `SELECT … FOR UPDATE SKIP LOCKED`) + **worker process** (`python -m app.worker`) | Durable: survives crashes and deploys, retries with backoff, scales by adding workers; no extra infrastructure |
| Rate limiting | **slowapi** (per IP now, per user after F8) | Protects LLM/transcription spend and the API |
| Errors & tracing | Structured JSON logs with `request_id` + `meeting_id`; **Sentry** (optional, if DSN set) | Find any failure from one log line |
| Streaming | Server-Sent Events (`StreamingResponse`, `text/event-stream`) | Ask AI token streaming |
| Backend tooling | **uv** (deps), **ruff** (lint + format), **mypy** (types), **pytest + pytest-asyncio + httpx** | |
| Frontend tests | **Vitest** (unit) + **Playwright** (smoke) | |
| Auth (F8) | **Supabase Auth** in the browser; FastAPI verifies the Supabase JWT | |
| CI | GitHub Actions: backend + frontend checks on every push | |
| Deploy | `web/` → **Vercel** (root dir `web`); `api/` → **Railway**, two services from the same Dockerfile: **api** (uvicorn) and **worker** | Always-on: streaming works, jobs run, no cold start for reviewers |

## 2. System flow

```
Browser (web/, Vercel)
  │  1. POST {API}/api/meetings              → API creates meeting row, returns signed upload URL
  │  2. upload file DIRECTLY to Supabase Storage with that URL (progress bar)
  │  3. POST {API}/api/meetings/:id/uploaded → API verifies object, starts processing
  │  4. GET  {API}/api/meetings/:id/status   (TanStack Query polls every 3s until ready | failed)
  ▼
FastAPI (api/, Railway)
  ├── enqueues jobs → jobs table (Postgres)
  ├── Deepgram callback → POST /api/webhooks/deepgram → enqueue `ingest_transcript`
  └── Claude   Ask AI, streamed over SSE, cites segment idx (runs in the API, not a job)
  ▼
Worker (api/, Railway, same image, `python -m app.worker`)
  ├── `transcribe`         → send media to Deepgram (callback mode) 
  ├── `ingest_transcript`  → save speakers + segments → status = summarizing → enqueue `summarize`
  └── `summarize`          → Claude summary + action items (JSON → Pydantic) → status = ready
  ▼
Supabase Postgres + Storage
```

**Status machine** (`meetings.status`, enforced in `app/services/meetings/status.py`):
`uploading → uploaded → transcribing → summarizing → ready`; any step → `failed` (`error_code`, `error_message`). A failed **summary** does not fail the meeting; it shows on the summary panel and the meeting becomes `ready`.

Local dev can't receive Deepgram callbacks → `DEEPGRAM_MODE=sync` calls Deepgram synchronously (dev only).
CORS: the API allows only `WEB_URL`.

## 3. Data model (`api/app/db/models.py`, migrations in `api/alembic/`)

```
meetings
  id uuid pk | title text | source enum(upload,url,seed)
  status enum(uploading,uploaded,transcribing,summarizing,ready,failed)
  media_path text null | media_url text null | media_kind enum(audio,video)
  duration_ms int null | language text null | deepgram_request_id text null
  error_code text null | error_message text null
  share_token text unique null | owner_id uuid null (F8)
  recorded_at timestamptz null | created_at | updated_at

speakers
  id uuid pk | meeting_id fk | label text ("Speaker 0") | display_name text null
  color_index int (0–7) | talk_time_ms int

segments            -- one row per utterance
  id uuid pk | meeting_id fk | speaker_id fk | idx int
  start_ms int | end_ms int | text text | confidence real
  search tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED + GIN index
  unique(meeting_id, idx)

summaries
  id uuid pk | meeting_id fk | template enum(general,sales,standup,interview)
  content jsonb  -- { sections: [{ heading, bullets: [{ text, refs: number[] }] }] }
  status enum(generating,ready,failed) | error_code text null
  model text | prompt_version text | created_at
  unique(meeting_id, template)

action_items
  id uuid pk | meeting_id fk | text | owner_speaker_id fk null
  due_hint text null | done bool default false | ref_idx int

chat_messages
  id uuid pk | meeting_id fk | role enum(user,assistant) | content text
  refs int[] | stopped bool default false | created_at

highlights (F7)
  id uuid pk | meeting_id fk | start_ms | end_ms | note text null | created_at

jobs
  id uuid pk | kind enum(transcribe,ingest_transcript,summarize) | payload jsonb
  status enum(queued,running,done,failed) | attempts int default 0 | max_attempts int default 3
  run_after timestamptz default now() | locked_until timestamptz null | last_error text null
  dedupe_key text unique null      -- e.g. "summarize:<meeting_id>:general" → no duplicate jobs
  created_at | updated_at
  index (status, run_after)
```
All child tables: `ON DELETE CASCADE` from `meetings`. Times are integer **milliseconds**.
The `tsvector` column and GIN index are added with raw SQL in the Alembic migration.

**Job queue contract** (`app/services/jobs.py`, `app/worker.py`):
- `enqueue(kind, payload, dedupe_key)` inserts a job; a duplicate `dedupe_key` that is still queued/running is ignored.
- Worker loop: claim one job with `UPDATE … WHERE id = (SELECT id FROM jobs WHERE status='queued' AND run_after <= now() ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`, set `status=running`, `locked_until = now() + 5 min`.
- Success → `done`. Failure → `attempts += 1`; if `attempts < max_attempts` → back to `queued` with `run_after = now() + 2^attempts * 10s`; else `failed` and the meeting gets the matching error code.
- A job whose `locked_until` passed (worker crashed) is reclaimed by the next worker.
- Every job handler is **idempotent** (safe to run twice). Worker stops gracefully on SIGTERM (finishes the current job).
- `WORKER_CONCURRENCY` (default 2) jobs run in parallel per worker process.

**Citation contract:** the LLM sees segments only as `[#idx] (mm:ss) Speaker: text` and returns `refs: list[int]`. The API drops any ref not in this meeting before saving or returning it (`app/services/llm/refs.py`). The frontend re-checks before rendering a chip.

## 4. API (FastAPI routers, all under `/api`)

All list endpoints are paginated (`limit` ≤ 50, cursor = `created_at,id`). Every response carries an `X-Request-ID` header.

| Method | Route | Router | Feature |
|---|---|---|---|
| GET | `/api/health` | health | F0 |
| GET | `/api/meetings` · `/api/meetings/{id}` | meetings | F0, F3 |
| POST | `/api/meetings` | meetings | F1 |
| POST | `/api/meetings/{id}/uploaded` | meetings | F1 |
| PATCH / DELETE | `/api/meetings/{id}` | meetings | F1, F3, F6 |
| POST | `/api/meetings/{id}/process` | meetings | F2 |
| GET | `/api/meetings/{id}/status` | meetings | F2 |
| POST | `/api/webhooks/deepgram` | webhooks | F2 |
| PATCH | `/api/speakers/{id}` | speakers | F3 |
| POST | `/api/meetings/{id}/summary` | summaries | F4 |
| PATCH | `/api/action-items/{id}` | summaries | F4 |
| GET / POST / DELETE | `/api/meetings/{id}/chat` (POST streams SSE) | chat | F5 |
| GET | `/api/search?q=` | search | F6 |
| POST / DELETE | `/api/meetings/{id}/share` · `/highlights` | sharing | F7 |
| GET | `/api/share/{token}` | sharing | F7 |

Success: the Pydantic response model. Failure: `{ "error": { "code": "...", "message": "..." } }` with the right HTTP status (one exception handler in `app/core/errors.py`).
After any API change: `make gen-api` regenerates `web/lib/api/schema.d.ts`.

## 5. Folder structure

```
fanthom/
├── CLAUDE.md  Makefile  .github/workflows/ci.yml  .claude/settings.json
├── docs/      ARCHITECTURE.md DESIGN.md FEATURES.md DECISIONS.md PLAYBOOK.md BRIEF.md
├── openspec/  (managed by OpenSpec)
├── api/
│   ├── pyproject.toml  uv.lock  Dockerfile  .env.example
│   ├── alembic/        env.py, versions/
│   ├── app/
│   │   ├── main.py                 app factory, CORS, rate limits, request-id middleware, routers, exception handlers
│   │   ├── worker.py               job worker entrypoint (python -m app.worker)
│   │   ├── core/                   config.py (settings) errors.py logging.py time.py
│   │   ├── db/                     session.py models.py
│   │   ├── schemas/                Pydantic request/response models per resource
│   │   ├── routers/                health meetings speakers summaries chat search webhooks sharing
│   │   └── services/
│   │       ├── jobs.py storage.py deepgram.py transcription.py
│   │       ├── meetings/           status.py queries.py
│   │       └── llm/                client.py prompts.py summary.py chat.py refs.py
│   ├── scripts/        seed.py export_seed.py
│   ├── seed/           *.json (processed demo meetings) + media manifest
│   └── tests/          unit/ (pure logic) api/ (endpoint tests with httpx) fixtures/
└── web/
    ├── package.json  .env.example
    ├── app/            (marketing)/  (app)/meetings/...  s/[token]/
    ├── components/     ui/ (shadcn) brand/ meeting/ dashboard/
    ├── lib/            api/ (client.ts, schema.d.ts generated) time.ts player-store.ts
    └── tests/          unit/ e2e/
```

**Layering (backend):** routers are thin (parse → call service → return schema). Services hold the logic. Only services talk to Deepgram, Claude, Storage and the DB. Pure functions (mappers, validators, status machine, refs, time) have no I/O so they're unit-tested without mocks.

## 6. Environment variables

`api/.env`
```
DATABASE_URL=postgresql+asyncpg://...   # Supabase "Session pooler" string, scheme changed to postgresql+asyncpg
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
STORAGE_BUCKET=recordings
DEEPGRAM_API_KEY=
DEEPGRAM_MODE=callback                  # callback | sync (sync = local dev only)
DEEPGRAM_CALLBACK_SECRET=
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-5-5
API_URL=http://localhost:8000           # public URL Deepgram calls back to
WEB_URL=http://localhost:3000           # allowed CORS origin
MAX_UPLOAD_MB=50                        # Supabase free-tier per-file limit
WORKER_CONCURRENCY=2
DB_POOL_SIZE=10
RATE_LIMIT_CHAT=20/minute
RATE_LIMIT_SUMMARY=10/minute
SENTRY_DSN=                             # optional
```

`web/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```
Settings are validated at boot (`app/core/config.py` with pydantic-settings). Secret keys live only in `api/.env` and Railway, never in `web/`.

## 7. Commands (root `Makefile`)

| Command | Does |
|---|---|
| `make dev-api` | `uv run fastapi dev app/main.py` (port 8000) |
| `make dev-web` | `pnpm dev` (port 3000) |
| `make dev-worker` | `uv run python -m app.worker` |
| `make check` | **Check gate**: backend (ruff, mypy, pytest) + frontend (typecheck, lint, vitest) |
| `make migrate` | `alembic upgrade head` |
| `make migration m="msg"` | `alembic revision --autogenerate -m "msg"` |
| `make seed` / `make export-seed` | load / export demo meetings |
| `make gen-api` | regenerate frontend API types from `{API}/openapi.json` |
| `make e2e` | Playwright smoke tests |

## 8. Reliability and scale

### Built into this version
| Concern | How it's handled |
|---|---|
| Big files | Browser uploads straight to Storage with signed URLs; the API never holds file bytes |
| Slow work (transcription, summaries) | Durable Postgres job queue + separate worker; API stays fast |
| Crashes / deploys mid-job | Job lease (`locked_until`) expires → another worker picks it up; handlers are idempotent |
| Duplicate work | `dedupe_key` on jobs; webhook idempotency via `deepgram_request_id`; unique constraints on segments/summaries |
| Provider failures | Timeouts, retries with exponential backoff, max attempts, clear error codes per meeting |
| Bad AI output | Pydantic validation + one repair retry; citations checked against real segment ids |
| Abuse and cost | Per-IP rate limits on chat/summary/upload; max upload size; max chat message length; LLM `max_tokens` caps |
| Database load | Indexed foreign keys, `(meeting_id, idx)` unique index, GIN index for search, paginated lists, connection pool limits |
| Observability | Request id on every request, structured logs with `meeting_id`/`job_id`, `/api/health`, optional Sentry |
| Security | Secrets only on the server, CORS locked to the web origin, webhook secret check, signed URLs expire, private bucket |

### Path to millions of users (what changes, in order)
1. **Horizontal scale:** the API is stateless → run N API instances behind a load balancer; run M workers and scale them on queue depth (`SELECT count(*) FROM jobs WHERE status='queued'`).
2. **Database:** add PgBouncer (transaction pooling) and a read replica for dashboards/search; partition `segments` by `created_at` month once it reaches hundreds of millions of rows.
3. **Queue:** move from the Postgres queue to a managed queue (SQS / Redis Streams) when job throughput exceeds a few hundred per second; the `jobs.py` interface stays the same.
4. **Search:** move cross-meeting search to a dedicated engine (OpenSearch / Typesense, or pgvector for semantic search) fed by an `ingest_transcript` hook.
5. **Media:** serve recordings through a CDN with signed URLs; transcode long videos to audio-only for transcription to cut cost.
6. **Provider limits:** per-worker concurrency caps and a token bucket per provider (Deepgram, Anthropic) so bursts queue instead of failing; negotiate higher rate limits.
7. **Multi-tenant safety:** per-user and per-workspace quotas, row-level ownership checks everywhere (F8), audit log for shares.
