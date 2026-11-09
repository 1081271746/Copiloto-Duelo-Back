from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.models.entities import User
from app.security.tokens import verify_password


def test_registration_login_and_profile(client, app, user):
    response = client.get("/api/users/me", headers=user["headers"])
    assert response.status_code == 200
    assert "password_hash" not in response.json()
    with app.state.session_factory() as db:
        stored = db.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2id$")
        assert verify_password(user["password"], stored.password_hash)
    assert client.post("/api/auth/register", json={
        "email": "FIRST@example.com", "name": "Duplicate", "password": user["password"],
    }).status_code == 409


def test_profile_update_and_password_revocation(client, user):
    assert client.patch("/api/users/me", headers=user["headers"], json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/users/me", headers=user["headers"], json={"name": None}).status_code == 422
    assert client.post("/api/users/me/password", headers=user["headers"],
                       json={"current_password": "wrong", "new_password": "NewPassword123!"}).status_code == 400
    assert client.post("/api/users/me/password", headers=user["headers"],
                       json={"current_password": user["password"], "new_password": "NewPassword123!"}).status_code == 204
    assert client.get("/api/users/me", headers=user["headers"]).status_code == 401
    assert client.post("/api/auth/login", json={"email": "first@example.com", "password": "NewPassword123!"}).status_code == 200


def test_logout(client, user):
    assert client.post("/api/auth/logout", headers=user["headers"]).status_code == 204
    assert client.get("/api/users/me", headers=user["headers"]).status_code == 401


def test_invalid_authentication(client, user, settings):
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    token = user["headers"]["Authorization"].split()[1]
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=settings.jwt_audience)
    claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "first@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "unknown@example.com", "password": "wrong"}).status_code == 401


def test_validation_never_echoes_password(client):
    response = client.post("/api/auth/register", json={"email": "invalid", "password": "private", "name": ""})
    assert response.status_code == 422
    assert "private" not in response.text


def test_health(client):
    assert client.get("/api/healthz").json()["redis"] is True
