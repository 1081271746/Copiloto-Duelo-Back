from tests.test_journal import create_entry


def test_seed_filter_details_completions_and_isolation(client, user, other_user):
    exercises = client.get("/api/exercises", headers=user["headers"]).json()
    assert len(exercises) == 6
    filtered = client.get("/api/exercises?category=acceptance", headers=user["headers"]).json()
    assert len(filtered) == 1
    exercise_id = exercises[0]["id"]
    assert client.get(f"/api/exercises/{exercise_id}", headers=user["headers"]).status_code == 200
    assert client.get("/api/exercises/missing", headers=user["headers"]).status_code == 404
    assert client.get("/api/resources", headers=user["headers"]).json()
    assert client.post(f"/api/exercises/{exercise_id}/complete", headers=user["headers"], json={"notes": "Me resultó útil."}).status_code == 201
    assert len(client.get("/api/exercise-history", headers=user["headers"]).json()) == 1
    assert client.get("/api/exercise-history", headers=other_user["headers"]).json() == []
    assert client.get("/api/recommendations", headers=user["headers"]).json()["reason"] == "analysis_required"


def test_crisis_blocks_generic_exercise_completion(client, user):
    create_entry(client, user, "No quiero seguir viviendo")
    exercise_id = client.get("/api/exercises", headers=user["headers"]).json()[0]["id"]
    assert client.post(f"/api/exercises/{exercise_id}/complete", headers=user["headers"], json={}).status_code == 409
    output = client.get("/api/recommendations", headers=user["headers"]).json()
    assert output["items"] == []
    assert output["safety_guidance"]
