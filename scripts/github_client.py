import os
from datetime import date, timedelta

import httpx

QUERY = """
query($query:String!,$cursor:String){
  search(query:$query,type:ISSUE,first:100,after:$cursor){
    issueCount pageInfo{hasNextPage endCursor}
    nodes{... on PullRequest{
      number title body url mergedAt updatedAt additions deletions changedFiles
      author{__typename login avatarUrl url}
      labels(first:20){nodes{name}}
      closingIssuesReferences(first:10){nodes{number title url}}
      reviews(first:20){nodes{author{__typename login avatarUrl url} body state submittedAt url}}
    }}
  }
}
"""


def is_bot(author: dict | None) -> bool:
    if not author:
        return True
    login = author.get("login", "").lower()
    return author.get("__typename") == "Bot" or login.endswith(("[bot]", "-bot", "_bot"))


def fetch_pull_requests(owner: str, name: str, since: date) -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    by_number: dict[int, dict] = {}
    window_start = since
    today = date.today()
    with httpx.Client(timeout=120) as client:
        while window_start <= today:
            window_end = window_start
            search = f"repo:{owner}/{name} is:pr is:merged merged:{window_start.isoformat()}..{window_end.isoformat()} sort:created-asc"
            cursor = None
            while True:
                last_error: Exception | None = None
                for _ in range(3):
                    try:
                        response = client.post(
                            "https://api.github.com/graphql",
                            headers={"Authorization": f"Bearer {token}"},
                            json={"query": QUERY, "variables": {"query": search, "cursor": cursor}},
                        )
                        break
                    except (httpx.ReadTimeout, httpx.ConnectError) as exc:
                        last_error = exc
                else:
                    raise RuntimeError(f"GitHub request failed after 3 attempts: {last_error}")
                response.raise_for_status()
                payload = response.json()
                if payload.get("errors"):
                    raise RuntimeError(payload["errors"])
                connection = payload["data"]["search"]
                if connection["issueCount"] > 1000:
                    raise RuntimeError(f"GitHub search slice {window_start}..{window_end} exceeds 1,000 results")
                for pr in connection["nodes"]:
                    if pr and pr.get("mergedAt") and not is_bot(pr.get("author")):
                        by_number[pr["number"]] = pr
                if not connection["pageInfo"]["hasNextPage"]:
                    break
                cursor = connection["pageInfo"]["endCursor"]
            window_start = window_end + timedelta(days=1)
    return sorted(by_number.values(), key=lambda pr: pr["mergedAt"], reverse=True)
