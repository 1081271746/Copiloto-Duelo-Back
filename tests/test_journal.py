def create_entry(client, user, content="Hoy extraño mucho a mi familiar."):
    return client.post("/api/journal", headers=user["headers"],
                       json={"content": content, "emotional_state": "sadness"})


def test_journal_crud_and_isolation(client, user, other_user):
    response = create_entry(client, user)
    assert response.status_code == 201
    entry_id = response.json()["entry"]["id"]
    assert response.json()["safety_alert"] is None
    assert client.get("/api/journal", headers=user["headers"]).json()[0]["id"] == entry_id
    assert client.get("/api/journal", headers=other_user["headers"]).json() == []
    for method in ["get", "patch", "delete"]:
        kwargs = {"json": {"content": "Changed"}} if method == "patch" else {}
        assert getattr(client, method)(f"/api/journal/{entry_id}", headers=other_user["headers"], **kwargs).status_code == 404
    changed = client.patch(f"/api/journal/{entry_id}", headers=user["headers"], json={"content": "Recuerdo con cariño."})
    assert changed.json()["entry"]["version"] == 2
    assert client.delete(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 204
    assert client.get(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 404


def test_validation_and_pagination(client, user):
    for content in ["", "   ", "a" * 10001]:
        assert create_entry(client, user, content).status_code == 422
    entry_id = create_entry(client, user).json()["entry"]["id"]
    assert client.patch(f"/api/journal/{entry_id}", headers=user["headers"], json={"content": None}).status_code == 422
    assert client.get("/api/journal?limit=101", headers=user["headers"]).status_code == 422
    assert client.get("/api/journal?offset=-1", headers=user["headers"]).status_code == 422
    assert client.post("/api/journal", headers=user["headers"], json={
        "content": "Test", "emotional_state": "sad", "recorded_at": "2026-01-01T12:00:00",
    }).status_code == 422


def test_alerts_created_before_ai_and_private(client, user, other_user):
    response = create_entry(client, user, "Quiero quitarme la vida.")
    alert = response.json()["safety_alert"]
    assert alert["risk_level"] == "high"
    assert alert["guidance"]["emergency_contacted"] is False
    assert alert["guidance"]["resources"]["emergency_number"] == "123"
    assert client.get("/api/alerts", headers=other_user["headers"]).json() == []
    assert client.post(f"/api/alerts/{alert['id']}/acknowledge", headers=other_user["headers"]).status_code == 404
    acknowledged = client.post(f"/api/alerts/{alert['id']}/acknowledge", headers=user["headers"])
    assert acknowledged.json()["acknowledged_at"] is not None
    assert client.delete(f"/api/journal/{response.json()['entry']['id']}", headers=user["headers"]).status_code == 204
    assert client.get(f"/api/alerts/{alert['id']}", headers=user["headers"]).json()["entry_id"] is None


def test_empty_update_does_not_create_a_version_or_event(client, app, user):
    from unittest.mock import AsyncMock
    entry = create_entry(client, user).json()["entry"]
    app.state.events.publish = AsyncMock(return_value=True)
    response = client.patch(f"/api/journal/{entry['id']}", headers=user["headers"], json={})
    assert response.status_code == 200
    assert response.json()["entry"] == entry
    app.state.events.publish.assert_not_awaited()
    assert client.get(f"/api/journal/{entry['id']}", headers=user["headers"]).json() == entry


def test_recorded_offsets_survive_create_and_edit(client, user):
    from datetime import datetime
    response = client.post("/api/journal", headers=user["headers"], json={
        "content": "A timestamped reflection", "emotional_state": "sadness",
        "recorded_at": "2026-01-01T12:00:00-05:00",
    })
    assert response.status_code == 201
    entry_id = response.json()["entry"]["id"]
    loaded = client.get(f"/api/journal/{entry_id}", headers=user["headers"]).json()
    assert datetime.fromisoformat(loaded["recorded_at"]) == datetime.fromisoformat("2026-01-01T17:00:00+00:00")
    client.patch(f"/api/journal/{entry_id}", headers=user["headers"],
                 json={"recorded_at": "2026-01-02T12:00:00+03:00"})
    loaded = client.get(f"/api/journal/{entry_id}", headers=user["headers"]).json()
    assert datetime.fromisoformat(loaded["recorded_at"]) == datetime.fromisoformat("2026-01-02T09:00:00+00:00")


def test_deleting_entry_preserves_activity_and_minimal_alert(client, app, settings, user):
    from tests.test_analysis import configure_analyzer
    configure_analyzer(app, settings)
    entry_id = create_entry(client, user).json()["entry"]["id"]
    result = client.post(f"/api/journal/{entry_id}/analyze", headers=user["headers"]).json()
    analysis_id = result["analysis"]["id"]
    exercise_id = result["recommendations"][0]["id"]
    assert client.post(f"/api/exercises/{exercise_id}/complete", headers=user["headers"],
                       json={"analysis_id": analysis_id, "notes": "A fictional completion"}).status_code == 201
    changed = client.patch(f"/api/journal/{entry_id}", headers=user["headers"],
                           json={"content": "Quiero morir"}).json()
    alert_id = changed["safety_alert"]["id"]
    assert client.delete(f"/api/journal/{entry_id}", headers=user["headers"]).status_code == 204
    history = client.get("/api/exercise-history", headers=user["headers"]).json()
    assert len(history) == 1 and history[0]["analysis_id"] is None
    assert client.get(f"/api/alerts/{alert_id}", headers=user["headers"]).json()["entry_id"] is None
    assert client.get(f"/api/analyses/{analysis_id}", headers=user["headers"]).status_code == 404
    assert client.get("/api/users/me", headers=user["headers"]).status_code == 200
