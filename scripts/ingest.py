import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.models import DashboardSnapshot
from scripts.classify import classify_bounded
from scripts.github_client import fetch_pull_requests, is_bot
from scripts.local_git_client import fetch_local_contributions
from scripts.score import is_substantive_review, rank_engineers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="PostHog/posthog")
    parser.add_argument("--since", type=date.fromisoformat)
    parser.add_argument("--from-cache", type=Path)
    parser.add_argument("--local-repo", type=Path, help="Read complete contribution history from a local Git checkout")
    parser.add_argument("--fetch-only", action="store_true", help="Write raw.json and stop before GPT classification")
    parser.add_argument("--max-gpt-records", type=int, default=500, help="Hard cap for contributor-balanced GPT classification")
    parser.add_argument("--output", type=Path, default=Path("backend/data/dashboard.json"))
    args = parser.parse_args()
    if args.max_gpt_records < 0:
        parser.error("--max-gpt-records must be zero or greater")
    if args.from_cache:
        raw = json.loads(args.from_cache.read_text())
        prs, since = raw["pull_requests"], date.fromisoformat(raw["window_start"])
    else:
        if not args.since: parser.error("--since is required without --from-cache")
        if args.local_repo:
            prs = fetch_local_contributions(args.local_repo, args.repo, args.since, date.today())
            source = "local_git"
        else:
            owner,name = args.repo.split("/",1)
            prs = fetch_pull_requests(owner,name,args.since)
            source = "github_graphql"
        since = args.since
        raw={"repository":args.repo,"source":source,"window_start":since.isoformat(),"window_end":date.today().isoformat(),"pull_requests":prs}
        Path("backend/data/raw.json").write_text(json.dumps(raw,indent=2))
    reviews=sum(1 for pr in prs for review in pr.get("reviews",{}).get("nodes",[]) if not is_bot(review.get("author")) and is_substantive_review(review))
    print(f"coverage: {since}..{date.today()} | PRs: {len(prs)} | authors: {len({p['author']['login'] for p in prs})} | substantive reviews: {reviews}")
    if args.fetch_only:
        print("fetch-only complete: wrote backend/data/raw.json")
        return
    classifications, gpt_count = classify_bounded(prs, args.max_gpt_records)
    print(f"classification: {gpt_count} GPT-assisted | {len(prs) - gpt_count} deterministic baseline | cap {args.max_gpt_records}")
    engineers=rank_engineers(prs,classifications)
    snapshot={"repository":raw.get("repository",args.repo),"window_start":since.isoformat(),"window_end":date.today().isoformat(),"generated_at":datetime.now(timezone.utc).isoformat(),"model":"gpt-5.5","methodology":{"weights":{"impact":40,"complexity":25,"output":20,"ownership":15},"summary":f"GPT-5.5 enriches a contributor-balanced maximum of {args.max_gpt_records} contributions; deterministic baselines cover the complete window and code calculates Output, Ownership, and the final ranking.","limitations":["Public Git evidence cannot capture private planning, mentoring, incident response, reviews, or other invisible work.","Scores compare visible contributions within this repository and time window only.","Unknown file paths receive a conservative component importance of 4/10.",f"GPT enrichment is capped at {args.max_gpt_records} contributions; remaining records use auditable title/path heuristics."]},"engineers":engineers}
    validated=DashboardSnapshot.model_validate(snapshot)
    args.output.write_text(validated.model_dump_json(indent=2))
    print(f"wrote {args.output} with {len(engineers)} ranked engineers")


if __name__ == "__main__": main()
