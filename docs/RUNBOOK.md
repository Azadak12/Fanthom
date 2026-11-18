# RUNBOOK.md — Build Fanthom, prompt by prompt

Follow this file top to bottom. Every prompt is written out in full: copy it, paste it, then do what the "You do" line says.

## First, how files work (read once)

You **never upload or attach files** to Claude Code. All the docs live inside your project folder, and Claude reads them from there:

| File | How Claude gets it |
|---|---|
| `CLAUDE.md` | **Loaded automatically** every time you start `claude` in the folder. Never paste it. |
| `docs/FEATURES.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/BRIEF.md` | Claude opens them when **your prompt names them** (e.g. "Read the F2 section of docs/FEATURES.md"). |
| `openspec/changes/<name>/…` | **Created by OpenSpec** when you run `/openspec-propose`. You review them; `/openspec-apply-change` builds from them. |
| `docs/DECISIONS.md` | You or Claude add a line when something changes. |

Two places you type things:
- **Terminal** → commands like `git`, `openspec init`, `make dev-api`.
- **Claude Code chat** (after typing `claude`) → prompts and slash commands like `/openspec-propose`, `/model`, `/clear`.

Run the app locally in three extra terminal tabs whenever you need to test: `make dev-api`, `make dev-worker` and `make dev-web`.

---

## STAGE 0 — Setup (terminal only, no Claude yet)

```bash
mkdir fanthom && cd fanthom && git init
# unzip fanthom-starter.zip here so CLAUDE.md, Makefile, docs/, .claude/, .github/ are in this folder
# create docs/BRIEF.md and paste the full assignment brief into it
# create docs/reference/ and put screenshots of Fathom's main screens in it
#   (dashboard, meeting page with transcript, summary, action items, ask/chat, share)

pnpm create next-app@latest web --ts --tailwind --app --eslint --import-alias "@/*" --use-pnpm
cd web && corepack use pnpm@latest && cd ..
uv init --app --python 3.12 api

openspec init            # choose Claude Code
git add . && git commit -m "chore: scaffold + specs"
```
Create the GitHub repo and push. (Vercel and Railway are connected later, in F0.)

Start Claude Code:
```bash
claude
```

---

## STAGE 1 — Explore (once)

**Prompt 1** (Claude Code chat)
```
/model
```
→ pick **Opus**.

**Prompt 2**
```
/openspec-explore
Read docs/BRIEF.md, docs/ARCHITECTURE.md, and only the Roadmap table at the top of docs/FEATURES.md.
1) List anything the brief asks for that FEATURES.md is missing or contradicts.
2) What in the data model or processing pipeline will break first in production?
3) Which feature's scope is too big, and what should be cut from it?
Don't write code or files. Short numbered list only.
```
**What happens:** Claude reads the brief and specs and gives you a list of gaps and risks. No files change.

**You do:** decide which points you agree with. Then:

