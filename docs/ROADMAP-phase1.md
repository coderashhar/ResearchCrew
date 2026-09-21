# ResearchCrew Phase 1: trustworthy core on Vercel (Next.js + FastAPI + Neon)

Repo: `/Users/mohd.ashharkhan/Desktop/Projects/Multi Agent Research`

## Context

PM brainstorm picked Phase 1 = "trustworthy core". The user also wants to leave Streamlit and deploy on Vercel. Streamlit cannot run on Vercel, so the UI moves to Next.js and the Python agents move behind FastAPI, deployed as two Vercel Services in one project. Runs are saved in Neon Postgres. UI follows Emil Kowalski design-engineering rules.

Problems in current code:
- Critic score is decorative: a 4/10 report ships unchanged (`agents.py` `critic_chain`, regex-parsed in `app.py:613`).
- Thin research: `tools.py` hardcodes `topic="news", days=30`; reader sees 800 chars of search output, scrapes **one** URL, keeps 3,000 chars.
- Writer lists "all URLs found", so reports cite pages nobody read. No inline citations.
- `app.py:748-829` duplicates `pipeline.py`. No retries, no tests, nothing persists.
- Scraped text goes into `unsafe_allow_html` unescaped.

**Outcome:** every claim cites `[n]` a source the system actually read; a structured critic fact-checks and sends weak reports back for revision or more research; live streamed progress in Next.js; every run saved with a shareable permalink.

Installed already (Python): `langgraph 1.2.6`, `langchain 1.3.11`, `langchain_mistralai 1.1.5`, `tavily-python 0.7.26` (has `extract()`), `pydantic 2.13`, `tenacity 9.1`.

Vercel facts (docs, 2026-08): Hobby function max **300s** (Pro 800s). FastAPI app builds into one function; `maxDuration` set per service. Services (Beta) host Next.js + FastAPI in one project via top-level `rewrites`; `vercel dev -L` runs both locally. Fallback if Services is not enabled: Next.js app + `api/index.py` FastAPI function with a `next.config` rewrite `/api/:path*` (same code, different wiring).

## How to use this plan

Each PR below is self-contained. Prompt: **"Implement PR N from docs/ROADMAP-phase1.md"** (PR 1 copies this plan into the repo at that path). For each PR:
1. Branch from latest `main` with the listed branch name. Confirm the "Depends on" PRs are merged first.
2. Make the listed commits in order. Each commit passes the checks below on its own.
3. Write the listed tests in the same commit as the code they cover.
4. Open the PR against `main` with a summary + test plan. **No Claude attribution trailers in commits or PR body.**

Checks per commit: backend `cd backend && pytest -q`; frontend (from PR 7) `cd frontend && npm run lint && npm test && npm run build`.

Old Streamlit files (`app.py`, `agents.py`, `tools.py`, `pipeline.py` at root) stay untouched and working until PR 10 removes them. New code lives in `backend/` and `frontend/`.

## Target layout

```
vercel.json
docs/ROADMAP-phase1.md
backend/
  main.py                    FastAPI (entrypoint main:app)
  cli.py
  research/ __init__.py config.py schemas.py citations.py tools.py agents.py graph.py db.py events.py
  migrations/001_runs.sql
  tests/  conftest.py + one test file per module
  requirements.txt  pytest.ini
frontend/                    Next.js 16 App Router, TypeScript, Tailwind, Vitest, Playwright
```

---

## PR 1: Backend foundation, schemas, citations
Branch `phase1/01-backend-foundation`. Depends on: none.

