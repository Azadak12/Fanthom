# DECISIONS.md

One line per decision that changes scope, stack or design. Newest at the bottom.

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Upload goes browser → Supabase Storage via signed URL, never through the API | Large recordings; keeps the API fast and cheap |
| 2026-11-18 | Demo workspace opens with no sign-in; auth (F8) is last and optional | Reviewers must reach the product in one click |
| 2026-11-18 | Every AI bullet carries segment refs, validated server-side | Core promise: notes that show their receipts; prevents invented citations |
| 2026-11-18 | A failed summary doesn't fail the meeting | The transcript is still useful on its own |
| 2026-11-18 | No live meeting bot (Zoom/Meet/Teams) | Out of scope for this build; upload + URL import cover the core flow |
| 2026-11-18 | Backend in FastAPI (Python), frontend in Next.js; monorepo `api/` + `web/` | Python suits the AI/LLM work; Pydantic validates LLM output; clear UI/API split |
| 2026-11-18 | API deployed on Railway (always-on), web on Vercel | SSE and the worker need long-running processes; no cold start for reviewers |
| 2026-11-18 | Frontend API types generated from FastAPI's OpenAPI | One source of truth for the contract between web and API |
| 2026-11-18 | Durable Postgres job queue + worker instead of in-process background tasks | Work survives crashes/deploys, retries safely, scales by adding workers, no extra infrastructure |
| 2026-11-18 | Rate limits, pagination, request ids and structured logs from F0 | Reliability and cost control are built in, not added later |
