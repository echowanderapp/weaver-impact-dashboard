# Engineering Impact Dashboard MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy an evidence-backed, single-page ranking of the five most impactful PostHog engineers using a reproducible 90-day GitHub snapshot.

**Architecture:** A one-time Python ingestion command fetches GitHub data, obtains structured GPT-5.5 classifications, applies deterministic weights, and writes a JSON snapshot. A Railway-hosted FastAPI service exposes the snapshot to a Railway-hosted React/Vite dashboard; no external dependency is called during page requests.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, OpenAI Responses API, React 19, TypeScript, Vite, plain CSS, Railway

**Spec:** `docs/superpowers/specs/2026-08-30-engineering-impact-dashboard-design.md`

## Global Constraints

- Total implementation time is 80 minutes; stop feature work at minute 72.
- Deploy frontend and backend as separate Railway services.
- Use model identifier `gpt-5.5`, configured through `OPENAI_MODEL` with `gpt-5.5` as the default.
- Include all merged pull-request data from an explicit, inclusive 90-day window.
- GPT-5.5 classifies evidence but never directly ranks engineers.
- The public request path must not require GitHub or OpenAI.
- Do not add a database, authentication, scheduled refresh, filters, or automated test suite.
- Verification is snapshot validation, API smoke calls, frontend production build, and manual deployed-page inspection.

---

### Task 1: Establish the Snapshot Contract and Deployable Skeleton (0–10 minutes)

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/models.py`
- Create: `backend/app/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/Procfile`
- Create: `backend/data/dashboard.json`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/Procfile`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Produces: `DashboardSnapshot`, `Engineer`, `DimensionScores`, and `Evidence` in matching Python and TypeScript shapes.
- Produces: `GET /health` and `GET /api/dashboard`.
- Produces: frontend environment variable `VITE_API_BASE_URL` and backend variable `FRONTEND_ORIGIN`.

- [ ] **Step 1: Define the shared JSON shape in Pydantic and TypeScript**

Use these fields consistently in `backend/app/models.py` and `frontend/src/types.ts`:

```text
DashboardSnapshot
  repository: string
  window_start: YYYY-MM-DD string
  window_end: YYYY-MM-DD string
  generated_at: ISO-8601 string
  model: string
  methodology: { weights: DimensionScores; summary: string; limitations: string[] }
  engineers: Engineer[]

Engineer
  rank: integer
  login: string
  name: string | null
  avatar_url: string
  profile_url: string
  score: number
  strongest_dimension: "outcome" | "complexity" | "leverage" | "ownership"
  dimensions: DimensionScores
  confidence: number
  summary: string
  authored_prs: integer
  substantive_reviews: integer
  evidence: Evidence[]

DimensionScores
  outcome: number
  complexity: number
  leverage: number
  ownership: number

Evidence
  title: string
  url: string
  kind: "pull_request" | "review"
  explanation: string
  impact_score: number
```

- [ ] **Step 2: Create a valid five-engineer placeholder snapshot**

Write `backend/data/dashboard.json` using the exact contract, visibly label its summaries as sample data, and include five distinct engineers so frontend work can start before ingestion finishes.

- [ ] **Step 3: Implement the FastAPI read-only service**

In `backend/app/main.py`, load and validate `data/dashboard.json` once during startup, configure CORS from `FRONTEND_ORIGIN`, return health status from `/health`, and return the parsed snapshot from `/api/dashboard`.

- [ ] **Step 4: Scaffold the Vite application and data fetch**

In `frontend/src/App.tsx`, fetch `${import.meta.env.VITE_API_BASE_URL}/api/dashboard`, store loading/error/data state, and render temporary JSON when successful. Add scripts `dev`, `build`, and `start`; implement `start` with `vite preview --host 0.0.0.0 --port $PORT`.

- [ ] **Step 5: Smoke-check both skeletons**

