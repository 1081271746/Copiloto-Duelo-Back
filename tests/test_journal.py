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
