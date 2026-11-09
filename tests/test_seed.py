from sqlalchemy import func, select

from app.models.entities import EmotionalAnalysis, Exercise, ExerciseCompletion, JournalEntry, SafetyAlert, User
from seed.demo import seed_demo
from seed.library import seed_library


def test_demo_seed_is_explicit_fictional_and_idempotent(client, app, settings):
    with app.state.session_factory() as db:
        seed_demo(db, settings, "TestOnlyPassword123!")
        seed_demo(db, settings, "TestOnlyPassword123!")
        seed_library(db)
        assert db.scalar(select(func.count()).select_from(User)) == 2
        assert db.scalar(select(func.count()).select_from(JournalEntry)) == 2
        assert db.scalar(select(func.count()).select_from(EmotionalAnalysis)) == 2
        assert db.scalar(select(func.count()).select_from(ExerciseCompletion)) == 1
        assert db.scalar(select(func.count()).select_from(SafetyAlert)) == 1
        assert db.scalar(select(func.count()).select_from(Exercise)) == 6
        assert db.scalar(select(EmotionalAnalysis)).model == "seed-fixture-not-gemini"