Run:

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/dashboard
npm --prefix frontend install
npm --prefix frontend run build
```

Expected: health reports `ok`, the dashboard response contains five sample engineers, and Vite exits with a successful build.

- [ ] **Step 6: Commit the deployable skeleton**

```bash
git add backend frontend .env.example .gitignore
git commit -m "chore: scaffold impact dashboard services"
```

### Task 2: Ingest Complete 90-Day GitHub Evidence (10–30 minutes)

**Files:**
- Create: `scripts/requirements.txt`
- Create: `scripts/github_client.py`
- Create: `scripts/ingest.py`

**Interfaces:**
- Consumes: `GITHUB_TOKEN`, CLI flags `--repo` and `--since`.
- Produces: `PullRequestEvidence` records containing PR metadata, reviews, and linked issues.
- Produces: raw intermediate file `backend/data/raw.json` for reruns without another GitHub fetch.

- [ ] **Step 1: Implement a paginated GitHub GraphQL client**

Create `fetch_pull_requests(owner: str, name: str, since: date) -> list[dict]` in `scripts/github_client.py`. Query merged PRs ordered by newest first in pages of 50. Request author identity, title, body, URL, merge time, labels, additions, deletions, changed files, closing issues, and the first 50 reviews with author, body, state, and submission time. Continue PR pagination until a page's oldest merge precedes `since`; filter the final list with `mergedAt >= since at 00:00:00Z`.

- [ ] **Step 2: Normalize identities and exclude automation**

Create `is_bot(author: dict) -> bool` using GitHub typename `Bot` plus login suffixes `[bot]`, `-bot`, and `_bot`. Drop PRs without a human author. Drop reviews from bots, the PR author, or outside the requested window.

- [ ] **Step 3: Mark substantive reviews conservatively**

Create `is_substantive_review(review: dict) -> bool` that returns true for `CHANGES_REQUESTED`, or for a non-empty review body of at least 80 characters. Preserve these reviews for leverage evidence; do not award credit for approvals with no explanation.

- [ ] **Step 4: Write the raw cache and print coverage statistics**

Implement `python scripts/ingest.py --repo PostHog/posthog --since YYYY-MM-DD`. Write `backend/data/raw.json` containing the exact window, fetched PRs, and normalized reviews. Print total PRs, oldest and newest merge dates, human authors, and substantive reviews. Exit nonzero if the oldest included date is after the requested date while GitHub still reported older pages, because that signals incomplete pagination.

- [ ] **Step 5: Run the fetch**

```bash
python -m pip install -r scripts/requirements.txt
python scripts/ingest.py --repo PostHog/posthog --since 2026-06-01
```

For the planned 2026-08-30 execution, `2026-06-01` is the exact 90-day start date. If execution occurs later, recompute the date before starting the timer. Expected: `raw.json` exists and the printed window covers the requested start through today.

- [ ] **Step 6: Commit ingestion**

```bash
git add scripts backend/data/raw.json
git commit -m "feat: ingest PostHog contribution evidence"
```

### Task 3: Classify Evidence with GPT-5.5 and Calculate Rankings (30–43 minutes)

**Files:**
- Create: `scripts/classify.py`
- Create: `scripts/score.py`
- Modify: `scripts/ingest.py`
- Replace: `backend/data/dashboard.json`

**Interfaces:**
- Consumes: `backend/data/raw.json`, `OPENAI_API_KEY`, and optional `OPENAI_MODEL`.
- Produces: strict `Classification` objects with integer `outcome`, `complexity`, `leverage`, `ownership` in `[0,4]`, float `confidence` in `[0,1]`, up to three tags, and an explanation of at most 240 characters.
- Produces: the final `DashboardSnapshot` contract from Task 1.

- [ ] **Step 1: Implement schema-constrained batch classification**

In `scripts/classify.py`, use the OpenAI Responses API and `OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")`. Send batches of no more than 20 compact PR records. Instruct the model to judge demonstrated outcomes rather than size or activity, treat additions/deletions as context only, and return one schema-valid classification per PR number. Retry once on API or schema failure; after a second failure assign all dimensions `1`, confidence `0.2`, tag `unclassified`, and a transparent fallback explanation.

- [ ] **Step 2: Implement deterministic aggregation**

In `scripts/score.py`, implement:

```python
WEIGHTS = {"outcome": 0.40, "complexity": 0.25, "leverage": 0.20, "ownership": 0.15}
```

For authored PRs, sum `rating * confidence` per dimension and apply `log1p` to each contributor's sum. For substantive reviews, add `0.25 * confidence` to leverage and `0.10 * confidence` to ownership for the review author. Min-max normalize each dimension across eligible contributors to 0–100, using 50 when all values in a dimension are equal. Compute the weighted total, sort by total descending then outcome descending then login ascending, and retain five.

- [ ] **Step 3: Select auditable evidence and generate summaries**

For every finalist, select the three authored PRs with the highest weighted classification score. If the engineer has substantive review leverage and fewer than three authored items, fill remaining positions with their strongest reviews. Build a one-sentence summary from the top evidence explanations and strongest dimension; do not make a second LLM request.

- [ ] **Step 4: Generate and validate the production snapshot**

Extend `scripts/ingest.py` with `--from-cache` and `--output`. Load `raw.json`, classify, score, assign ranks 1–5, attach methodology and limitations from the design spec, validate through `backend.app.models.DashboardSnapshot`, then overwrite `backend/data/dashboard.json`.

Run:

```bash
OPENAI_MODEL=gpt-5.5 python scripts/ingest.py --from-cache backend/data/raw.json --output backend/data/dashboard.json
python -c 'from backend.app.models import DashboardSnapshot; import json; DashboardSnapshot.model_validate(json.load(open("backend/data/dashboard.json"))); print("snapshot valid")'
```

Expected: `snapshot valid`; the JSON contains five ranked engineers and two or three evidence links for each.

- [ ] **Step 5: Commit ranking output**

```bash
git add scripts backend/data/dashboard.json
git commit -m "feat: rank engineers from impact evidence"
```

### Task 4: Build the Single-Screen Dashboard (43–63 minutes)

