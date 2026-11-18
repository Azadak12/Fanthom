# FEATURES.md — Fanthom Feature Specs (Action List)

> Build **in order**, one feature = one OpenSpec change (`/opsx:propose fNN-name`).
> Each feature has: Goal · Requirements · Acceptance criteria · System design · Edge cases · Error handling · Tasks.
> Error codes refer to `api/app/core/errors.py` (see `CLAUDE.md` → Backend rules). Design rules: `docs/DESIGN.md`.

## Roadmap (build in this order)

| # | Change name | Priority |
|---|---|---|
| — | Read brief, explore, finalize these docs | — |
| F0 | `f00-foundation` | P0 |
| F1 | `f01-add-meeting` | P0 |
| F2 | `f02-transcription` | P0 |
| F3 | `f03-meeting-page` | P0 |
| F4 | `f04-summary-actions` | P0 |
| F5 | `f05-ask-ai` | P1 |
| F6 | `f06-dashboard-search` | P1 |
| F7 | `f07-highlights-share` | P2 |
| F8 | `f08-auth` | P2 |
| — | Polish, README, intro video, walkthrough, submit | — |

**Rule:** P0 features must work end to end on the live URL before any P1/P2 work starts. If a feature grows beyond its spec, cut its P2 parts and write the cut down in `docs/DECISIONS.md`.

---

## F0 — Foundation (`f00-foundation`)

**Goal:** both apps deployed and talking to each other, the full data model migrated, and a seeded demo workspace, so every later feature plugs in.

### Requirements
- R0.1 Monorepo per `docs/ARCHITECTURE.md` §5: `api/` (FastAPI, uv, ruff, mypy, pytest) and `web/` (Next.js 15, TS strict, Tailwind v4, shadcn/ui, TanStack Query); root `Makefile` with the commands in ARCHITECTURE §7.
- R0.2 SQLAlchemy models for all tables in ARCHITECTURE §3; first Alembic migration (incl. `tsvector` column + GIN index) applied to Supabase.
- R0.3a Job queue: `jobs` table + `app/services/jobs.py` (enqueue with dedupe, claim with `SKIP LOCKED`, retry with backoff, lease reclaim) + `app/worker.py` (concurrency, graceful SIGTERM). Contract in ARCHITECTURE §3.
- R0.3b Request-id middleware, structured JSON logging, slowapi rate limiter wired (limits applied per feature), pagination helper.
- R0.3 Supabase Storage bucket `recordings` (private); `app/services/storage.py` with signed upload URL, signed read URL, exists/size check, delete.
- R0.4 `app/core/config.py` (pydantic-settings), `app/core/errors.py` (`AppError` + exception handler), `app/core/logging.py`, `app/services/meetings/status.py` (allowed transitions), `web/lib/time.ts` (`formatMs`, `parseTimestamp`); pure parts unit-tested.
- R0.5 Seed script loads **2–3 real demo meetings** (media file + transcript + speakers + summary JSON) so the demo works even if Deepgram/Claude are down. In F0 it seeds the media and meeting rows; transcripts and summaries are filled in after F4 (see F4 last task).
- R0.6 `GET /api/meetings`, `GET /api/meetings/{id}`, `GET /api/health` (DB + storage status). CORS allows only `WEB_URL`.
- R0.7 `web/`: typed API client generated from `/openapi.json` (`make gen-api`); app shell (sidebar, header); landing page with "Open demo workspace" CTA; dashboard lists meetings from the API.
- R0.8 Deploy: `api/` to Railway (Dockerfile), `web/` to Vercel (root dir `web`); env vars set on both; CI green.

### Acceptance criteria
- Deployed web URL → landing → "Open demo" → dashboard lists the seeded meetings (no login), data coming from the deployed API.
- `{API_URL}/docs` shows the OpenAPI docs; `/api/health` returns `{ db: "ok", storage: "ok" }`.
- `make check` passes locally and in CI.
- `status.py` rejects illegal transitions (e.g. `ready → transcribing`) in tests.
- Job queue tests: a failing job retries with backoff then ends `failed`; two workers never claim the same job; an expired lease is reclaimed; a duplicate `dedupe_key` is ignored.