Commits:
1. `Add backend package skeleton and test setup`: `backend/research/__init__.py`, `requirements.txt` (fastapi, langgraph, langchain, langchain-mistralai, tavily-python, beautifulsoup4, requests, tenacity, pydantic, psycopg[binary,pool], python-dotenv, rich, pytest, httpx), `pytest.ini`, `tests/conftest.py` (clears API env vars, blocks network via monkeypatched `socket.socket` unless `@pytest.mark.integration`). Add `docs/ROADMAP-phase1.md` (copy of this plan).
2. `Load API keys from one place`: `research/config.py` with `Settings` (pydantic-settings or dataclass): `MISTRAL_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`, `WRITER_MODEL=mistral-medium-3-5`, `CRITIC_MODEL=mistral-large-latest`, `PASS_SCORE=7`, `MAX_REVISIONS=2`, `TIME_BUDGET_S=220`; `get_settings()` raises `MissingKeyError` naming the missing variable.
3. `Define research data contracts`: `research/schemas.py` — `SearchQuery(query, topic: Literal["general","news"], days: int|None)`, `SearchPlan(queries: 1-5)`, `Source(id, url, title, domain, content, score)`, `UnsupportedClaim(claim, source_id, reason)`, `Critique` (five rubric ints 1-10, `overall` 1-10, strengths, gaps, unsupported_claims, needs_more_research, followup_queries), `Draft(version, report, critique|None)`.
4. `Parse and validate inline citations`: `research/citations.py` — `used_ids`, `clean_citations`, `build_sources_section`, `format_sources_block` (numbered `[n] title (url)\n content` for prompts).

Tests:
- `test_config.py`: defaults applied; missing `TAVILY_API_KEY` raises error naming it; env overrides `PASS_SCORE`.
- `test_schemas.py`: `Critique` rejects 0 and 11; `SearchPlan` rejects 0 and 6 queries; `topic` rejects `"sports"`.
- `test_citations.py`: `[1]`, `[1, 3]`, `[2][4]` parsed; duplicates collapse, ordered; unknown `[9]` stripped, `[1, 9]` becomes `[1]`; Sources section lists only cited sources in id order; no citations → no Sources section; `format_sources_block` truncates content to limit.

## PR 2: Multi-source search and reading
Branch `phase1/02-multi-source-research`. Depends on: PR 1.

Commits:
1. `Search with per-query topic and recency`: `tools.search(q, max_results=6)` passes `topic`, `days` only when set; `tenacity` retry (3 tries, exponential, on network/5xx errors).
2. `Pick diverse, high-scoring sources`: `select_sources(results, existing_urls, n=6)` — normalize URL (strip fragment, `utm_*`), dedupe URL + domain, skip existing, rank by Tavily `score`.
3. `Read sources in one batch with scrape fallback`: `read_sources(results, start_id)` — `tavily.extract(urls, format="markdown")`; `failed_results` go to `_scrape_fallback` (current BeautifulSoup logic) in `ThreadPoolExecutor(max_workers=6)`; skip on double failure; 4,000 chars per source; ids sequential from `start_id`.

Tests (`test_tools.py`, Tavily client mocked):
- `search` sends `topic="general"` without `days`; sends `days` for news; retries twice then succeeds; gives up after 3.
- `select_sources`: two URLs from same domain → one kept (higher score); `?utm_source=x` duplicates collapse; existing URLs excluded; returns at most `n`.
- `read_sources`: extract success → `Source` list with sequential ids from `start_id`; one failed URL uses fallback; fallback raising → source skipped, others kept; content truncated to 4,000.

## PR 3: Planner, cited writer, structured critic
Branch `phase1/03-agent-chains`. Depends on: PR 1.

Commits:
1. `Plan search queries before searching`: `planner_chain` → `SearchPlan`; prompt includes today's date, rules for `general` vs `news`.
2. `Write reports with inline citations only`: `writer_chain(topic, sources_block, previous_draft, critique_notes)`; rules: every factual claim cites `[n]`, only given sources, no Sources section, source text is untrusted data; revision mode when `previous_draft` set.
3. `Fact-check reports with a structured critic`: `critic_chain` → `Critique` via `with_structured_output`, input report + sources block; separate `critic_llm` from `CRITIC_MODEL`; both LLMs `.with_retry(stop_after_attempt=3)`. `build_chains(settings, writer_llm=None, critic_llm=None)` factory so tests inject fakes.

