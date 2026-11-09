from tests.test_journal import create_entry


def test_tracking_summaries_and_private_timeline(client, user, other_user):
    create_entry(client, user)
    create_entry(client, user, "Quiero morir")
    summary = client.get("/api/tracking/summary", headers=user["headers"]).json()
    assert summary["counts"]["entries"] == 2
    assert summary["counts"]["alerts"] == 1
    assert client.get("/api/tracking/summary", headers=other_user["headers"]).json()["counts"]["entries"] == 0
    trends = client.get("/api/tracking/trends", headers=user["headers"]).json()
    assert sum(item["count"] for item in trends["daily_states"]) == 2
    timeline = client.get("/api/tracking/timeline", headers=user["headers"]).json()
    assert len(timeline) == 3
    assert client.get("/api/tracking/timeline", headers=other_user["headers"]).json() == []
    assert len(client.get("/api/tracking/timeline?limit=1&offset=1", headers=user["headers"]).json()) == 1
    assert client.get("/api/tracking/summary?days=0", headers=user["headers"]).status_code == 422
