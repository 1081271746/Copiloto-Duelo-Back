from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, literal, select, union_all

from app.models.entities import EmotionalAnalysis, ExerciseCompletion, JournalEntry, SafetyAlert


class TrackingService:
    def __init__(self, db):
        self.db = db

    def summary(self, user_id: str, days: int):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        counts = {}
        for name, model, date in [
            ("entries", JournalEntry, JournalEntry.recorded_at),
            ("analyses", EmotionalAnalysis, EmotionalAnalysis.created_at),
            ("completed_exercises", ExerciseCompletion, ExerciseCompletion.completed_at),
            ("alerts", SafetyAlert, SafetyAlert.created_at),
        ]:
            counts[name] = self.db.scalar(select(func.count()).select_from(model).where(
                model.user_id == user_id, date >= since,
            ))
        states = self.db.execute(select(JournalEntry.emotional_state, func.count()).where(
            JournalEntry.user_id == user_id, JournalEntry.recorded_at >= since,
        ).group_by(JournalEntry.emotional_state)).all()
        return {"period_days": days, "since": since, "counts": counts,
                "emotional_states": [{"state": state, "count": count} for state, count in states],
                "disclaimer": "Este resumen es descriptivo, no mide recuperación ni constituye un diagnóstico."}

    def trends(self, user_id: str, days: int):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        daily = self.db.execute(select(func.date(JournalEntry.recorded_at), JournalEntry.emotional_state, func.count()).where(
            JournalEntry.user_id == user_id, JournalEntry.recorded_at >= since,
        ).group_by(func.date(JournalEntry.recorded_at), JournalEntry.emotional_state)
            .order_by(func.date(JournalEntry.recorded_at))).all()
        analyses = self.db.scalars(select(EmotionalAnalysis).where(
            EmotionalAnalysis.user_id == user_id, EmotionalAnalysis.created_at >= since,
        ).order_by(EmotionalAnalysis.created_at.desc()).limit(5001)).all()
        emotions, categories = Counter(), Counter()
        for analysis in analyses[:5000]:
            emotions.update(set(analysis.result["emotions"]))
            categories.update({item["category"] for item in analysis.result["categories"]})
        return {"period_days": days, "daily_states": [
            {"date": str(day), "state": state, "count": count} for day, state, count in daily],
            "emotions": dict(emotions), "categories": dict(categories),
            "analyses_considered": min(len(analyses), 5000), "truncated": len(analyses) > 5000,
            "disclaimer": "Las categorías no son etapas universales, obligatorias ni lineales."}

    def timeline(self, user_id: str, limit: int, offset: int):
        queries = []
        for kind, model, date in [
            ("journal", JournalEntry, JournalEntry.created_at),
            ("analysis", EmotionalAnalysis, EmotionalAnalysis.created_at),
            ("exercise", ExerciseCompletion, ExerciseCompletion.completed_at),
            ("alert", SafetyAlert, SafetyAlert.created_at),
        ]:
            related = model.id if kind == "journal" else model.entry_id if kind in ("analysis", "alert") else model.analysis_id
            queries.append(select(literal(kind).label("type"), model.id.label("id"),
                                  date.label("occurred_at"), related.label("related_id")).where(model.user_id == user_id))
        combined = union_all(*queries).subquery()
        rows = self.db.execute(select(combined).order_by(
            combined.c.occurred_at.desc(), combined.c.id,
        ).limit(limit).offset(offset)).mappings()
        return [dict(row) for row in rows]
