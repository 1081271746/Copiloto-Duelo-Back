from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy import select, update

from app.core.errors import ServiceError
from app.models.entities import EmotionalAnalysis, JournalEntry
from app.repositories.base import UserRepository
from app.schemas.journal import AlertOutput
from app.services.library import LibraryService
from app.services.safety import RISK_LEVELS, RiskAssessment, SafetyService


UNLOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class AnalysisService:
    def __init__(self, db, settings, events, analyzer):
        self.db = db
        self.settings = settings
        self.events = events
        self.analyzer = analyzer
        self.safety = SafetyService(settings)

    async def analyze(self, entry_id, user):
        entry = UserRepository(self.db, JournalEntry).get(entry_id, user.id)
        if not self.settings.gemini_key:
            raise ServiceError("gemini_not_configured")
        version, content = entry.version, entry.content
        lock_key = f"copilot:analysis:{entry_id}"
        lock_token = str(uuid4())
        try:
            acquired = await self.events.redis.set(lock_key, lock_token, nx=True,
                                                   ex=int(self.settings.gemini_timeout) + 30)
        except RedisError:
            raise ServiceError("analysis_coordinator_unavailable") from None
        if not acquired:
            raise HTTPException(409, "analysis_in_progress")
        try:
            await self.events.rate_limit(f"gemini:global:{self.settings.gemini_model}", self.settings.gemini_rpm, 60)
            day = datetime.now(timezone.utc).date().isoformat()
            await self.events.rate_limit(f"gemini:{user.id}:{day}", self.settings.daily_limit, 86400)
            previous = self.db.scalars(select(JournalEntry).where(
                JournalEntry.user_id == user.id, JournalEntry.id != entry_id,
                JournalEntry.recorded_at <= entry.recorded_at,
            ).order_by(JournalEntry.recorded_at.desc()).limit(5)).all()
            history = [{"content": item.content[:2000], "recorded_at": item.recorded_at.isoformat()} for item in previous]
            self.db.rollback()
            result = await self.analyzer.analyze(content, history)
            entry = UserRepository(self.db, JournalEntry).get(entry_id, user.id)
            if entry.version != version:
                raise HTTPException(409, "entry_changed_during_analysis")
            locked = self.db.execute(update(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.user_id == user.id,
                JournalEntry.version == version,
            ).values(updated_at=entry.updated_at))
            if locked.rowcount != 1:
                self.db.rollback()
                raise HTTPException(409, "entry_changed_during_analysis")
            deterministic = self.safety.detect(content)
            ai_risk = result.risk_level
            risk = max((deterministic.level, ai_risk), key=lambda level: RISK_LEVELS[level])
            result.risk_level = risk
            pending = LibraryService(self.db, self.settings).has_pending_risk(user.id)
            if risk != "none" or pending:
                result.recommended_categories = []
            analysis = EmotionalAnalysis(user_id=user.id, entry_id=entry.id, entry_version=version,
                                          result=result.model_dump(mode="json"), model=self.settings.gemini_model)
            self.db.add(analysis)
            alert = None
            if RISK_LEVELS[risk] > RISK_LEVELS[deterministic.level]:
                alert = self.safety.record(self.db, user, entry, RiskAssessment(risk, ["ai_complement"]),
                                            source="ai")
            self.db.commit()
            recommendations = LibraryService(self.db, self.settings).recommendations(user, analysis)
            delivered = await self.events.publish(user.id, "analysis.completed", {"analysis_id": analysis.id, "entry_id": entry.id})
            delivered = await self.events.publish(user.id, "tracking.updated", {"analysis_id": analysis.id}) and delivered
            if recommendations["items"]:
                delivered = await self.events.publish(user.id, "recommendation.created", {"analysis_id": analysis.id}) and delivered
            if alert:
                delivered = await self.events.publish(user.id, "safety.alert", {"alert_id": alert.id}) and delivered
            return {"analysis": analysis, "recommendations": recommendations["items"],
                    "safety_alert": AlertOutput.model_validate(alert).model_dump(mode="json") if alert else None,
                    "realtime_delivered": delivered}
        finally:
            try:
                await self.events.redis.eval(UNLOCK_SCRIPT, 1, lock_key, lock_token)
            except RedisError:
                pass
