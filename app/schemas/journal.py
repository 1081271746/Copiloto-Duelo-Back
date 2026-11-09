from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from app.schemas.auth import StrictModel


Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
EmotionalState = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class JournalCreate(StrictModel):
    content: Content
    emotional_state: EmotionalState
    recorded_at: datetime | None = None

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("timezone_required")
        return value


class JournalUpdate(StrictModel):
    content: Content | None = None
    emotional_state: EmotionalState | None = None
    recorded_at: datetime | None = None

    @field_validator("content", "emotional_state", "recorded_at")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("null_not_allowed")
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("timezone_required")
        return value


class JournalOutput(StrictModel):
    id: str
    content: str
    emotional_state: str
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime
    version: int


class AlertOutput(StrictModel):
    id: str
    entry_id: str | None
    risk_level: str
    source: str
    rule_codes: list[str]
    guidance: dict
    acknowledged_at: datetime | None
    created_at: datetime


class JournalMutation(StrictModel):
    entry: JournalOutput
    safety_alert: AlertOutput | None
    realtime_delivered: bool
