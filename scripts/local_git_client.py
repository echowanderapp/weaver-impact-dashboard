import re
import subprocess
from hashlib import sha256
from datetime import date
from pathlib import Path
from urllib.parse import quote

PR_NUMBER = re.compile(r"\(#(\d+)\)\s*$")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _identity(name: str, email: str) -> dict[str, str]:
    normalized_email = email.strip().lower()
    name_slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "unknown"
    identity_hash = sha256(normalized_email.encode()).hexdigest()[:6]
    login = f"{name_slug}-{identity_hash}"
    return {
        "__typename": "User",
        "login": login,
        "name": name.strip() or login,
        "email": normalized_email,
        "avatarUrl": f"https://github.com/{quote(login)}.png",
        "url": f"https://github.com/search?q={quote(normalized_email)}&type=users",
    }


def _commit_record(repository: str, header: str, changed_paths: list[str], ordinal: int) -> dict:
    fields = header.split("\x1f", 4)
    sha, name, email, authored_at, title = (fields + [""] * 5)[:5]
    body = ""
    file_rows = [line.strip() for line in changed_paths if line.strip()]
    additions = deletions = 0
    match = PR_NUMBER.search(title)
    pr_number = int(match.group(1)) if match else 1_000_000_000 + ordinal
    evidence_url = f"https://github.com/{repository}/pull/{match.group(1)}" if match else f"https://github.com/{repository}/commit/{sha}"
    return {
        "number": pr_number,
        "oid": sha,
        "title": title.strip(),
        "body": body.strip(),
        "url": evidence_url,
        "mergedAt": authored_at.strip(),
        "additions": additions,
        "deletions": deletions,
        "changedFiles": len(file_rows),
        "author": _identity(name, email),
        "labels": {"nodes": []},
        "closingIssuesReferences": {"nodes": []},
        "reviews": {"nodes": []},
        "files": {"nodes": [{"path": path} for path in file_rows[:100]]},
        "diffExcerpt": "",
        "source": "local_git",
    }


def fetch_local_contributions(repo_path: str | Path, repository: str, since: date, until: date) -> list[dict]:
    repo = Path(repo_path).resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"{repo} is not a Git checkout")
    if _git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise RuntimeError("Local PostHog checkout is shallow; run git -C posthog fetch --unshallow origin")
    output = _git(
        repo,
        "log",
        "--first-parent",
        "--use-mailmap",
        f"--since={since.isoformat()}T00:00:00Z",
        f"--until={until.isoformat()}T23:59:59Z",
        "--format=%x1e%H%x1f%aN%x1f%aE%x1f%aI%x1f%s",
        "--name-only",
        "--no-renames",
        "HEAD",
    )
    records = []
    for ordinal, chunk in enumerate(output.split("\x1e"), 1):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        lines = chunk.splitlines()
        records.append(_commit_record(repository, lines[0], lines[1:], ordinal))
    records.sort(key=lambda item: item["mergedAt"], reverse=True)
    return records