**Files:**
- Create: `frontend/src/components/RankCard.tsx`
- Create: `frontend/src/components/ImpactChart.tsx`
- Create: `frontend/src/components/EngineerDetail.tsx`
- Create: `frontend/src/components/MethodologyDrawer.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `DashboardSnapshot` and `Engineer` from `frontend/src/types.ts`.
- Produces: keyboard-accessible engineer selection and methodology disclosure with no route changes.

- [ ] **Step 1: Implement the page shell and states**

Render a header containing `PostHog Engineering Impact`, the exact snapshot window, and generation time. Render concise loading text, an actionable API-error panel, and an empty-state message. Keep the content at `max-width: 1440px` with a dark neutral palette and one warm accent color.

- [ ] **Step 2: Implement the top-five ranking rail**

Render five `RankCard` buttons with rank, avatar, name/login, score, strongest dimension, and summary. Select rank one initially. Use visible focus and selected states; selecting a card updates the detail panel.

- [ ] **Step 3: Implement selected-engineer evidence**

Render `ImpactChart` as four labeled horizontal bars from 0–100 rather than a hard-to-read radar chart. Below it, render two or three evidence links with title, kind, explanation, and impact score. Open GitHub links in a new tab with safe `rel` attributes.

- [ ] **Step 4: Implement methodology disclosure**

Render a button that opens `MethodologyDrawer`. Include the four exact weights, two-stage LLM-plus-deterministic calculation, bot and shallow-review exclusions, confidence meaning, and all snapshot limitations. Close via button, Escape, or backdrop.

- [ ] **Step 5: Fit the laptop viewport and build**

Use a two-column layout above 960px and stacked layout below it. Keep summaries to two lines and evidence compact enough that the primary ranking plus selected details are visible without excessive scrolling at 1440×900.

Run:

```bash
npm --prefix frontend run build
```

Expected: TypeScript and Vite complete successfully with no missing environment-variable compile error.

- [ ] **Step 6: Commit the dashboard**

```bash
git add frontend
git commit -m "feat: present evidence-backed impact ranking"
```

### Task 5: Deploy Two Railway Services and Smoke-Test (63–80 minutes)

**Files:**
- Create: `backend/railway.json`
- Create: `frontend/railway.json`
- Create: `README.md`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: Railway-provided `PORT`, frontend `VITE_API_BASE_URL`, and backend `FRONTEND_ORIGIN`.
- Produces: public backend health/API URLs and a public frontend dashboard URL.

- [ ] **Step 1: Make service commands Railway-safe**

Set backend start to `uvicorn app.main:app --host 0.0.0.0 --port $PORT` when the Railway root is `backend`. Set frontend build to `npm ci && npm run build` and start to `npm run start -- --host 0.0.0.0 --port $PORT`. Configure `/health` as the backend health-check path.

- [ ] **Step 2: Create the Railway project and backend service**

From the repository root, link or initialize a Railway project. Create a backend service rooted at `backend`, deploy it, and wait until `/health` returns HTTP 200. Record its generated public domain.

- [ ] **Step 3: Create and deploy the frontend service**

Create a frontend service rooted at `frontend`. Set `VITE_API_BASE_URL` to the backend's HTTPS origin, deploy it, and record its public domain.

- [ ] **Step 4: Lock backend CORS and redeploy if required**

Set backend `FRONTEND_ORIGIN` to the frontend's exact HTTPS origin. Redeploy backend and confirm a request bearing that `Origin` receives the matching `Access-Control-Allow-Origin` response.

- [ ] **Step 5: Perform final smoke verification**

Run:

```bash
curl -fsS https://BACKEND_DOMAIN/health
curl -fsS https://BACKEND_DOMAIN/api/dashboard
curl -fsSI https://FRONTEND_DOMAIN/
```

Expected: health is `ok`, the dashboard response has five engineers and the exact 90-day dates, and the frontend returns HTTP 200. Open the frontend at laptop width; select ranks two and five, open and close methodology, follow one evidence URL, and confirm there are no browser-console errors.

- [ ] **Step 6: Write submission and reproduction instructions**

In `README.md`, record the public dashboard URL, a short approach description, exact elapsed timer value, environment-variable names, local ingestion command, local run commands, impact weights, and limitations. Never include secret values.

- [ ] **Step 7: Commit deployment documentation**

```bash
git add backend/railway.json frontend/railway.json README.md
git commit -m "docs: add Railway deployment and submission guide"
```

## Cutoff Rules

If behind schedule, preserve correctness and deployment in this order:

1. At minute 30, use the raw cache even if linked-issue fields are sparse.
2. At minute 43, classify only the most recent 200 qualifying PRs with GPT-5.5, but retain all 90-day PRs in counts and label unclassified evidence transparently.
3. At minute 63, use CSS bars instead of adding or debugging a chart library.
4. At minute 72, stop all UI refinement and deploy the last successful build.
5. Never cut pagination completeness, evidence links, methodology disclosure, snapshot validation, or public URL smoke checks.