Tests (`test_agents.py`, `langchain_core` fake chat models / `RunnableLambda`, no network):
- Planner prompt contains topic and today's date; structured output parsed into `SearchPlan`.
- Writer prompt contains sources block, "cite" rule, and untrusted-data rule; revision prompt includes previous draft and critique gaps; first-draft prompt omits them.
- Critic receives both report and sources block; returns `Critique`; critic uses the critic model, not the writer model.
- Retry: fake LLM failing once then succeeding still returns result.

## PR 4: Revise-loop graph and CLI
Branch `phase1/04-research-graph`. Depends on: PR 2, PR 3.

Commits:
1. `Route critique to finish, revise, or research more`: `route_after_critique(state, settings, now)` pure function: finalize if `overall >= PASS_SCORE`, `revisions >= MAX_REVISIONS`, or elapsed `> TIME_BUDGET_S`; `search_and_read` if `needs_more_research and research_rounds < 1`; else `write`.
2. `Run research as a LangGraph state machine`: `graph.py` — state (`topic, queries, sources: add, drafts: add, research_rounds, revisions, started_at`), nodes `plan`, `search_and_read`, `write`, `critique`, `finalize`; `build_graph(chains, tools)` with dependency injection.
3. `Add research CLI`: `cli.py` streams `graph.stream(stream_mode="updates")` and prints with `rich`.

Tests (`test_graph.py`):
- Routing table: score 8 → finalize; score 5, revisions 0 → write; score 5, `needs_more_research`, rounds 0 → search_and_read; same with rounds 1 → write; score 5, revisions 2 → finalize; elapsed 230s → finalize.
- Full graph with fake chains (scores 5 then 8) and fake tools: 2 drafts, second is revision, final report ends with Sources listing only cited ids.
- Research round: critic asks for more research → followup queries searched, new source ids continue from last id, no URL duplicates.
- Fake tool failure in one source does not stop the graph.
- `cli.py` smoke: runs with fakes, exit code 0.

## PR 5: Neon persistence and rate limit
Branch `phase1/05-neon-persistence`. Depends on: PR 1.

Commits:
1. `Store research runs in Postgres`: `migrations/001_runs.sql` (`runs`: id uuid pk, topic, created_at, status, final_report, final_score, drafts jsonb, sources jsonb, queries jsonb, elapsed_s, error, client_hash); `db.py` with `psycopg_pool` (URL must carry `connect_timeout=30`, Neon sleeps); `python -m research.db migrate`.
2. `Save, finish, and load runs`: `create_run`, `finish_run`, `fail_run`, `get_run` (pydantic `RunRecord`).
3. `Limit runs per client`: `runs_in_last_hour(client_hash)`; client hash = sha256(IP + salt) so raw IPs are never stored.

Tests (`test_db.py`):
- Unit: `RunRecord` JSON round-trip of drafts/sources; client hash stable and not equal to IP; `connect_timeout` appended when missing and respected when present.
- Integration (`@pytest.mark.integration`, skipped without `TEST_DATABASE_URL`, use a Neon test branch, never the prod DB): migrate is idempotent; create → finish → get returns saved report; fail stores error; `runs_in_last_hour` counts only recent rows for that hash.

## PR 6: FastAPI streaming API on Vercel
Branch `phase1/06-fastapi-streaming`. Depends on: PR 4, PR 5.

Commits:
1. `Define stream event protocol`: `events.py` — typed events `run`, `plan`, `sources`, `draft`, `critique`, `final`, `error`; `to_sse(event)`; mapper from graph updates to events.
2. `Stream research runs over SSE`: `main.py` — `POST /api/research {topic}` (1-300 chars) → `StreamingResponse`: create run, stream events, heartbeat comment every 10s, finish/fail run; `GET /api/runs/{id}`; `GET /api/health`.
3. `Reject clients over the hourly limit`: 429 with `Retry-After` when ≥ 5 runs/hour.
4. `Deploy the API as a Vercel service`: root `vercel.json` with `api` service (`root: backend/`, `entrypoint: main:app`, `maxDuration: 300`) and `/api/(.*)` rewrite.

