from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class DimensionScores(BaseModel):
    impact: float = Field(ge=0, le=10)
    complexity: float = Field(ge=0, le=10)
    output: float = Field(ge=0, le=10)
    ownership: float = Field(ge=0, le=10)


class WeightScores(BaseModel):
    impact: float
    complexity: float
    output: float
    ownership: float


class Evidence(BaseModel):
    title: str
    url: HttpUrl
    kind: Literal["pull_request", "review"]
    explanation: str
    impact_score: float = Field(ge=0, le=100)


class Engineer(BaseModel):
    rank: int = Field(ge=1, le=5)
    login: str
    name: str | None = None
    avatar_url: HttpUrl
    profile_url: HttpUrl
    score: float = Field(ge=0, le=100)
    strongest_dimension: Literal["impact", "complexity", "output", "ownership"]
    dimensions: DimensionScores
    confidence: float = Field(ge=0, le=1)
    summary: str
    authored_prs: int = Field(ge=0)
    substantive_reviews: int = Field(ge=0)
    primary_component: str | None = None
    active_weeks: int = Field(default=0, ge=0)
    component_share: float = Field(default=0, ge=0, le=100)
    meaningful_output: float = Field(default=0, ge=0)
    evidence: list[Evidence] = Field(min_length=1, max_length=3)


class Methodology(BaseModel):
    weights: WeightScores
    summary: str
    limitations: list[str]


class DashboardSnapshot(BaseModel):
    repository: str
    window_start: date
    window_end: date
    generated_at: datetime
    model: str
    methodology: Methodology
    engineers: list[Engineer] = Field(min_length=1, max_length=5)
