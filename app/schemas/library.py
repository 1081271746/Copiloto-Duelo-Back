from datetime import datetime
from typing import Annotated

from pydantic import StringConstraints

from app.schemas.auth import StrictModel


class ExerciseOutput(StrictModel):
    id: str
    title: str
    category: str
    description: str
    instructions: list[str]
    duration_minutes: int


class ResourceOutput(StrictModel):
    id: str
    title: str
    description: str
    url: str
    country: str | None
    category: str


class CompletionInput(StrictModel):
    analysis_id: str | None = None
    notes: Annotated[str, StringConstraints(max_length=2000)] | None = None


class CompletionOutput(StrictModel):
    id: str
    exercise_id: str
    analysis_id: str | None
    notes: str | None
    completed_at: datetime
