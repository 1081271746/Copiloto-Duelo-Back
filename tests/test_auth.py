from datetime import datetime, timedelta, timezone

import jwt
import pytest
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


@pytest.mark.parametrize(("field", "value"), [
    ("ver", False), ("ver", -1), ("ver", "0"), ("jti", ""), ("sub", ""),
])
def test_invalid_claim_shapes_are_rejected(client, user, settings, field, value):
    original = user["headers"]["Authorization"].split()[1]
    claims = jwt.decode(original, settings.jwt_secret, algorithms=["HS256"], audience=settings.jwt_audience)
    claims[field] = value
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_expired_database_session_overrides_valid_jwt(client, app, user, settings):
    from app.models.entities import TokenSession
    token = user["headers"]["Authorization"].split()[1]
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=settings.jwt_audience)
    with app.state.session_factory() as db:
        session = db.get(TokenSession, claims["jti"])
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/users/me", headers=user["headers"]).status_code == 401


@pytest.mark.parametrize("mutation", ["issuer", "audience", "signature", "algorithm", "missing_exp"])
def test_jwt_trust_boundaries(client, user, settings, mutation):
    original = user["headers"]["Authorization"].split()[1]
    claims = jwt.decode(original, settings.jwt_secret, algorithms=["HS256"], audience=settings.jwt_audience)
    key, algorithm = settings.jwt_secret, "HS256"
    if mutation == "issuer":
        claims["iss"] = "untrusted-issuer"
    elif mutation == "audience":
        claims["aud"] = "different-api"
    elif mutation == "signature":
        key = "untrusted-key-with-more-than-32-characters"
    elif mutation == "algorithm":
        key, algorithm = "", "none"
    else:
        claims.pop("exp")
    forged = jwt.encode(claims, key, algorithm=algorithm)
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_corrupted_password_hash_fails_closed(client, app, user):
    with app.state.session_factory() as db:
        account = db.get(User, user["id"])
        account.password_hash = "not-an-argon2-hash"
        db.commit()
    response = client.post("/api/auth/login", json={"email": "first@example.com", "password": user["password"]})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"
