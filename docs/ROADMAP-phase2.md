# ResearchCrew Phase 2: steerable, signed-in, and accountable

Phase 1 made a report you can trust: cited, fact-checked, revised when weak, saved
with a permalink. Phase 2 makes it a product people come back to.

Three things are missing:

- **You cannot steer it.** The planner's sub-questions are invisible; you type a
  topic and hope. Steerability is the edge over black-box deep-research tools.
- **Runs belong to nobody.** `/r/{id}` works if you kept the link. There is no
  "my research", and the rate limit counts a hashed IP, which is both leaky and
  easy to dodge.
- **Nobody knows what a run costs.** Not the user, not us. Tokens, time and
  which sources were rejected all vanish.

Phase 2 fixes those, in that order, and closes with the panel that shows the
whole run.

## How to use this plan

Prompt **"Implement PR N from docs/ROADMAP-phase2.md"**. Each PR: branch from
latest `main` with the listed name, make the listed commits in order, write the
listed tests with the code they cover, open the PR against `main`. **No Claude
attribution trailers.**

Checks per commit: `cd backend && pytest -q`; `cd frontend && npm run lint && npm test && npm run build`. Browser tests before opening a frontend PR: `npx playwright test`.

## Architecture change behind PRs 1-2

Today the browser calls the Python service directly (`vercel.json` rewrites
`/api/*` to it) and anyone with the URL can spend your Tavily and Mistral credit.
Phase 2 puts the session in front of it:

```
browser → Next.js route handler /api/*  →  Python service (private)
            (Auth.js session cookie)        (verifies a signed user token)
```

The Python service stops being publicly routed and is reached through a Vercel
**service binding**, whose internal URL arrives as an environment variable. The
Next handler streams the response through untouched, so SSE still works. Locally
the existing `API_PROXY` variable plays the same role.

---

## PR 1: Put the API behind the app
Branch `phase2/01-private-api`. Depends on: none.

Commits:
1. `Proxy API calls through the web app`: `frontend/src/app/api/[...path]/route.ts` —
   forwards method, body and relevant headers to `process.env.API_INTERNAL_URL`
   (falling back to `API_PROXY` locally), returns `response.body` as a stream so
   SSE passes through, forwards status and `Retry-After`. `export const maxDuration = 300`.
2. `Stop exposing the Python service publicly`: `vercel.json` — drop the
   `/api/(.*)` rewrite, add a binding from `web` to `api`; `lib/api.ts` calls the
   internal URL directly on the server. README updated.

Tests:
- `route.test.ts` (mocked `fetch`): POST body and method forwarded; a streamed
  body is piped through unbuffered; 429 keeps its status and `Retry-After`; a
  failed upstream fetch becomes a 502 with a readable message; hop-by-hop headers
  are not forwarded.
- Playwright: existing suite still passes against the stub (it already proxies).

## PR 2: Sign in with Google
Branch `phase2/02-google-sign-in`. Depends on: PR 1.

Commits:
1. `Add Google sign-in`: `next-auth@beta` (v5, supports Next 16) with the Google
   provider and JWT sessions; `auth.ts`, `app/api/auth/[...nextauth]/route.ts`,
   a header account menu, sign-in page. `AUTH_SECRET`, `AUTH_GOOGLE_ID`,
   `AUTH_GOOGLE_SECRET`.
2. `Identify the caller to the API`: the proxy mints a short-lived HS256 token
   (`sub`, `email`, 5 min) signed with `API_TOKEN_SECRET` and sends it as a
   bearer token. Anonymous visitors get no token.
3. `Scope runs to the person who ran them`: `migrations/002_users.sql` —
   `runs.user_id text`, indexed with `created_at`; FastAPI verifies the token
   (`python-jose` or `pyjwt`), stores `user_id`, and counts the hourly limit per
   user (20/hour) or per hashed IP when signed out (5/hour, as now).
4. `Let a report be opened only by its owner`: `GET /api/runs/{id}` returns a run
   to its owner, and to anyone when `user_id` is null (Phase 1 runs stay
   readable).

Tests:
- Backend `test_auth.py`: valid token accepted; expired, wrong-secret and
  malformed tokens rejected with 401; missing token stays anonymous; per-user
  limit applies to the user and not their IP; a run's owner can read it, another
  user gets 404, an anonymous run stays readable.
- Frontend: signed-out header shows "Sign in"; signed-in shows the account menu;
  the proxy attaches a bearer token when a session exists and none when it does
  not.
- **Secrets are yours to create**: a Google OAuth client (authorized redirect
  `https://<domain>/api/auth/callback/google` and `http://localhost:3000/...`),
  `AUTH_SECRET`, `API_TOKEN_SECRET`.

## PR 3: Edit the plan before it runs
Branch `phase2/03-editable-plan`. Depends on: PR 1.

The planner's queries become a step you approve. This is the steerability that
black-box tools do not offer.

Commits:
1. `Plan a topic without running it`: split the graph — `POST /api/plan {topic}`
   returns a `SearchPlan` (one model call, a few seconds, no search). Graph gains
   an entry that accepts ready-made queries and skips the `plan` node.
