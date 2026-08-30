# Engineering Impact Dashboard MVP Design

## Objective

Build and deploy, within 80 minutes, a single-page dashboard that identifies the five most impactful engineers in the public PostHog GitHub repository using at least the latest 90 days of data. The result must load quickly, explain every ranking with linked evidence, and remain useful even when GitHub or OpenAI is unavailable.

## Scope

The MVP contains a one-time ingestion pipeline, deterministic ranking logic, a read-only backend, and a laptop-focused frontend. The frontend and backend deploy as separate Railway services from one repository.

The MVP excludes authentication, a database, scheduled refreshes, live GitHub requests from the user-facing application, administration, arbitrary date filters, and automated test suites. Verification consists of snapshot validation, API smoke calls, a production frontend build, and manual inspection of the deployed page.

## Architecture

The repository contains three focused areas:

- `scripts/` fetches public GitHub data, asks GPT-5.5 for structured classifications, calculates rankings, and writes a versioned JSON snapshot.
- `backend/` loads that snapshot at startup and exposes health, dashboard, and methodology endpoints through FastAPI.
- `frontend/` fetches the dashboard payload and renders the complete experience on one responsive page.

The deployed request path reads only the precomputed snapshot. GitHub and OpenAI credentials are needed for ingestion but are not required by either public service.

## Data Window and Inputs

The ingestion command accepts an explicit `--since` date and defaults to the UTC date 90 days before execution. It records inclusive `window_start`, `window_end`, repository identity, and generation time in the snapshot.

GitHub GraphQL supplies merged pull requests and their authors, titles, bodies, URLs, merge timestamps, labels, additions, deletions, changed-file counts, review authors, review bodies, review states, and linked closing issues where available. Pagination continues until all qualifying pull requests in the window are collected. Bot and automation accounts are excluded using GitHub's bot type plus a conservative login-pattern fallback.

## Impact Method

Impact is modeled through four dimensions rather than raw activity:

- Impact, 40%: `0.5 × ComponentImportance + 0.3 × ChangeSignificance + 0.2 × BlastRadius`.
- Complexity, 25%: `0.35 × Logic + 0.30 × Architecture + 0.20 × CrossComponent + 0.15 × ChangeScope`.
- Meaningful Output, 20%: percentile-normalized sum of completed PR values, where major features are worth 5 and trivial/generated changes are worth 0.
- Ownership, 15%: `0.4 × Frequency + 0.3 × Continuity + 0.3 × ComponentShare`, weighted by component importance.

GPT-5.5 receives compact PR evidence and returns strict JSON containing change significance, blast radius, four complexity signals, PR value, confidence, impact tags, and a short explanation. It does not score ownership or rank engineers. Invalid output is retried once; a second failure produces a conservative, low-confidence classification so one PR cannot stop ingestion.

Deterministic code aggregates classified authored PRs and substantive reviews. Per-engineer dimension values are normalized against the observed contributor distribution, combined using the published weights, and rounded to a 0–100 score. Extreme activity is dampened so volume alone cannot dominate. The final top five are selected by total score, then outcome score, then login for stable ties.

Each ranked engineer includes a concise explanation, dimension breakdown, confidence, contribution counts for context only, and two or three highest-value evidence links. The UI explicitly states that public repository evidence cannot capture private planning, mentoring, incident response, or other invisible work.

## API Contract

`GET /health` returns `{ "status": "ok" }` after the snapshot has loaded.

`GET /api/dashboard` returns metadata, methodology, and exactly the top five ranked engineers when at least five eligible contributors exist. The backend serves stable JSON and permits the configured frontend origin through CORS.

The process fails during startup with an actionable message if the snapshot is missing or violates its Pydantic schema.

## Dashboard Experience

The page fits its primary content within a typical laptop viewport. It contains:

- A compact header with repository, exact date range, generation time, and a methodology button.
- Five rank cards showing identity, total score, strongest dimension, and one-sentence reason.
- A detail panel for the selected engineer with a four-dimension horizontal chart and linked evidence.
- A methodology drawer explaining weights, calculation stages, GPT-5.5's limited role, exclusions, and limitations.

The first-ranked engineer is selected by default. Selecting another card updates the detail panel without navigation. Loading, API failure, and empty-data states use plain, actionable copy.

## Deployment

Railway hosts two services sourced from the same repository:

- Backend service root: `backend`; build installs Python dependencies; start runs Uvicorn on Railway's `PORT`; health check is `/health`.
- Frontend service root: `frontend`; build runs the Vite production build; start serves `dist` with SPA fallback on Railway's `PORT`.

The frontend receives `VITE_API_BASE_URL` at build time. The backend receives `FRONTEND_ORIGIN` for CORS. The generated snapshot is included with the backend deployment artifact. `GITHUB_TOKEN` and `OPENAI_API_KEY` remain local ingestion variables and are not placed in public service environments.

## Verification and Time Budget

The implementation must stop expanding scope at 72 minutes and preserve the final eight minutes for deployment and smoke verification.

- 0–10 minutes: scaffold shared contract, backend, frontend, and Railway commands.
- 10–30 minutes: GitHub ingestion and contributor aggregation.
- 30–43 minutes: GPT-5.5 classification and deterministic scoring.
- 43–63 minutes: single-page dashboard.
- 63–72 minutes: Railway deployment.
- 72–80 minutes: health call, dashboard call, page inspection, and submission notes.

Success means both Railway URLs are publicly reachable, the page loads in under ten seconds, five engineers are ranked, every rank has understandable evidence, and the methodology explains exactly how the values were produced.