### System design
- `app/main.py`: app factory → CORS middleware → exception handlers → include routers under `/api`.
- `app/db/session.py`: async engine (asyncpg) + `get_session` dependency; models in `app/db/models.py`; `alembic/env.py` uses the async engine and `models.Base.metadata`.
- `scripts/seed.py`: idempotent (upsert by fixed UUIDs), uploads media to `recordings/seed/<id>.<ext>`; run with `make seed`.
- Demo meetings: 2–3 mock calls (10–20 min, 3–6 people) recorded with friends. After F4 works, run them through the real pipeline and export the results to `api/seed/*.json` with `make export-seed`. **Do not use copyrighted recordings.**
- `web/lib/api/client.ts`: `openapi-fetch` client with base URL `NEXT_PUBLIC_API_URL`; errors normalized to `{ code, message }`.
- `api/Dockerfile`: python:3.12-slim + uv. Railway runs two services from it: **api** (`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`) and **worker** (`python -m app.worker`).

### Edge cases
- Seed run twice → no duplicates (upsert).
- Missing env var at boot → API refuses to start with an error naming the variable (pydantic-settings).
- Supabase unreachable → `/api/health` reports `db: "down"` with 503; web shows an error state, not a crash.
- Web calls API from a non-allowed origin → blocked by CORS (tested).
- API down or cold → web shows a friendly "Can't reach the server, retrying…" state (TanStack Query retry with backoff).

### Error handling
- One FastAPI exception handler maps `AppError` → `{ "error": { code, message } }`, `RequestValidationError` → 422 `VALIDATION`, anything else → 500 `INTERNAL` (logged with request id, no stack trace to the client).
- `web/app/error.tsx` and `web/app/not-found.tsx` styled per DESIGN §8.

### Tasks
- [ ] Monorepo scaffold: `api/` (uv project, ruff, mypy, pytest config) + `web/` (Next.js, shadcn init, fonts, tokens) + root Makefile
- [ ] `config.py`, `errors.py` + handler, `logging.py` + tests
- [ ] SQLAlchemy models + Alembic async setup + first migration (with tsvector + GIN)
- [ ] `status.py` + tests (written first)
- [ ] Job queue (`jobs` model, `jobs.py`, `worker.py`) + tests (written first)
- [ ] Request-id middleware, JSON logging, rate limiter, pagination helper
- [ ] `storage.py` (signed upload/read URLs, exists, delete)
- [ ] `GET /api/health`, `GET /api/meetings`, `GET /api/meetings/{id}` + API tests
- [ ] `make gen-api` + `web/lib/api/client.ts`; `web/lib/time.ts` + tests
- [ ] App shell + landing + dashboard reading from the API (loading/empty/error states)
- [ ] Seed script (idempotent) + demo media
- [ ] Dockerfile, Railway (api + worker services) + Vercel deploy, CI, smoke-check live URLs

---

## F1 — Add a meeting (`f01-add-meeting`)

**Goal:** a user adds a recording by uploading a file **or** pasting a public media URL, and lands on a processing view.

### Requirements
- R1.1 `/meetings/new` with a dropzone (DESIGN §7) and a "Import from URL" tab.
- R1.2 Accepted: audio `mp3, m4a, wav, webm, ogg`; video `mp4, mov, webm`. Max size `MAX_UPLOAD_MB`.
- R1.3 Title field, pre-filled from the file name (without extension), editable, 1–120 chars.
- R1.4 File goes **directly from browser to Supabase Storage** via a signed upload URL, with a progress bar and a cancel button.
- R1.5 After upload, auto-start processing (calls F2) and redirect to `/meetings/:id` showing the processing card.
- R1.6 URL import: validate `https://`, then skip upload and hand the URL to F2.