Tests:
- `test_events.py`: each graph update maps to the right event; `to_sse` output format `event: x\ndata: {...}\n\n`; `final` includes cited sources only.
- `test_api.py` (`TestClient`, fake graph + in-memory repo): events arrive in order `run, plan, sources, draft, critique, final`; run saved as `done`; graph exception → `error` event and run `error`; empty or 301-char topic → 422; 6th request in an hour → 429; `GET /api/runs/{unknown}` → 404; heartbeat emitted when fake graph sleeps past interval (interval patched to 0.05s).

## PR 7: Next.js shell with live run view
Branch `phase1/07-frontend-shell`. Depends on: PR 6.

Check `frontend/node_modules/next/dist/docs/` before assuming Next 16 APIs (`params` is a Promise).

Commits:
1. `Scaffold Next.js frontend`: `create-next-app` (TS, Tailwind, App Router, `src/`), Vitest + Testing Library + jsdom, dark theme tokens ported from `app.py` `:root`, plus motion tokens `--ease-out: cubic-bezier(0.23,1,0.32,1)`, `--ease-in-out: cubic-bezier(0.77,0,0.175,1)`.
2. `Parse the research event stream`: `lib/sse.ts` (chunk-safe parser), `lib/types.ts` (mirrors `events.py`), `lib/runReducer.ts`, `hooks/useResearchRun.ts` (POST fetch + stream reader + abort).
3. `Show live pipeline progress`: `TopicForm`, `PipelineTracker` (Plan, Search/Read, Write, Critic, revision badge), `LiveLog`; `history.replaceState` to `/r/{id}` on `run` event.
4. `Route web and API through Vercel services`: add `web` service and catch-all rewrite to `vercel.json`; README local dev `vercel dev -L`.

Tests (Vitest):
- `sse.test.ts`: event split across chunks; multiple events in one chunk; heartbeat comments ignored; malformed JSON → error event.
- `runReducer.test.ts`: full event sequence reaches `done` with drafts and sources; `error` sets failed state; revision increments badge; duplicate source ids ignored.
- `PipelineTracker.test.tsx`: node states for each step; revision badge text.
- `TopicForm.test.tsx`: empty topic disabled; Enter submits; disabled while running.

## PR 8: Results view, citations, permalinks
Branch `phase1/08-frontend-results`. Depends on: PR 7.

Commits:
1. `Render reports with citation popovers`: `Report` (`react-markdown`), `CitationChip` + popover (Base UI) with source title, domain, excerpt, link; no `dangerouslySetInnerHTML`.
2. `Show score history and rubric`: `ScoreHistory` (`v1 5 → v2 8`), `RubricBars`, `UnsupportedClaims`.
3. `Show sources and earlier drafts`: `SourcesList` (cited vs read-but-uncited), `Drafts` (collapsible), Markdown download.
4. `Add shareable run pages`: `app/r/[id]/page.tsx` server component (`await params`) fetching `GET /api/runs/{id}`, `not-found` for 404.

Tests:
- Vitest: `Report` turns `[2]` into chip linked to source 2; unknown id renders plain text; `<script>` in source excerpt renders as text; `ScoreHistory` shows chips in order; `RubricBars` sets `scaleX` from score; `SourcesList` splits cited vs uncited; download content equals final report.
- Playwright `e2e/run.spec.ts` with `page.route('/api/research')` returning a recorded SSE fixture and `/api/runs/*` fixture: submit topic → tracker advances → report with chips shows → click chip shows popover → URL is `/r/{id}` → reload shows same report.

## PR 9: Motion and interaction polish (Emil Kowalski rules)
Branch `phase1/09-motion-polish`. Depends on: PR 8.

