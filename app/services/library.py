from fastapi import HTTPException
from sqlalchemy import select

from app.models.entities import EmotionalAnalysis, Exercise, ExerciseCompletion, JournalEntry, SafetyAlert
from app.repositories.base import UserRepository
from app.schemas.library import ExerciseOutput
from app.services.safety import SafetyService


class LibraryService:
    def __init__(self, db, settings):
        self.db = db
        self.safety = SafetyService(settings)

    def has_pending_risk(self, user_id: str) -> bool:
        return self.db.scalar(select(SafetyAlert.id).where(
            SafetyAlert.user_id == user_id, SafetyAlert.acknowledged_at.is_(None),
        ).limit(1)) is not None

    def recommendations(self, user, analysis=None) -> dict:
        analysis = analysis or self.db.scalar(select(EmotionalAnalysis).where(
            EmotionalAnalysis.user_id == user.id,
        ).order_by(EmotionalAnalysis.created_at.desc()).limit(1))
        risk = self.has_pending_risk(user.id)
        if analysis:
            entry = self.db.get(JournalEntry, analysis.entry_id)
            risk = risk or analysis.result["risk_level"] not in ("none", "low")
            risk = risk or self.safety.detect(entry.content).level != "none"
            if entry.version != analysis.entry_version:
                return {"items": [], "reason": "analysis_outdated", "safety_guidance": self.safety.guidance(user.country, "moderate") if risk else None}
        if risk:
            return {"items": [], "reason": "safety_priority", "safety_guidance": self.safety.guidance(user.country, "high")}
        if analysis is None:
            return {"items": [], "reason": "analysis_required", "safety_guidance": None}
        categories = analysis.result["recommended_categories"]
        exercises = self.db.scalars(select(Exercise).where(Exercise.category.in_(categories)).order_by(Exercise.title).limit(10)).all()
        return {"items": [ExerciseOutput.model_validate(item).model_dump() for item in exercises],
                "reason": "analysis_based", "safety_guidance": None}

    def complete(self, exercise_id: str, data, user):
        exercise = self.db.get(Exercise, exercise_id)
        if exercise is None:
            raise HTTPException(404, "not_found")
        if data.analysis_id:
            UserRepository(self.db, EmotionalAnalysis).get(data.analysis_id, user.id)
        if self.has_pending_risk(user.id):
            raise HTTPException(409, {"code": "safety_priority", "guidance": self.safety.guidance(user.country, "high")})
        completion = ExerciseCompletion(user_id=user.id, exercise_id=exercise_id,
                                        analysis_id=data.analysis_id, notes=data.notes)
        self.db.add(completion)
        self.db.commit()
        return completion