### Acceptance criteria
- Uploading a 20 MB mp3 shows progress, then redirects to the meeting page with status `Transcribing`.
- A 200 MB file or a `.pdf` is rejected **before** upload with a clear message.
- Cancelling mid-upload deletes the pending meeting row and the partial object.

### System design
```
POST /api/meetings
  body (Pydantic, discriminated on source):
        { title, source: "upload", file_name, mime_type, size_bytes } | { title, source: "url", url }
  → validate (type allow-list, size ≤ MAX_UPLOAD_MB, url https)
  → insert meetings(status = uploading | uploaded for url)
  → upload: storage.create_signed_upload_url(f"{id}/{safe_name}")
  ← { meeting_id, upload_url?, token? }

Browser → uploads the file to the signed URL (XHR for progress events)

POST /api/meetings/{id}/uploaded   → verify object exists + size → status uploading → uploaded
                                   → triggers POST /api/meetings/{id}/process (F2)
DELETE /api/meetings/{id}          → cancel: delete row + storage object
```
- `media_kind` from MIME type; `safeName` = slugified file name.

### Edge cases
- File type spoofed (`.mp3` that's really a PDF): client checks MIME + extension; server re-checks MIME on `uploaded`; Deepgram failure in F2 is the final guard (`UNSUPPORTED_FORMAT`).
- 0-byte file → reject (`VALIDATION`).
- User closes the tab mid-upload → meeting stays `uploading`; a meeting stuck in `uploading` > 30 min is shown as `Failed — upload incomplete` with a delete action (check on read, no cron needed).
- Double-click on upload → button disabled while a request is in flight; server is fine with duplicates (separate meetings), so prevent on the client.
- Very long file name / emoji / spaces → slugified storage path; original name kept as title.
- URL is not publicly reachable or is an HTML page (e.g. YouTube link) → F2 fails with `UNSUPPORTED_FORMAT` and the message _"This link isn't a direct audio/video file."_
- Network drops mid-upload → show "Upload interrupted" with Retry (new signed URL).

### Error handling
| Case | Code | User message |
|---|---|---|
| Wrong type | `UNSUPPORTED_FORMAT` | "This file type isn't supported. Use MP3, M4A, WAV, MP4, MOV or WEBM." |
| Too large | `FILE_TOO_LARGE` | "Files can be up to {MAX} MB. Try an audio-only export." |
| Upload failed | `UPLOAD_FAILED` | "Upload didn't finish. Check your connection and retry." |
| Bad URL | `VALIDATION` | "Paste a direct https link to an audio or video file." |

### Tasks
- [ ] Pydantic request schemas + `POST /api/meetings` + API tests for validation
- [ ] Signed upload URL helper; `POST /{id}/uploaded`; `DELETE /{id}`
- [ ] Dropzone + URL tab + title field + progress + cancel
- [ ] Redirect to meeting page with processing card (placeholder until F2)
- [ ] Stale-upload detection on read

---

## F2 — Transcription pipeline (`f02-transcription`)

**Goal:** turn a recording into speakers + timestamped segments, reliably, and move the meeting through the status machine.

### Requirements
- R2.1 `POST /api/meetings/{id}/process` sends the media to Deepgram (`nova-3`, `diarize=true`, `utterances=true`, `smart_format=true`, `punctuate=true`, `detect_language=true`).
- R2.2 Media is passed as a **signed read URL** (valid 1h) or the imported URL.
- R2.3 Callback mode in prod (`/api/webhooks/deepgram?meetingId=…&secret=…`), sync mode in local dev.
- R2.4 Store: `speakers` (one per diarized speaker, `label = "Speaker N"`, `color_index = N % 8`, `talk_time_ms`), `segments` (one per utterance), `meetings.duration_ms`, `language`.
- R2.5 Then set status `summarizing` and enqueue a `summarize` job (F4).
- R2.6 Meeting page polls `/api/meetings/{id}/status` every 3s while processing and shows the current step.
- R2.7 "Retry" button on failed meetings restarts from the failed step.

### Acceptance criteria
- A 15-min 3-person recording reaches `summarizing` with 3 speakers and correctly ordered segments.
- Segments' `start_ms` are strictly non-decreasing by `idx`; no empty-text segments saved.
- Sending the same webhook twice does not duplicate segments.
- A silent file ends in `failed` with `NO_SPEECH`.

### System design
```
process(id):
  assert status in (uploaded, failed[step=transcribe])  → else 409
  set status = transcribing
  mode=callback → Deepgram transcribe_url(url, options, callback=API_URL + webhook path)
  mode=sync     → await result → handle_transcript(id, result)

POST /api/webhooks/deepgram
  verify secret (constant-time compare) → 401 if wrong
  store raw payload reference → enqueue job ingest_transcript(meeting_id, request_id) → return 200 immediately

ingest_transcript job (id, dg):     (one DB transaction, idempotent)
  if meeting.status != transcribing → ignore (idempotency)
  utterances = dg.results.utterances
  if none or all empty → fail(NO_SPEECH)
  delete existing speakers/segments for id   (safe re-run)
  insert speakers (distinct dg speaker ids, sorted by first appearance)
  insert segments (idx, start_ms = round(start*1000), end_ms, text.trim(), confidence)
  talk_time_ms = Σ(end-start) per speaker
  update meeting duration_ms, language, status = summarizing
  enqueue summarize(id, "general") with dedupe_key "summarize:<id>:general"   # F4
```
- Mapping lives in `app/services/deepgram.py` (`map_utterances(dg) → (speakers, segments)`), pure and unit-tested with a saved Deepgram JSON fixture in `tests/fixtures/`.

### Edge cases
- Single speaker → 1 speaker row; timeline still renders one lane.
- 9+ speakers → colors repeat (DESIGN §3), names still unique ("Speaker 8").
- Diarization flips the same person into two speakers → allowed; F3 lets the user rename/merge (rename only in MVP; merge = stretch).
- Overlapping speech (utterances overlap in time) → keep both, order by `start_ms` then speaker.
- Non-English audio → store detected `language`; summary prompt answers in that language (F4).
- Very long meeting (>2h) → Deepgram handles it; F4 switches to chunked summarization.
- Webhook arrives after the user hit Retry → status check ignores stale callbacks (store `deepgram_request_id` on the meeting and compare).
- Webhook never arrives → if `transcribing` > 15 min, show "Taking longer than usual" + Retry.
- Signed URL expires before Deepgram fetches it → Deepgram error → `TRANSCRIPTION_FAILED`, Retry generates a fresh URL.
- Worker crashes mid-ingest → transaction rolls back, lease expires, job re-runs (idempotent: deletes and re-inserts segments).
- Job fails 3 times → job `failed`, meeting `failed` with the job's error code; Retry enqueues a fresh job.

### Error handling
| Case | Code | Status → | User message |
|---|---|---|---|
| Deepgram 4xx bad media | `UNSUPPORTED_FORMAT` | failed | "We couldn't read this file's audio." |
| Deepgram 5xx / timeout (after 1 retry) | `TRANSCRIPTION_FAILED` | failed | "Transcription service had a problem. Retry in a minute." |
| 429 | `RATE_LIMITED` | stays transcribing, retry with backoff (max 3) | — |
| No speech | `NO_SPEECH` | failed | "We couldn't hear anyone speaking in this file." |
| Bad webhook secret | `UNAUTHORIZED` | unchanged | (401, logged) |

### Tasks
- [ ] `map_utterances` + fixture tests (written first), then Deepgram client in `services/deepgram.py`
- [ ] `POST /{id}/process` (callback + sync modes), store request id
- [ ] `transcribe` + `ingest_transcript` job handlers (idempotent) + tests; webhook router with secret check (`hmac.compare_digest`) that only enqueues
- [ ] `GET /{id}/status` + `make gen-api` + processing card with steps (TanStack Query polling)
- [ ] Retry action + stale-processing detection

---

## F3 — Meeting page (`f03-meeting-page`)

**Goal:** watch/listen to the meeting with a transcript and speaker timeline that are always in sync. This is where reviewers spend the most time, so polish it.

### Requirements
- R3.1 Layout per DESIGN §6. Header: title (inline editable), date, duration, speaker count, Share (F7).
- R3.2 Player: `<video>` for video, `<audio>` + simple waveform/progress bar for audio. Signed read URL refreshed on expiry.
- R3.3 Transcript: segments grouped per speaker turn; active segment highlighted and auto-scrolled into view while playing (toggle "Follow along" on by default; turns off when the user scrolls manually; "Jump to now" button brings it back).
- R3.4 Click a segment timestamp → seek + play.
- R3.5 Speaker timeline: one lane per speaker with talk-time %; click = seek; click a name = filter the transcript to that speaker.
- R3.6 Rename speaker (inline) → updates everywhere (transcript, timeline, summary owner pills, action items).
- R3.7 Search in transcript (`/` shortcut): highlights matches, "3 of 12" with up/down.
- R3.8 Keyboard shortcuts per DESIGN §10.
- R3.9 Global player state in one client store (`useMeetingPlayer`: `currentMs`, `seek(ms)`, `playing`) so any component (chips in F4/F5) can seek.

### Acceptance criteria
- Clicking a segment at 11:40 starts playback at 11:40 ± 0.3s and highlights that segment.
- During playback the highlighted segment changes within 300ms of the speaker change.
- Renaming "Speaker 2" → "Sara" updates all places without reload, and persists after reload.
- A 1-hour meeting (~1,000 segments) scrolls smoothly (virtualize the list if > 400 segments).

### System design
- `GET /api/meetings/{id}` returns meeting + speakers + segments (+ summary, action items for F4) in one response (one query with `selectinload`). The page fetches it server-side for first paint, then hydrates TanStack Query.
- Active segment: binary search on `start_ms` with `currentMs` from `timeupdate` (throttle with `requestAnimationFrame`).
- `PATCH /api/meetings/{id}` `{ title }`; `PATCH /api/speakers/{id}` `{ display_name }` (1–40 chars, trimmed, Pydantic-validated).
- Virtualization: `@tanstack/react-virtual` only if needed (note in DECISIONS).

### Edge cases
- Meeting still processing → page shows processing card, then swaps in content without full reload when status becomes `ready` (or `summarizing`: transcript visible, summary skeleton).
- Media missing/expired URL → refresh signed URL once; if still failing show "Recording unavailable, transcript still works."
- Segment with `start_ms` beyond media duration (rounding) → clamp seek to duration.
- Seeking while the media hasn't loaded metadata → queue the seek until `loadedmetadata`.
- Two speakers renamed to the same name → allowed but warn inline "Another speaker has this name."
- Transcript search with regex chars (`(`, `?`) → escape input.
- Mobile Safari autoplay rules → play only on user gesture (chip clicks count as gestures).

### Error handling
- Failed `PATCH` → revert optimistic update + toast "Couldn't save. Try again."
- Unknown meeting id → API 404 `NOT_FOUND` → `web/app/not-found.tsx`.
- Meeting `failed` → error card with code-specific message + Retry (F2) + Delete.

### Tasks
- [ ] Page layout + header + inline title edit
- [ ] `useMeetingPlayer` store + Player (video/audio)
- [ ] Transcript list + active segment + follow-along + jump to now
- [ ] Speaker timeline lanes + seek + filter
- [ ] Rename speaker API + optimistic UI
- [ ] Transcript search + shortcuts
- [ ] Processing / failed / partial (summarizing) states

---

## F4 — AI summary + action items (`f04-summary-actions`)  ⭐ standout feature

**Goal:** a structured summary and action items where **every bullet has clickable timestamp citations** that were verified against the transcript.

### Requirements
- R4.1 Generate on `summarizing` with template `general`; user can switch template: **General, Sales call, Standup, Interview** (generated on demand, cached per template).
- R4.2 Output sections (General): _Overview (2–3 sentences), Key decisions, Discussion points, Open questions_. Each bullet: `{ text, refs: number[] }` (segment idx).
- R4.3 Action items: `{ text, owner (speaker label or null), dueHint (e.g. "Friday") or null, ref }`. Checkbox toggles `done` (persisted).
- R4.4 Citation chips per DESIGN §7: click → seek + scroll + flash segment; hover → speaker + snippet.
- R4.5 "Regenerate" button (per template) with confirm.
- R4.6 "Copy as Markdown" (summary + action items with timestamps).
- R4.7 Summary language = meeting language.

### Acceptance criteria
- For a seeded meeting, every bullet shows ≥ 1 chip and every chip points to a segment that actually supports it (spot-check 5).
- No chip ever references a non-existent idx (server-side filter, unit-tested).
- Switching template shows a skeleton then the new summary; switching back is instant (cached).
- Meeting ends in `ready`.

### System design
```
generate_summary(meeting_id, template):     # app/services/llm/summary.py
  segments → format lines "[#12] (11:40) Sara: We'll ship on Friday."
  if tokens(transcript) > ~120k → chunk by ~30 min, summarize chunks (map), then merge (reduce) keeping refs
  call Claude with system prompt (app/services/llm/prompts.py):
     - "Use only the transcript. Every bullet MUST include refs to the [#idx] lines that support it."
     - "If something isn't in the transcript, don't write it."
     - return JSON matching the Summary model (JSON schema from `Summary.model_json_schema()`)
  parse with Pydantic (Summary, ActionItems)
     ValidationError → retry once with the error appended → fail again → LLM_BAD_OUTPUT
  sanitize_refs: drop refs not in [0, maxIdx]; drop bullets left with 0 refs (log count)
  map action owner label → speaker_id (case-insensitive on display_name/label; else null)
  upsert summaries(meeting_id, template); replace action_items (only for template=general)
  status = ready
```
- Endpoints: `POST /api/meetings/{id}/summary { template }` (generate/regenerate: enqueues a `summarize` job with a dedupe key, returns 202), `PATCH /api/action-items/{id} { done }`. Frontend polls the summary status.
- Model + prompt version saved in `summaries.model` / `summaries.prompt_version` for traceability.
- Use Claude tool use (one tool whose input schema is the Summary JSON schema) to force structured output; still validate with Pydantic.

### Edge cases
- Very short meeting (< 2 min or < 5 segments) → summary has Overview only; other sections empty with "Nothing to note" text, not invented content.
- No decisions / no action items → show empty state "No action items were mentioned", not an empty box.
- LLM returns refs as strings ("12") or ranges ("12-14") → coerce with a Pydantic `field_validator` (int-cast strings; expand ranges up to 5).
- LLM cites a segment that exists but is irrelevant → can't fully prevent; mitigate with prompt + low temperature (0.2); noted as known limitation.
- Owner name not matching any speaker (e.g. "John" when speakers are unnamed) → keep text, owner = null, show "Unassigned".
- Speaker renamed after summary → owner pills read live speaker names (stored as `owner_speaker_id`, not text).
- Regenerate while one is running → disable button; server rejects concurrent generation for the same (meeting, template) with 409.
- Non-English meeting → prompt says "write in {language}".

### Error handling
| Case | Code | Result |
|---|---|---|
| Claude 5xx/timeout (after 1 retry) | `LLM_FAILED` | meeting stays usable (`ready` with transcript), summary panel shows error + Retry |
| Invalid JSON twice | `LLM_BAD_OUTPUT` | same as above |
| 429 | `RATE_LIMITED` | backoff retry (max 3), then `LLM_FAILED` |

**Important:** a failed summary must **not** mark the whole meeting `failed`; the transcript is still valuable. Store summary errors on the summary panel, set meeting `ready`.

### Tasks
- [ ] Pydantic models + `sanitize_refs` + tests first (invalid idx, ranges, strings)
- [ ] Prompt templates (4) in `app/services/llm/prompts.py`, versioned
- [ ] `generate_summary` + chunked path for long meetings + API tests with a mocked Claude client
- [ ] `make gen-api`; Summary panel + template switcher + skeleton + error/retry
- [ ] CitationChip (seek, scroll, flash, tooltip)
- [ ] Action items list + done toggle + owner pills
- [ ] Copy as Markdown
- [ ] `make export-seed`: export processed demo meetings (speakers, segments, summaries, action items) to `api/seed/*.json`; re-run `make seed` against production

---

## F5 — Ask AI (`f05-ask-ai`)

**Goal:** ask questions about one meeting and get streamed answers with citation chips.

### Requirements
- R5.1 "Ask AI" tab next to Transcript. 3 suggested questions when empty (e.g. "What did we decide about pricing?", "What are my next steps?", "What concerns were raised?").
- R5.2 Answers stream token by token; refs written as `[#12]` in the text are rendered as chips inline.
- R5.3 History saved per meeting (`chat_messages`), shown on reload; "Clear chat".
- R5.4 If the answer isn't in the transcript, the AI says so plainly.

### Acceptance criteria
- Asking "When is the launch?" on a seeded meeting returns an answer with ≥ 1 chip in < 3s to first token.
- Asking "What's the weather in Paris?" → "That wasn't discussed in this meeting."
- Invalid refs never render as chips (rendered as plain text).

### System design
- `POST /api/meetings/{id}/chat` with `{ message }` → FastAPI `StreamingResponse` (`text/event-stream`) using the Anthropic SDK's streaming; context = system prompt + transcript lines + last 10 messages. Events: `token`, `done` (with validated `refs`), `error`.
- Web reads the stream with `fetch` + `ReadableStream` (not the generated client).
- Client parses `[#n]` with a regex as text streams; validates n against the loaded segment list before rendering a chip.
- On stream finish (or client disconnect): API saves user + assistant messages with extracted `refs`; disconnect → `stopped = true`.
- Long meetings: same token check as F4; if too long, include only top-k segments by Postgres full-text rank for the question + the summary.

### Edge cases
- Empty or whitespace message → button disabled. Message > 2,000 chars → blocked with counter.
- User sends while a stream is running → disabled until done; "Stop" button aborts the stream (AbortController) and saves partial answer marked "stopped".
- Meeting still processing → tab disabled with tooltip "Available when the transcript is ready."
- Prompt injection inside the transcript ("ignore previous instructions") → system prompt treats transcript as data; never executes instructions from it.
- Network drop mid-stream → keep partial text, show "Connection lost — Retry".

### Error handling
- `LLM_FAILED` / `RATE_LIMITED` → assistant bubble shows error + Retry (resends same message, no duplicate user message).

### Tasks
- [ ] Chat route with streaming + persistence
- [ ] Inline chip parser + validation + tests
- [ ] Chat UI: suggestions, stream, stop, clear, errors
- [ ] Long-meeting retrieval fallback

---

## F6 — Dashboard + search (`f06-dashboard-search`)

**Goal:** see all meetings and search across every transcript.

### Requirements
- R6.1 `/meetings`: list (DESIGN §7 meeting row), newest first, with status badges and 2-line overview preview.
- R6.2 Search box: full-text across segment text + meeting titles; results grouped by meeting, each hit shows speaker, timestamp chip and the matched snippet with `<mark>`.
- R6.3 Clicking a hit opens `/meetings/:id?t=<ms>` and seeks there.
- R6.4 Delete meeting (confirm dialog) → removes rows + storage object.

### Acceptance criteria
- Searching a word said in two seeded meetings returns both, ranked, < 500ms.
- `?t=700000` opens the meeting at 11:40.
- Empty search shows the meeting list; no results shows "No matches for 'x'."

### System design
- `GET /api/search?q=` → `websearch_to_tsquery('english', q)` on `segments.search` + `ts_headline` for snippet; limit 50; join meetings/speakers.
- Debounce input 250ms; cancel in-flight requests.

### Edge cases
- Query with only stopwords ("the") → no results message, not an error.
- Special characters / quotes → `websearch_to_tsquery` handles them; never interpolate SQL.
- Non-English meetings → english stemming is imperfect; also match `ILIKE` fallback on titles. Known limitation.
- Deleting a meeting that's still processing → allowed; late webhook finds no meeting and is ignored.

### Error handling
- Search failure → inline error under the box + Retry; list still visible.
- Delete failure → toast, item restored.

### Tasks
- [ ] Dashboard list + states
- [ ] Search API + snippet highlighting + tests
- [ ] `?t=` deep link support in F3
- [ ] Delete with confirm

---

## F7 — Highlights + share link (`f07-highlights-share`)  (P2)

**Goal:** mark key moments and share a read-only meeting page.

### Requirements
- R7.1 Select text in the transcript (or press `H` while playing) → "Add highlight" → saved range with optional note; shown in a Highlights list and as `--highlight` marks on the timeline.
- R7.2 Share button → creates `share_token` (random 22-char) → copy link `/s/<token>`.
- R7.3 Public page: read-only player, transcript, summary, highlights. No Ask AI, no edit, no delete.
- R7.4 "Stop sharing" revokes the token.

### Acceptance criteria
- Opening the share link in a private window works without sign-in; edits are impossible (no edit controls, API rejects writes without owner).
- Revoked link → 404 page.

### System design
- `POST /api/meetings/{id}/share` / `DELETE` → set/clear token (`secrets.token_urlsafe(16)`).
- `/s/[token]` server component loads by token; media via short-lived signed URL.
- `POST/DELETE /api/meetings/{id}/highlights`.

### Edge cases
- Selection spanning two segments → highlight from first segment start to last segment end.
- Highlight end < start → swap. Zero-length → reject.
- Token guessing → 128-bit random; rate-limit `/s/*` lookups (simple in-memory per IP; note limitation).

### Tasks
- [ ] Highlights API + UI + timeline marks
- [ ] Share token API + share dialog
- [ ] Public read-only page

---

## F8 — Authentication (`f08-auth`)  (P2)

**Goal:** personal workspaces, without breaking the public demo.

### Requirements
- R8.1 Supabase Auth: magic link + Google.
- R8.2 Signed-in users see only their meetings (`owner_id`); the demo workspace stays public and read-only for everyone.
- R8.3 Web sends the Supabase access token as `Authorization: Bearer`; a FastAPI dependency (`get_current_user`) verifies the JWT and is required on all write endpoints. Demo meetings can't be edited/deleted by anyone.

### Edge cases
- Expired magic link → friendly page + "Send a new link".
- User signs in mid-upload → upload continues; meeting assigned on completion.
- Ownership is enforced in the API services (the API connects with full DB rights, so RLS is a second layer only): every query filters by `owner_id`; demo rows (`owner_id = null`, `source = seed`) are readable by all, writable by none.
- Invalid/expired token → 401 `UNAUTHORIZED`; web refreshes the session once, then sends the user to sign in.

### Tasks
- [ ] Supabase Auth in web + `get_current_user` JWT dependency in API + tests
- [ ] `owner_id` on create + ownership filters in services (+ RLS as backup)
- [ ] Demo protection + sign-in UI

---

## Final polish checklist

- [ ] README: what it is, live URLs (web + API docs), demo meeting to open first, what I built and why in this order, architecture diagram, what I cut and why, known limitations, how I worked (OpenSpec + Claude Code, link to `openspec/changes/archive` and `docs/DECISIONS.md`)
- [ ] Lighthouse pass on landing + meeting page (no console errors)
- [ ] Playwright smoke: open demo → click chip → player time changes
- [ ] 1-minute intro video
- [ ] Walkthrough recording (camera on, voiceover): demo → standout feature → code tour → process (specs, prompts, decisions)
- [ ] Submit: GitHub, live URL, intro, walkthrough, optional note