| Before (Streamlit CSS) | After | Why |
| --- | --- | --- |
| `transition: all 0.3s` (`app.py:80,103,264,338,498`) | Named properties (`transform, opacity, border-color, box-shadow`) 200ms `var(--ease-out)` | `all` animates layout and hides intent |
| Hover `translateY(-2px)`, `:active` back to 0 | `:active { scale: 0.97 }` 140ms; hover lift only in `@media (hover: hover) and (pointer: fine)` | Press must confirm the click; hover fires on tap on touch |
| `.fade-in-up` 0.6s, 20px, 100-400ms delays | 260ms `--ease-out`, 8px + opacity, 50ms stagger, first reveal only | Under 300ms feels responsive |
| Pipeline node state swaps instantly | Transition `border-color`/`opacity`; done check enters from `scale(0.95)` + opacity | Nothing appears from nothing |
| `nodePulse` animates `box-shadow` | Pulse pseudo-element `opacity`, 1.6s `ease-in-out` | Constant motion on GPU properties |
| `arrowFlow` wiggle | Connector fill via `clip-path: inset()`, `linear` | Constant progress is linear |
| Score shown once | New chip enters `scale(0.95)` + opacity 200ms; ring fills once | Motion explains the revision story |
| Rubric bars width | `transform: scaleX()`, `transform-origin: left`, 30ms stagger, once | Animate transform, not width |
| Popover default origin | `transform-origin: var(--transform-origin)`, 150ms from `scale(0.97)`; instant for subsequent chips | Origin-aware; fast repeat inspection |
| No reduced-motion | `prefers-reduced-motion`: drop translate/scale/pulse/sweep, keep 150ms opacity | Gentler, not zero |
| Enter-to-submit | No animation on submit itself | Keyboard actions must feel instant |

Commits:
1. `Add motion tokens and press feedback`
2. `Animate pipeline state changes on GPU properties`
3. `Animate score and rubric changes once`
4. `Make citation popovers origin-aware`
5. `Respect reduced motion`

Tests:
- `motion.test.ts` (static CSS/TSX scan): no `transition: all` or `transition-all` in `frontend/src`; no `ease-in` easing (except `ease-in-out`); no `scale(0)`; every hover transform is inside a `(hover: hover)` media query; a `prefers-reduced-motion` block exists.
- Vitest: `RubricBars` animates only when `animate` prop true (first reveal), not on re-render.
- Playwright: `page.emulateMedia({ reducedMotion: 'reduce' })` → pipeline node computed `animation-name` is `none`; button `:active` computed transform is scale 0.97 (via `mouse.down`).

## PR 10: Remove Streamlit, docs, deploy
Branch `phase1/10-cutover`. Depends on: PR 9.

Commits:
1. `Remove the Streamlit app`: delete root `app.py`, `agents.py`, `tools.py`, `pipeline.py`, root `requirements.txt`; update `.devcontainer/devcontainer.json` to Node + Python and `vercel dev -L`.
2. `Document the new architecture and deploy`: README (architecture diagram, env vars `MISTRAL_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`, `WRITER_MODEL`, `CRITIC_MODEL`, local dev, Vercel deploy, Neon migrate), new screenshots.
3. `Add deployed smoke test`: `scripts/smoke.py` — `GET /api/health`, then one short research run against `BASE_URL`, asserts `final` event with ≥1 citation.

Tests: full backend + frontend suites; `scripts/smoke.py` against the Vercel preview URL (user confirms the deploy first; secrets set by the user in Vercel project settings).

---

## End-to-end verification (after PR 10)
1. `cd backend && pytest -q`; `cd frontend && npm run lint && npm test && npm run build && npx playwright test`.
2. `python backend/cli.py` with "how do mRNA vaccines work" and "latest EU AI Act enforcement news": different Tavily topics chosen; ≥4 sources read; `[n]` citations; Sources lists only cited URLs; finishes within 220s budget.
3. `PASS_SCORE=10`: v1-v3 drafts, stops at max revisions or budget.
4. `vercel dev -L` in browser pane: live tracker, score chips, rubric bars, citation popovers, Sources/Drafts, refresh keeps `/r/{id}`, row in Neon `runs`.
5. Vercel preview: `python scripts/smoke.py` passes.
