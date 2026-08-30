import json
import os
import re
from collections import defaultdict
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field


class Classification(BaseModel):
    number: int
    change_significance: float = Field(ge=0, le=10)
    blast_radius: float = Field(ge=0, le=10)
    logic: float = Field(ge=0, le=10)
    architecture: float = Field(ge=0, le=10)
    cross_component: float = Field(ge=0, le=10)
    change_scope: float = Field(ge=0, le=10)
    pr_value: float = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    tags: list[str] = Field(max_length=3)
    explanation: str = Field(max_length=240)


class ClassificationBatch(BaseModel):
    items: list[Classification]


def deterministic_classification(pr: dict[str, Any]) -> Classification:
    title = pr.get("title", "").lower()
    paths = [node.get("path", "").lower() for node in pr.get("files", {}).get("nodes", [])]
    changed_files = pr.get("changedFiles") or len(paths)
    generated = any(token in title for token in ("generated", "chore(deps)", "bump ", "update snapshots")) or bool(paths) and all("generated" in path or path.endswith((".lock", ".snap")) for path in paths)
    docs = bool(paths) and all(path.endswith((".md", ".mdx")) or path.startswith("docs/") for path in paths)
    tests = bool(paths) and all("test" in path or "spec" in path or "fixture" in path for path in paths)
    cross_component = min(10, max(1, len({path.split("/", 1)[0] for path in paths}) * 2))
    scope = min(10, 1 + changed_files ** .5)
    if generated:
        value, significance, confidence, tag = 0.0, 1.0, .9, "generated"
    elif docs:
        value, significance, confidence, tag = .5, 1.5, .85, "docs"
    elif tests:
        value, significance, confidence, tag = 1.5, 2.5, .7, "tests"
    elif title.startswith("feat"):
        value, significance, confidence, tag = 3.0, 5.5, .45, "feature"
    elif title.startswith(("fix", "perf", "revert")):
        value, significance, confidence, tag = 3.0, 5.0, .45, "fix"
    elif title.startswith(("refactor", "cleanup")):
        value, significance, confidence, tag = 2.0, 3.5, .55, "refactor"
    else:
        value, significance, confidence, tag = 1.0, 2.5, .4, "uncertain"
    return Classification(number=pr["number"], change_significance=significance, blast_radius=min(10, 2 + cross_component * .45), logic=min(10, 2 + scope * .35), architecture=min(10, 1.5 + cross_component * .35), cross_component=cross_component, change_scope=scope, pr_value=value, confidence=confidence, tags=[f"heuristic:{tag}"], explanation=f"Deterministic {tag} baseline from commit convention and changed paths.")


def _candidate_priority(pr: dict[str, Any], baseline: Classification) -> float:
    title = pr.get("title", "").lower()
    paths = [node.get("path", "").lower() for node in pr.get("files", {}).get("nodes", [])]
    important = max((10 if any(x in path for x in ("capture/", "ingestion", "kafka", "auth")) else 9 if "feature_flag" in path else 8 if any(x in path for x in ("session_replay", "recordings", "api/")) else 6 if any(x in path for x in ("products/", "posthog/")) else 4 for path in paths), default=4)
    semantic_hint = 3 if re.search(r"security|critical|incident|performance|migration|reliability|race|data loss", title) else 0
    return important + min(pr.get("changedFiles", 0), 25) / 5 + baseline.pr_value + semantic_hint


def select_gpt_candidates(prs: list[dict[str, Any]], baselines: dict[int, Classification], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    eligible = [pr for pr in prs if not any(tag in ("heuristic:generated", "heuristic:docs") for tag in baselines[pr["number"]].tags)]
    by_author: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pr in eligible:
        by_author[pr["author"]["login"]].append(pr)
    for contributions in by_author.values():
        contributions.sort(key=lambda pr: _candidate_priority(pr, baselines[pr["number"]]), reverse=True)
    selected: list[dict[str, Any]] = []
    selected_numbers: set[int] = set()
    per_author = max(1, limit // len(by_author)) if by_author else 0
    for author in sorted(by_author):
        for pr in by_author[author][:per_author]:
            if len(selected) >= limit:
                break
            selected.append(pr)
            selected_numbers.add(pr["number"])
    remainder = sorted((pr for pr in eligible if pr["number"] not in selected_numbers), key=lambda pr: _candidate_priority(pr, baselines[pr["number"]]), reverse=True)
    selected.extend(remainder[:max(0, limit - len(selected))])
    return selected


def classify_bounded(prs: list[dict[str, Any]], limit: int) -> tuple[dict[int, Classification], int]:
    classifications = {pr["number"]: deterministic_classification(pr) for pr in prs}
    candidates = select_gpt_candidates(prs, classifications, min(limit, len(prs)))
    if candidates:
        classifications.update(classify_pull_requests(candidates))
    return classifications, len(candidates)


def fallback(pr: dict, reason: str) -> Classification:
    return Classification(number=pr["number"], change_significance=2, blast_radius=2, logic=2, architecture=2, cross_component=2, change_scope=2, pr_value=.5, confidence=.2, tags=["unclassified"], explanation=f"Classification unavailable: {reason[:180]}")


def classify_pull_requests(prs: list[dict[str, Any]]) -> dict[int, Classification]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    output: dict[int, Classification] = {}
    for offset in range(0, len(prs), 20):
        batch = prs[offset:offset + 20]
        compact = [{"number":p["number"],"title":p["title"],"body":(p.get("body") or "")[:1600],"labels":[x["name"] for x in p.get("labels",{}).get("nodes",[])],"files":[x["path"] for x in p.get("files",{}).get("nodes",[])],"changed_files":p.get("changedFiles"),"additions":p.get("additions"),"deletions":p.get("deletions"),"issues":p.get("closingIssuesReferences",{}).get("nodes",[]),"diff_excerpt":(p.get("diffExcerpt") or "")[:4000]} for p in batch]
        error = "unknown error"
        for _ in range(2):
            try:
                response = client.responses.parse(
                    model=model,
                    input=[
                        {"role":"system","content":"Assess each PostHog PR from visible evidence. Score change_significance and blast_radius 0-10. Score complexity signals logic, architecture, cross_component, and change_scope 0-10; file count is supporting evidence only. Assign pr_value: 5 major feature, 4 major bug/performance fix, 3 normal feature/fix, 2 useful refactor, 1-2 tests/infrastructure, 0.5 docs/minor cleanup, 0 generated/trivial. Do not score ownership. Be conservative, concise, and evidence-bound."},
                        {"role":"user","content":json.dumps(compact)},
                    ],
                    text_format=ClassificationBatch,
                )
                parsed = response.output_parsed
                if not parsed:
                    raise ValueError("empty structured response")
                output.update({item.number:item for item in parsed.items})
                break
            except Exception as exc:
                error = str(exc)
        for pr in batch:
            output.setdefault(pr["number"], fallback(pr, error))
    return output
