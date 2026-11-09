from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.auth import StrictModel


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class GriefCategory(str, Enum):
    denial = "denial"
    anger = "anger"
    bargaining = "bargaining"
    depression = "depression"
    acceptance = "acceptance"


class CategoryEstimate(StrictModel):
    category: GriefCategory
    confidence: float = Field(ge=0, le=1)
    rationale: ShortText


class AnalysisResult(StrictModel):
    emotions: list[ShortText] = Field(min_length=1, max_length=10)
    categories: list[CategoryEstimate] = Field(max_length=5)
    summary: ShortText
    patterns: list[ShortText] = Field(max_length=5)
    recommended_categories: list[GriefCategory] = Field(max_length=5)
    risk_level: Literal["none", "low", "moderate", "high", "critical"]


class AnalysisOutput(StrictModel):
    id: str
    entry_id: str
    entry_version: int
    result: AnalysisResult
    model: str
    created_at: datetime


class AnalysisResponse(StrictModel):
    analysis: AnalysisOutput
    recommendations: list[dict]
    safety_alert: dict | None
    realtime_delivered: bool
    disclaimer: str = "Las categorías son orientativas, no diagnósticas, universales ni lineales. El sistema no sustituye atención profesional."
