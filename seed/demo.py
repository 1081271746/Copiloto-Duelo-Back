from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from app.models.entities import EmotionalAnalysis, Exercise, ExerciseCompletion, JournalEntry, User, utc_now
from app.security.tokens import hash_password
from app.services.safety import SafetyService


def seed_demo(db, settings, password: str):
    if len(password) < 12 or len(password) > 128:
        raise ValueError("DEMO_PASSWORD must contain between 12 and 128 characters")
    for number, content, state in [
        (1, "Hoy recordé un paseo con mi familiar. Me duele su ausencia, pero pude compartir ese recuerdo con una amistad.", "sadness"),
        (2, "A veces siento que no puedo más. Hoy necesito compañía y apoyo.", "overwhelmed"),
    ]:
        user_id = str(uuid5(NAMESPACE_URL, f"grief-copilot/demo/user/{number}"))
        if db.get(User, user_id):
            continue
        user = User(id=user_id, email=f"demo{number}@example.com", name=f"Demo {number}",
                    password_hash=hash_password(password), country=settings.default_country)
        db.add(user)
        db.flush()
        created = utc_now() - timedelta(days=1)
        entry = JournalEntry(user_id=user.id, content=content, emotional_state=state,
                             created_at=created, recorded_at=created)
        db.add(entry)
        db.flush()
        assessment = SafetyService(settings).detect(content)
        SafetyService(settings).record(db, user, entry, assessment)
        analysis = EmotionalAnalysis(user_id=user.id, entry_id=entry.id, entry_version=1,
            model="seed-fixture-not-gemini",
            result={"emotions": [state], "categories": [],
                    "summary": "Dato ficticio de demostración; no fue generado por Gemini.",
                    "patterns": [], "recommended_categories": ["acceptance"] if number == 1 else [],
                    "risk_level": assessment.level})
        db.add(analysis)
        db.flush()
        if number == 1:
            exercise_id = str(uuid5(NAMESPACE_URL, "grief-copilot/exercises/acceptance"))
            db.add(ExerciseCompletion(user_id=user.id, exercise_id=exercise_id,
                                      analysis_id=analysis.id, notes="Registro ficticio de prueba."))
    db.commit()
