# PLAYBOOK.md — How Fanthom gets built

> This file is for **me (Abdul)**, not loaded by Claude. It's the exact loop I run for every feature, the prompts I paste, and the rules that keep this from turning into vibe coding.
> It also goes in the repo as evidence of process.

---

## 1. The difference from vibe coding

| Vibe coding | This project |
|---|---|
| "Build me a Fathom clone" | One feature at a time, from a written spec |
| AI decides scope | `FEATURES.md` decides scope; the AI proposes, I approve |
| Accept whatever compiles | Typecheck + lint + tests must pass after every task group (and in CI) |
| Edge cases discovered by users | Edge cases written **before** coding, turned into spec scenarios and tests |
| One giant chat for the whole build | Fresh session per feature, small context, cheap and focused |
| "It works on my machine" | Every feature checked on the deployed URL before it's marked done |
| No record of why | OpenSpec archive + `DECISIONS.md` + commit history show every decision |

## 2. One-time setup

```bash
mkdir fanthom && cd fanthom && git init
# unzip the starter kit here (CLAUDE.md, Makefile, docs/, .claude/, .github/)

# frontend
pnpm create next-app@latest web --ts --tailwind --app --eslint --import-alias "@/*" --use-pnpm
cd web && corepack use pnpm@latest && cd ..

# backend
uv init --app --python 3.12 api

openspec init                      # choose Claude Code
git add . && git commit -m "chore: scaffold + specs"
```
Push to GitHub. Then:
- **Vercel** → import the repo → Root Directory `web` → add `web/.env.local` values.
- **Railway** → new project from the repo → two services, both Root Directory `api` (built from `api/Dockerfile`, created in F0): **api** (default start command) and **worker** (start command `python -m app.worker`). Add `api/.env` values as shared variables.
Both redeploy on every push to `main`.

`web/package.json` scripts that keep output short (fewer tokens when Claude runs them):
```json
"typecheck": "tsc --noEmit",
"lint": "next lint --quiet",
"test": "vitest run --reporter=dot",
"e2e": "playwright test --reporter=line"
```
The backend side is already quiet in the Makefile (`pytest -q`, `ruff --quiet`).

## 3. Model and context rules (token saving)

- **Model:** Opus for `/opsx:explore`, for reviewing the proposals of F0, F2 and F4 (data model, pipeline, citations), and for hard bugs. **Sonnet for `/opsx:apply`** and small fixes. Switch with `/model`.
- **One session per feature.** After `/opsx:archive` and the commit: `/rename fNN-name` then `/clear`. A long session re-sends its whole history on every message.
- **`/compact` only mid-feature** when the context gets big (the compact instructions in CLAUDE.md say what to keep). Between features, always `/clear` instead.
- **`/context`** when something feels slow, to see what's eating the window.
- **Point Claude at exact sections**, never "read the docs": _"Read the F4 section of docs/FEATURES.md and §3 of docs/ARCHITECTURE.md."_
- **Specific prompts:** name the file, function and expected result. Vague prompts make Claude scan the whole repo.
- **Stop early:** `Esc` the moment it goes the wrong way; `/rewind` (or double `Esc`) to go back to a checkpoint instead of arguing with a broken attempt.
- **Plan mode** (`Shift+Tab`) for anything not covered by an OpenSpec task (e.g. a tricky bug), so it plans before it edits.

## 4. The loop (repeat for F0 → F8)

### Step 0 — Explore (once, right after reading the brief)
```
/opsx:explore
I'm rebuilding Fathom (fathom.video) as "Fanthom" for the 8x Product Engineer assignment.
Read CLAUDE.md, docs/ARCHITECTURE.md and the Roadmap table at the top of docs/FEATURES.md.
Here is the assignment brief: <paste brief>.
1) List anything in the brief that FEATURES.md doesn't cover or contradicts.
2) Challenge the data model and the processing pipeline: what will break first in production?
3) Point out any feature whose scope is too big and what to cut from it.
Don't write code or files. Answer in a short list.
```
→ Update the docs myself with what I accept. Log decisions in `DECISIONS.md`. Commit: `docs: finalize specs`.

### Step 1 — Propose
```
/opsx:propose f02-transcription
Source of truth: the "F2" section of docs/FEATURES.md, plus §2–3 of docs/ARCHITECTURE.md.
- Turn every requirement and every edge case into a spec scenario (WHEN/THEN).
- Put the system design and the error-handling table into design.md.
- tasks.md: small ordered task groups; unit tests for pure logic come BEFORE the code they test.
- Don't add anything that isn't in the F2 section.
```

### Step 2 — Review the proposal (me — this is the step that makes it not vibe coding)
- [ ] Every edge case from FEATURES.md is a scenario
- [ ] Error codes and user messages match the table
- [ ] Data/API changes match ARCHITECTURE.md (or ARCHITECTURE.md is updated on purpose)
- [ ] Tasks are small (each one ≈ 1 commit) and tests come first for logic
- [ ] Nothing extra snuck in
Fix it by editing the files directly or telling Claude exactly what to change. Then commit: `docs(f02): proposal`.

### Step 3 — Apply (Sonnet)
```
/opsx:apply f02-transcription
Work one task group at a time. After each group: run the check gate
(make check), fix failures, tick the tasks,
then STOP and give me a 3-line summary: files changed, why, anything I should test by hand.
```
After each stop: skim the diff (`git diff --stat`, then the important files), commit, say "continue".

### Step 4 — Verify like a user
- Click through the feature locally, including 2–3 edge cases from the spec (wrong file, silent file, long meeting…).
- Push → check the **deployed** web URL (Vercel) and API (`{API_URL}/docs` on Railway).
- If something's wrong:
```
Bug in f02: <what I did> → <what happened> → <what I expected>.
Relevant file: lib/deepgram.ts. Find the root cause first and explain it in 2 lines, then fix it
and add a test that would have caught it.
```

### Step 5 — Archive and reset
```
/opsx:archive f02-transcription
```
Commit `chore(f02): archive change`, push. Then `/rename f02-transcription` → `/clear`. Next feature.

## 5. Progress checkpoints

| Checkpoint | Must be true |
|---|---|
| 1 | F0 deployed with demo data |
| 2 | Upload → transcript works on the live URL |
| 3 | Summary with citations (standout feature) live |
| 4 | F5, F6 done; F7/F8 only if everything above is solid |
| 5 | README, intro video, walkthrough, submitted |

If a feature grows beyond its spec → cut its P2 parts, write the cut in `DECISIONS.md`, move on.

## 6. Evidence for reviewers (collected as I go)
- `openspec/changes/archive/` → every feature's spec, design and tasks, dated
- `docs/DECISIONS.md` → what I changed or cut and why
- Git log → small conventional commits per task group
- CI badge green on the README
- Optional: `/export` each feature session into `docs/sessions/` so they can read my prompts
- Walkthrough video: show one proposal, the review I did on it, and the code it produced
