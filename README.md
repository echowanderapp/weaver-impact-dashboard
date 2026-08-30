# PostHog Engineering Impact Dashboard

An evidence-backed top-five ranking over a fixed 90-day PostHog GitHub snapshot. GPT-5.5 assists with Impact and Complexity; deterministic code calculates Meaningful Output and component Ownership. The final score applies weights of 40%, 25%, 20%, and 15% respectively.

Impact combines component importance (50%), change significance (30%), and blast radius (20%). Complexity combines logic (35%), architecture (30%), cross-component reach (20%), and change scope (15%). Output is the contributor percentile of meaningful PR value. Ownership combines component frequency (40%), continuity (30%), and contribution share (30%), weighted by component importance.

## Generate data

```bash
python3 -m pip install -r scripts/requirements.txt -r backend/requirements.txt
GITHUB_TOKEN=... OPENAI_API_KEY=... OPENAI_MODEL=gpt-5.5 python3 scripts/ingest.py --repo PostHog/posthog --since 2026-06-01
```

For a complete local-history scan without GitHub pagination or search limits:

```bash
python3 scripts/ingest.py --repo PostHog/posthog --local-repo posthog --since 2026-06-01 --fetch-only
OPENAI_API_KEY=... OPENAI_MODEL=gpt-5.5 python3 scripts/ingest.py --from-cache backend/data/raw.json --max-gpt-records 500 --output backend/data/dashboard.json
```

The checkout must be non-shallow and current. Local Git is authoritative for commits, file paths, diffs, authors, and active weeks; PR numbers are extracted from squash-commit subjects when available. GitHub reviews, labels, and linked issues are unavailable in local-only mode.

The GPT pass is hard-capped at 500 contributions by default. Every contribution first receives a deterministic conventional-commit/path baseline. Generated and documentation-only changes remain deterministic. GPT capacity is allocated across contributors before remaining slots are filled by likely significance, so repository volume cannot silently increase LLM cost.

## Run locally

```bash
uvicorn backend.app.main:app --port 8000
VITE_API_BASE_URL=http://localhost:8000 npm --prefix frontend run dev
```

## Railway

Create two services from this repository. Set the backend root to `backend` and frontend root to `frontend`. Set frontend `VITE_API_BASE_URL` to the backend public origin and backend `FRONTEND_ORIGIN` to the frontend public origin. The public services need no GitHub or OpenAI credentials because they serve the generated snapshot.

Dashboard URL: https://frontend-production-912a.up.railway.app

Elapsed implementation time: timer value to be recorded at submission.

## Limitation

The ranking estimates visible repository impact. It cannot observe private planning, mentoring, incident response, or work performed outside the public repository.
