import os

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}",
                    jwt_secret="test-only-secret-with-at-least-32-characters",
                    groq_key="",
                    redis_url=os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6379/15"))


@pytest.fixture
def app(settings):
    redis = Redis.from_url(settings.redis_url)
    connection = redis.connection_pool.connection_kwargs
    if connection.get("db") != 15 or connection.get("host") not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Tests require a local Redis database 15 dedicated exclusively to tests")
    redis.flushdb()
    application = create_app(settings)
    yield application
    redis.flushdb()
    redis.close()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user(client):
    payload = {"email": "first@example.com", "password": "ExamplePassword123!", "name": "Test User"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    token = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert token.status_code == 200
    return {"id": response.json()["id"], "headers": {"Authorization": f"Bearer {token.json()['access_token']}"},
            "password": payload["password"]}


@pytest.fixture
def other_user(client):
    payload = {"email": "second@example.com", "password": "ExamplePassword123!", "name": "Other User"}
    response = client.post("/api/auth/register", json=payload)
    token = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    return {"id": response.json()["id"], "headers": {"Authorization": f"Bearer {token.json()['access_token']}"}}