**Prompt 3**
```
Apply these changes to the docs: <paste the numbered points you accept, in your own words>.
Edit only docs/FEATURES.md and docs/ARCHITECTURE.md, and add one line per change to docs/DECISIONS.md.
Show me a short summary of what you changed.
```
**Prompt 3b** (match Fathom's screens)
```
Look at the screenshots in docs/reference/. Update docs/DESIGN.md §6 (layout) and §7 (components)
so our screens follow the same structure, information order and interactions as these screens:
what sits where, what each panel shows, how navigation works. Keep our own name, logo, colors
and fonts from DESIGN.md (don't copy Fathom's branding). List every change you made.
Also list any feature visible in the screenshots that FEATURES.md doesn't cover, but don't add it.
```
**You do:** decide which uncovered features (if any) are worth adding, tell Claude to add them to FEATURES.md, then in the terminal: `git add . && git commit -m "docs: finalize specs"`.

**Prompt 4**
```
/clear
```

---

## STAGE 2 — Build each feature

Every feature follows the **same 6 moves**. F0 is written out fully; for F1–F8 only the parts that change are listed.

### F0 — Foundation

**Prompt 5** (model: Opus)
```
/openspec-propose f00-foundation
Source of truth: the "F0" section of docs/FEATURES.md, plus §1, §3, §5, §6, §7 of docs/ARCHITECTURE.md and §11 of docs/DESIGN.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error handling go into design.md.
- tasks.md: small ordered task groups. Backend first, then `make gen-api`, then frontend.
  Unit tests for pure logic come BEFORE the code they test.
- Add nothing that isn't in the F0 section.
```
**What happens:** OpenSpec creates `openspec/changes/f00-foundation/` with `proposal.md`, `specs/`, `design.md`, `tasks.md`. No code yet.

**You do — review (the most important step):** open those 4 files and check:
- [ ] every edge case from the F0 section is a scenario
- [ ] the tables match ARCHITECTURE §3 exactly (names, types, cascade, tsvector)
- [ ] tasks are small and tests come first
- [ ] nothing extra was added

Wrong or missing? Either edit the file yourself, or:

**Prompt 6** (only if needed)
```
Update the f00-foundation proposal: <what's wrong and what it should be>. Change only the proposal files.
```
Then terminal: `git add . && git commit -m "docs(f00): proposal"`.

**Prompt 7**
```
/model
```
→ pick **Sonnet** (cheaper, great for writing code from a clear spec).

**Prompt 8**
```
/openspec-apply-change f00-foundation
Do one task group at a time. After each group run `make check`, fix any failures,
tick the finished tasks in tasks.md, then STOP and tell me in 3 lines:
files changed, why, and what I should test by hand.
```
**What happens:** Claude builds the first task group, runs the checks, and stops with a short summary.

**You do after every stop:**
1. Terminal: `git diff --stat` (and open any file that looks important).
2. Terminal: `git add . && git commit -m "feat(f00): <what that group did>"`.
3. Then:

**Prompt 9** (repeat until every task is ticked)
```
continue
```

**You do — deploy (F0 only):**
- **Railway:** New Project → from your GitHub repo → Root Directory `api` → add every variable from `api/.env` (set `API_URL` to the Railway URL, `WEB_URL` to the Vercel URL). Name this service **api**.
- **Railway worker:** in the same project, add a second service from the same repo → Root Directory `api` → Start Command `python -m app.worker` → same variables (use Railway's shared variables). Name it **worker**.
- **Vercel:** Import the repo → Root Directory `web` → add `NEXT_PUBLIC_API_URL` = Railway URL, plus the Supabase public values.
- Run migrations and seed once against production: in terminal, put the production `DATABASE_URL` in `api/.env`, run `make migrate && make seed`.

**You do — verify:**
- Locally: `make dev-api` + `make dev-worker` + `make dev-web` → open localhost:3000 → landing → Open demo → dashboard lists meetings.
- Live: same on the Vercel URL. `{Railway URL}/docs` shows the API docs. CI is green on GitHub.

If something's broken:

**Bug prompt** (use any time)
```
Bug in f00: <what I did> → <what happened> → <what I expected>.
Error/log: <paste the error>.
Find the root cause first and explain it in 2 lines, then fix it and add a test that would have caught it.
```

**Prompt 10**
```
/openspec-archive-change f00-foundation
```
**What happens:** the spec is merged into `openspec/specs/` and the change moves to `openspec/changes/archive/`.

Terminal: `git add . && git commit -m "chore(f00): archive" && git push`

**Prompt 11** (reset for the next feature)
```
/rename f00-foundation
```
```
/clear
```

---

### F1 — Add a meeting

**Model for propose:** Sonnet (switch with `/model`)
```
/openspec-propose f01-add-meeting
Source of truth: the "F1" section of docs/FEATURES.md, plus §2 and §4 of docs/ARCHITECTURE.md and §7–8 of docs/DESIGN.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error-handling table go into design.md.
- tasks.md: backend first, then `make gen-api`, then frontend. Tests before logic.
- Add nothing that isn't in the F1 section.
```
**Review focus:** file type + size checked on both web and API · cancel deletes row **and** storage object · stuck-upload rule · error messages match the table.

Then the same moves: commit proposal → `/model` Sonnet → `/openspec-apply-change f01-add-meeting` (same apply prompt as Prompt 8, change the name) → `continue` until done → verify (upload a real mp3, try a .pdf, try a huge file, cancel mid-upload) → `/openspec-archive-change f01-add-meeting` → commit + push → `/rename f01-add-meeting` → `/clear`.

---

### F2 — Transcription

**Model for propose:** Opus
```
/openspec-propose f02-transcription
Source of truth: the "F2" section of docs/FEATURES.md, plus §2 and §3 of docs/ARCHITECTURE.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error-handling table go into design.md.
- tasks.md: `map_utterances` tests (with a saved Deepgram JSON fixture) come first,
  then the service, then the router, then `make gen-api`, then the processing card UI.
- Add nothing that isn't in the F2 section.
```
**Review focus:** webhook only checks the secret and enqueues a job · `transcribe` and `ingest_transcript` are jobs and idempotent · same webhook twice = no duplicates · stale callback ignored (`deepgram_request_id`) · job fails 3× → meeting `failed` · `NO_SPEECH` path · sync mode for local dev.

**Before apply:** set `DEEPGRAM_MODE=sync` in your local `api/.env`. Production (Railway) uses `callback`.

Apply → continue → **verify:** upload one of your mock meetings locally, watch it go Transcribing → Summarizing; check speakers in Supabase table editor and the `jobs` table; test a silent file; stop the worker mid-job, start it again, and check the job finishes. Push and test on the live site (callback mode). → archive → commit + push → rename → clear.

---

### F3 — Meeting page

**Model for propose:** Sonnet
```
/openspec-propose f03-meeting-page
Source of truth: the "F3" section of docs/FEATURES.md, plus §6, §7, §8, §10 of docs/DESIGN.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error handling go into design.md.
- tasks.md: API changes first (PATCH speaker/title), then `make gen-api`, then the player store, transcript, timeline, search.
- Follow docs/DESIGN.md exactly for layout, colors and states.
- Add nothing that isn't in the F3 section.
```
**Review focus:** one shared player store · follow-along + "jump to now" · rename speaker updates everywhere · keyboard shortcuts · processing/failed states.

Apply → continue → **verify:** click lines (player jumps), play and watch the highlight move, rename a speaker, search the transcript, try on your phone. → archive → commit + push → rename → clear.

---

### F4 — Summary + action items ⭐

**Model for propose:** Opus
```
/openspec-propose f04-summary-actions
Source of truth: the "F4" section of docs/FEATURES.md, plus §3 of docs/ARCHITECTURE.md (citation contract) and §7 of docs/DESIGN.md (citation chip).
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error-handling table go into design.md.
- tasks.md: Pydantic models + `sanitize_refs` tests first, then prompts, then `generate_summary`
  with a mocked Claude client in tests, then `make gen-api`, then the UI. Last task: export seed.
- Add nothing that isn't in the F4 section.
```
**Review focus:** summary runs as a `summarize` job with a dedupe key · every bullet must have refs · invalid refs dropped on the server · a failed summary does **not** fail the meeting · 4 templates cached separately · rate limit on the endpoint · prompt asks for the meeting's language.

Apply → continue → **verify:** open a processed meeting, click 5 citation chips and check each one really says that thing; switch templates; tick an action item; rename a speaker and check owner pills change.

**Then load real demo data:**
```
Run `make export-seed` for my processed demo meetings and show me which meetings were exported.
```
Terminal (production `DATABASE_URL` in `api/.env`): `make seed`. Check the live demo shows real meetings with summaries.

→ archive → commit + push → rename → clear.

**Checkpoint:** F0–F4 must work on the live site before going further.

---

### F5 — Ask AI

**Model for propose:** Sonnet
```
/openspec-propose f05-ask-ai
Source of truth: the "F5" section of docs/FEATURES.md, plus §3 of docs/ARCHITECTURE.md and §7 of docs/DESIGN.md (Ask AI, citation chip).
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- System design and error handling go into design.md.
- tasks.md: SSE endpoint + persistence + tests first, then the chip parser with tests, then the chat UI.
- Add nothing that isn't in the F5 section.
```
**Review focus:** "not discussed" answer · stop button saves partial answer · transcript treated as data (prompt injection) · invalid refs shown as plain text.

Apply → continue → **verify:** ask 3 real questions, one off-topic question, press Stop mid-answer, reload and see history. → archive → commit + push → rename → clear.

---

### F6 — Dashboard + search

**Model for propose:** Sonnet
```
/openspec-propose f06-dashboard-search
Source of truth: the "F6" section of docs/FEATURES.md, plus §3–4 of docs/ARCHITECTURE.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- tasks.md: search endpoint + tests first (use the tsvector column), then `make gen-api`, then UI.
- Add nothing that isn't in the F6 section.
```
**Review focus:** no raw SQL string-building · `?t=` deep link opens at the right moment · delete removes the file too.

Apply → continue → verify → archive → commit + push → rename → clear.

---

### F7 — Highlights + share (optional — only if F0–F6 are solid)
```
/openspec-propose f07-highlights-share
Source of truth: the "F7" section of docs/FEATURES.md, plus §4 of docs/ARCHITECTURE.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- tasks.md: API + tests first, then `make gen-api`, then UI. Add nothing outside F7.
```
**Verify:** open the share link in a private window; revoke it and check it shows 404.

### F8 — Login (optional — only if everything else is done)
Model: Opus.
```
/openspec-propose f08-auth
Source of truth: the "F8" section of docs/FEATURES.md, plus §3 of docs/ARCHITECTURE.md.
- Every requirement and every edge case becomes a spec scenario (WHEN/THEN).
- The public demo workspace must keep working with no login.
- tasks.md: JWT dependency + tests first, then ownership filters, then web sign-in.
```

---

## STAGE 3 — Final quality pass

**Prompt** (model: Opus, fresh session)
```
Act as a senior reviewer. Compare the code in api/ and web/ against docs/FEATURES.md (F0–F6),
docs/ARCHITECTURE.md §8 (reliability and scale) and the rules in CLAUDE.md. List, by severity,
anything that is missing, broken, insecure, or won't hold up under heavy load (e.g. secrets in web/,
slow work done inside a request, non-idempotent jobs, missing rate limits or pagination, N+1 queries,
missing indexes, AI text without citations, missing error/empty states, untested pure logic).
Don't change code yet. Max 15 items.
```
**You do:** pick the items worth fixing, then:
```
Fix items <numbers> one at a time. Run `make check` after each and stop with a 2-line summary.
```

**Prompt — e2e smoke test**
```
Add one Playwright test in web/tests/e2e: open the demo workspace, open the first meeting,
click the first citation chip, and assert the player's current time changes. Run it with `make e2e`.
```

---

## STAGE 4 — Ship

**Prompt — README**
```
Write README.md at the repo root: what Fanthom is, live web URL and API docs URL, which demo
meeting to open first, features built, architecture (from docs/ARCHITECTURE.md §2), what was cut
and why (from docs/DECISIONS.md), "Reliability and scale" (summarize docs/ARCHITECTURE.md §8:
what's built in now and the path to millions of users), known limitations, how to run locally,
and "How I built it" linking openspec/changes/archive/ and docs/DECISIONS.md. Add the CI badge.
Under 180 lines.
```
Terminal: `git add . && git commit -m "docs: README" && git push`

**You do:**
1. 1-minute intro video (who you are, your sales + engineering background, why this product).
2. Walkthrough recording, camera on, with voice: demo → citation chips → code tour (api/ services, web/ components) → show one OpenSpec proposal you reviewed and what you changed in it.
3. Submit on 8x: GitHub link, live URL, intro video, walkthrough, short note.

---

## Quick reference

| Situation | Type this |
|---|---|
| Run locally | terminal tabs: `make dev-api`, `make dev-worker`, `make dev-web` |
| Start of any feature | `/clear`, then `/model` (Opus for F0, F2, F4, F8; Sonnet otherwise), then the propose prompt |
| Claude stopped after a task group | review diff → commit → `continue` |
| Claude is going the wrong way | press `Esc`, then explain what you want instead |
| Need to undo Claude's last steps | `/rewind` |
| Conversation getting long mid-feature | `/compact` |
| Something broke | the Bug prompt |
| Feature done | `/openspec-archive-change <name>` → commit + push → `/rename <name>` → `/clear` |
| See where tokens go | `/context` |
