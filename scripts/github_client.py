import os
from datetime import date

import httpx

QUERY = """
query($owner:String!,$name:String!,$cursor:String){
  repository(owner:$owner,name:$name){
    pullRequests(first:50,after:$cursor,orderBy:{field:UPDATED_AT,direction:DESC},states:MERGED){
      pageInfo{hasNextPage endCursor}
      nodes{
        number title body url mergedAt additions deletions changedFiles
        files(first:100){nodes{path}}
        author{__typename login avatarUrl url}
        labels(first:20){nodes{name}}
        closingIssuesReferences(first:10){nodes{number title url}}
        reviews(first:50){nodes{author{__typename login avatarUrl url} body state submittedAt url}}
      }
    }
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
    items: list[dict] = []
    cursor = None
    with httpx.Client(timeout=45) as client:
        while True:
            response = client.post(
                "https://api.github.com/graphql",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": QUERY, "variables": {"owner": owner, "name": name, "cursor": cursor}},
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError(payload["errors"])
            connection = payload["data"]["repository"]["pullRequests"]
            nodes = connection["nodes"]
            for pr in nodes:
                if pr.get("mergedAt") and date.fromisoformat(pr["mergedAt"][:10]) >= since and not is_bot(pr.get("author")):
                    items.append(pr)
            oldest = min((node["mergedAt"][:10] for node in nodes if node.get("mergedAt")), default=None)
            if not connection["pageInfo"]["hasNextPage"] or (oldest and oldest < since.isoformat()):
                break
            cursor = connection["pageInfo"]["endCursor"]
    return items
