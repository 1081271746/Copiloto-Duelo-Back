from sqlalchemy import delete

from app.models.entities import EmotionalAnalysis, JournalEntry, utc_now
from app.repositories.base import UserRepository
from app.services.safety import SafetyService


class JournalService:
    def __init__(self, db, settings, events):
        self.db = db
        self.safety = SafetyService(settings)
        self.events = events
        self.repository = UserRepository(db, JournalEntry)

    async def create(self, data, user):
        entry = JournalEntry(user_id=user.id, content=data.content, emotional_state=data.emotional_state,
                             recorded_at=data.recorded_at or utc_now())
        self.db.add(entry)
        self.db.flush()
        alert = self.safety.record(self.db, user, entry, self.safety.detect(entry.content))
        self.db.commit()
        delivered = await self.events.publish(user.id, "journal.created", {"entry_id": entry.id})
        if alert:
            delivered = await self.events.publish(user.id, "safety.alert", {"alert_id": alert.id}) and delivered
        return {"entry": entry, "safety_alert": alert, "realtime_delivered": delivered}

    async def update(self, entry_id, data, user):
        entry = self.repository.get(entry_id, user.id)
        values = data.model_dump(exclude_unset=True)
        if not values:
            return {"entry": entry, "safety_alert": None, "realtime_delivered": True}
        for key, value in values.items():
            setattr(entry, key, value)
        entry.version += 1
        entry.updated_at = utc_now()
        alert = self.safety.record(self.db, user, entry, self.safety.detect(entry.content))
        self.db.commit()
        delivered = await self.events.publish(user.id, "journal.updated", {"entry_id": entry.id})
        if alert:
            delivered = await self.events.publish(user.id, "safety.alert", {"alert_id": alert.id}) and delivered
        return {"entry": entry, "safety_alert": alert, "realtime_delivered": delivered}

    async def delete(self, entry_id, user):
        entry = self.repository.get(entry_id, user.id)
        self.db.delete(entry)
        self.db.commit()
        return await self.events.publish(user.id, "journal.deleted", {"entry_id": entry_id})
