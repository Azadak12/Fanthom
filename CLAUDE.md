# CLAUDE.md — Fanthom

Fanthom is a rebuild of **Fathom (fathom.video)**, the AI meeting notetaker: recording → speaker-labeled transcript → AI summary + action items where **every point links to the exact moment it was said** → cited Q&A about the meeting.
Promise: _"Meeting notes that show their receipts."_ Built for the 8x Product Engineer assignment: reviewers judge the live product, the code + git history, and the process.

## Read on demand (don't load all at once)
- `docs/FEATURES.md` → read **only the section for the current feature** (F0–F8).
- `docs/ARCHITECTURE.md` → stack, data model, API routes, folders, env, commands. Read when a task touches these.
- `docs/DESIGN.md` → read before building or changing UI.
- `docs/DECISIONS.md` → append a line when scope, stack or design changes.

## Stack (details in ARCHITECTURE.md)
Monorepo. `web/`: Next.js 16 App Router · TypeScript strict · Tailwind v4 + shadcn/ui · TanStack Query · typed client generated from the API's OpenAPI.
`api/`: Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 async + Alembic · Deepgram · Anthropic SDK · uv · ruff · mypy · pytest.
Data: Supabase Postgres + Storage. Background work: Postgres job queue + worker. Deploy: web → Vercel, api + worker → Railway.
Don't add a dependency without a line in `docs/DECISIONS.md`.

## Commands
`make dev-api` · `make dev-web` · `make dev-worker` · `make migrate` · `make migration m="..."` · `make seed` · `make gen-api` · `make e2e`
**Check gate** (run after every task group): `make check`

## Backend rules (`api/`)
- All business logic lives in `app/services/`. Routers only parse input, call a service, return a Pydantic schema.
- Type hints everywhere; mypy must pass. No bare `except`. Async all the way (async SQLAlchemy session, async httpx/SDK clients).
- Errors: raise `AppError(code, message, status)` from `app/core/errors.py`; one exception handler returns `{"error": {"code", "message"}}`. Codes: `VALIDATION NOT_FOUND FILE_TOO_LARGE UNSUPPORTED_FORMAT UPLOAD_FAILED TRANSCRIPTION_FAILED NO_SPEECH LLM_FAILED LLM_BAD_OUTPUT RATE_LIMITED UNAUTHORIZED CONFLICT`.
- Slow or external work (transcription, ingest, summaries) runs as a **job** via `app/services/jobs.py` and the worker, never inside a request and never with FastAPI `BackgroundTasks`. Every job handler is idempotent.
- Every external call (Deepgram, Claude, Storage): timeout + 1 retry on 5xx/429 with backoff + structured log with `request_id`/`job_id` and `meeting_id`.
- List endpoints are paginated (max 50). Expensive endpoints (upload, summary, chat) are rate-limited.
- LLM output is untrusted: parse into a Pydantic model → on `ValidationError` retry once with the error appended → else `LLM_BAD_OUTPUT`. Citations go through `app/services/llm/refs.py`.
- Schema changes only via Alembic migrations. Never edit an applied migration.
- Pure logic (mappers, validators, status machine, refs, time) gets pytest unit tests **written before** the implementation.

## Frontend rules (`web/`)
- No `any`. Server Components by default; `"use client"` only for interactive parts (player, transcript, chat, forms).
- Call the API only through `lib/api/client.ts` (generated types). Never hand-write API types; run `make gen-api` after API changes.
- Server state in TanStack Query; player state in `lib/player-store.ts`.
- UI uses tokens from `DESIGN.md` only (no hex in components). Every list/panel has loading, empty and error states.
- The frontend holds no secrets: only `NEXT_PUBLIC_*` values.

## Shared rules
- Time is integer milliseconds everywhere; format only in the UI (`web/lib/time.ts`).
- Make the smallest change that satisfies the task. Don't refactor unrelated code. Don't build anything not in `docs/FEATURES.md`.

## How to work
- One feature = one OpenSpec change named `fNN-name` (e.g. `f02-transcription`). Copy that feature's requirements, edge cases, error handling and design from `docs/FEATURES.md` into the proposal's specs (as scenarios), `design.md` and `tasks.md`.
- Never start `/openspec-apply-change` on a proposal the human hasn't approved.
- Work through `tasks.md` in order: backend first (schema → service → router → tests), then `make gen-api`, then frontend.
- After each task group: run `make check`, fix failures, then stop and summarize what changed (files + why) so the human can commit.
- If a requirement is unclear or conflicts with the code, ask; don't guess.
- If a fix fails twice, stop and explain the root cause instead of trying a third variation.
- Commits: conventional style, e.g. `feat(f02): store diarized segments`, `fix(f04): drop invalid citation refs`.

## Definition of done (per feature)
Acceptance criteria in FEATURES.md pass · listed edge cases handled or written as known limitations · loading/empty/error states exist · `make check` green · works on the deployed URLs (Vercel + Railway) · OpenSpec change archived.

## Never
- Build auth before F0–F4 work end to end. The demo must open into a seeded workspace with no sign-in.
- Send a file through the API; the browser uploads to Storage with a signed URL.
- Show an AI sentence without its citation chip.
- Put a secret key in `web/` or in a `NEXT_PUBLIC_*` variable.
- Copy Fathom's logo, name or assets.
- Disable a test, a lint rule or a type check to make the gate pass.

# Compact instructions
When compacting, keep: current feature id and change name, tasks done/remaining, files changed, failing checks and their errors, decisions made. Drop: file contents already written, full test logs.
