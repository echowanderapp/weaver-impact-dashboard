import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.models import DashboardSnapshot
from scripts.classify import classify_pull_requests
from scripts.github_client import fetch_pull_requests, is_bot
from scripts.score import is_substantive_review, rank_engineers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="PostHog/posthog")
    parser.add_argument("--since", type=date.fromisoformat)
    parser.add_argument("--from-cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("backend/data/dashboard.json"))
    args = parser.parse_args()
    if args.from_cache:
        raw = json.loads(args.from_cache.read_text())
        prs, since = raw["pull_requests"], date.fromisoformat(raw["window_start"])
    else:
        if not args.since: parser.error("--since is required without --from-cache")
        owner,name = args.repo.split("/",1)
        prs, since = fetch_pull_requests(owner,name,args.since), args.since
        raw={"repository":args.repo,"window_start":since.isoformat(),"window_end":date.today().isoformat(),"pull_requests":prs}
        Path("backend/data/raw.json").write_text(json.dumps(raw,indent=2))
    reviews=sum(1 for pr in prs for review in pr.get("reviews",{}).get("nodes",[]) if not is_bot(review.get("author")) and is_substantive_review(review))
    print(f"coverage: {since}..{date.today()} | PRs: {len(prs)} | authors: {len({p['author']['login'] for p in prs})} | substantive reviews: {reviews}")
    classifications=classify_pull_requests(prs)
    engineers=rank_engineers(prs,classifications)
    snapshot={"repository":raw.get("repository",args.repo),"window_start":since.isoformat(),"window_end":date.today().isoformat(),"generated_at":datetime.now(timezone.utc).isoformat(),"model":"gpt-5.5","methodology":{"weights":{"impact":40,"complexity":25,"output":20,"ownership":15},"summary":"GPT-5.5 assists with Impact and Complexity signals; deterministic code calculates Meaningful Output, Ownership, and the final ranking.","limitations":["Public GitHub evidence cannot capture private planning, mentoring, incident response, or other invisible work.","Scores compare visible contributions within this repository and time window only.","Unknown file paths receive a conservative component importance of 4/10."]},"engineers":engineers}
    validated=DashboardSnapshot.model_validate(snapshot)
    args.output.write_text(validated.model_dump_json(indent=2))
    print(f"wrote {args.output} with {len(engineers)} ranked engineers")


if __name__ == "__main__": main()