2. `Run an approved plan`: `POST /api/research` accepts optional `queries`; when
   present the run starts from `search_and_read`. Validation: 1-6 queries, each
   1-200 characters, topic still required for the writer.
3. `Show the plan and let it be changed`: `PlanEditor` — each query editable,
   removable, with news/general and a day window; add a query; "Start research"
   or "Skip and run as planned". Remembers the last choice per session.

Tests:
- Backend: `/api/plan` returns queries and creates no run row; `/api/research`
  with supplied queries never calls the planner chain; 7 queries or a 201-character
  query → 422; graph test: supplied queries are searched verbatim.
- Frontend: editing a query updates the payload; removing the last query disables
  start; adding a query defaults to `general`; skipping sends no `queries`.
- Playwright: plan appears, a query is edited, the run uses the edited text (the
  stub echoes queries into the log).

## PR 4: A library of your runs
Branch `phase2/04-library`. Depends on: PR 2.

Commits:
1. `List and delete your runs`: `GET /api/runs?limit&cursor&q` — the caller's
   runs, newest first, keyset pagination, optional topic search
   (`topic ilike %q%`), returning topic, score, status, created_at, elapsed and
   source count. `DELETE /api/runs/{id}` for the owner.
2. `Add the library page`: `/library` — cards with topic, score chip, date and
   source count; search box; empty state; delete with an undo window; "Run again"
   prefills the topic.
3. `Link the library from the run view`, and show "saved to your library" once a
   signed-in run finishes.

Tests:
- Backend: only the caller's runs are listed; ordering and keyset paging;
  search matches case-insensitively; delete removes it and 404s for a stranger;
  anonymous callers get an empty list.
- Frontend: cards render score colour by band; empty state; search filters;
  delete calls the endpoint and removes the card.
- Playwright: library lists a run, search narrows it, delete removes it.

## PR 5: Know what a run costs
Branch `phase2/05-cost-tracking`. Depends on: PR 1.

Commits:
1. `Record tokens and time per step`: a LangChain callback handler collects
   prompt and completion tokens per chain; the graph records elapsed time per
   node; Tavily calls counted (searches and extracts).
2. `Price a run`: a small per-model price table (`research/pricing.py`, rates in
   config so they can be corrected without a deploy) turning tokens into a cost;
   `runs.usage jsonb` stores per-step tokens, cost, seconds, and search counts.
3. `Show the cost with the result`: one line under the report — "42s · 8.2k
   tokens · $0.004 · 6 sources" — and in the `final` event.

Tests:
- Backend: handler sums tokens per chain and keeps writer and critic separate;
  pricing maths for known and unknown models (unknown → cost `null`, never a
  wrong number); usage survives the JSON round-trip; a revision's tokens are
  added, not replaced.
- Frontend: the summary line formats tokens and cost, and omits cost when it is
  unknown.

## PR 6: Show your work
Branch `phase2/06-transparency-panel`. Depends on: PR 5.

Commits:
1. `Keep the sources that were considered`: the graph records every search result
   it saw with the reason it was dropped (duplicate domain, already read,
   unreadable, outranked), stored as `runs.considered jsonb`.
2. `Add the run timeline`: a panel with each step, its duration, tokens and cost,
   the queries issued, and sources used vs rejected with the reason; the revision
   loop shown as branches rather than a flat list.
3. `Open the panel from a finished run`, collapsed by default.

Tests:
- Backend: each drop reason recorded once per URL; considered sources exclude
  page text; a run with no rejects records an empty list.
- Frontend: timeline orders steps by start; rejected sources show their reason;
  the panel is collapsed until opened.
- Playwright: the panel opens and shows a rejected source with a reason.

## PR 7: Docs and deployment
Branch `phase2/07-docs`. Depends on: PR 6.

Commits:
1. `Document sign-in and the new environment`: README — Google OAuth setup, the
   new variables, the private-API topology, and a diagram of the two services.
2. `Extend the smoke test`: `scripts/smoke.py` also checks that the API rejects an
   unsigned request, that `/api/plan` returns queries, and that usage is recorded.
3. `Refresh the screenshots` from the stubbed run, including the plan editor,
   library and transparency panel.

## New environment variables

| Variable | Where | Purpose |
| --- | --- | --- |
| `AUTH_SECRET` | web | Signs the session cookie |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | web | Google OAuth client |
| `API_TOKEN_SECRET` | web + api | Signs the short-lived user token; **must match** |
| `API_INTERNAL_URL` | web | Injected by the Vercel service binding |
| `PRICE_PER_MTOK_*` | api | Optional price overrides per model |

`API_TOKEN_SECRET` mismatching between the two services fails only at request
time, never at build time — the same trap as a shared JWT secret anywhere else.

## Definition of done

- Signing in with Google lists your own runs, and the Python service answers
  nothing without a valid token.
- A run can be steered: the plan is visible and editable before any search runs.
- Every finished run shows what it cost and, on demand, every source it
  considered and why each was dropped.
- `pytest`, `vitest`, `playwright`, `lint` and `build` all pass; `scripts/smoke.py`
  passes against a deployment.
