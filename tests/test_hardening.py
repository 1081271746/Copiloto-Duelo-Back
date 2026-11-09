from dataclasses import replace

from redis import Redis
from sqlalchemy import select

from app.models.entities import JournalEntry, User
from tests.test_analysis import configure_analyzer
from tests.test_journal import create_entry


def test_request_size_limit(client):
    response = client.post("/api/auth/login", content=b"x" * 65537, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_analysis_errors_preserve_data_and_release_lock(client, app, settings, user):
    from app.core.errors import ServiceError
    configure_analyzer(app, settings)
    app.state.analyzer.analyze.side_effect = ServiceError("gemini_timeout", 504)
    entry_id = create_entry(client, user).json()["entry"]["id"]
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).status_code == 504
    with Redis.from_url(settings.redis_url) as redis:
        assert redis.get(f"copilot:analysis:{entry_id}") is None
    assert client.get(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 200
    assert client.get("/api/analyses", headers=user["headers"]).json() == []


def test_entry_edited_during_analysis_is_rejected(client, app, settings, user):
    from app.schemas.analysis import AnalysisResult
    from tests.test_analysis import RESULT
    configure_analyzer(app, settings)
    entry_id = create_entry(client, user).json()["entry"]["id"]

    async def concurrent_edit(content, previous):
        with app.state.session_factory() as db:
            entry = db.get(JournalEntry, entry_id)
            entry.content = "Changed during analysis"
            entry.version += 1
            db.commit()
        return AnalysisResult.model_validate(RESULT)

    app.state.analyzer.analyze.side_effect = concurrent_edit
    response = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"])
    assert response.status_code == 409
    assert client.get("/api/analyses", headers=user["headers"]).json() == []


def test_analysis_lock_prevents_duplicate_calls(client, app, settings, user):
    configure_analyzer(app, settings)
    entry_id = create_entry(client, user).json()["entry"]["id"]
    with Redis.from_url(settings.redis_url) as redis:
        redis.set(f"copilot:analysis:{entry_id}", "another-request", ex=60)
    assert client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).status_code == 409
    app.state.analyzer.analyze.assert_not_awaited()


def test_acknowledgement_does_not_clear_current_risk(client, user):
    output = create_entry(client, user, "Quiero morir").json()
    alert_id = output["safety_alert"]["id"]
    client.post(f"/api/alerts/{alert_id}/acknowledge", headers=user["headers"])
    exercise = client.get("/api/exercises", headers=user["headers"]).json()[0]
    assert client.post(f"/api/exercises/{exercise['id']}/complete", headers=user["headers"], json={}).status_code == 409
    assert client.get("/api/recommendations", headers=user["headers"]).json()["reason"] == "safety_priority"


def test_login_rate_limit(client, settings):
    with Redis.from_url(settings.redis_url) as redis:
        redis.set("copilot:limits:login:testclient", 20, ex=60)
    response = client.post("/api/auth/login", json={"email": "unknown@example.com", "password": "invalid"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers
