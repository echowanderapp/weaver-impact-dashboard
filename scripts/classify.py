import json
import os
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
        compact = [{"number":p["number"],"title":p["title"],"body":(p.get("body") or "")[:1600],"labels":[x["name"] for x in p.get("labels",{}).get("nodes",[])],"files":[x["path"] for x in p.get("files",{}).get("nodes",[])],"changed_files":p.get("changedFiles"),"issues":p.get("closingIssuesReferences",{}).get("nodes",[])} for p in batch]
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
