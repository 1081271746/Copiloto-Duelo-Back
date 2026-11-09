import pytest

from app.core.config import Settings


def test_database_configuration_isolated_from_platform(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused")
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    assert Settings().database_url == "sqlite:///./copilot.db"
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite:///configured.db")
    assert Settings().database_url == "sqlite:///configured.db"


def test_invalid_secret_rejected():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings(jwt_secret="").validate()


def test_secret_values_excluded_from_configuration_repr():
    settings = Settings(jwt_secret="private-jwt-value", gemini_key="private-gemini-value")
    assert "private-jwt-value" not in repr(settings)
    assert "private-gemini-value" not in repr(settings)


@pytest.mark.parametrize("overrides", [
    {"jwt_secret": " " * 64}, {"token_minutes": 0}, {"daily_limit": 0},
    {"gemini_rpm": -1}, {"gemini_timeout": 0}, {"gemini_timeout": float("nan")},
    {"gemini_timeout": float("inf")}, {"gemini_timeout": 301},
    {"jwt_issuer": " "}, {"jwt_audience": ""}, {"gemini_model": "../models/test"},
    {"default_country": "colombia"}, {"cors_origins": []}, {"cors_origins": ["*"]},
    {"cors_origins": ["https://example.com/path"]},
    {"cors_origins": ["https://user:password@example.com"]},
    {"cors_origins": ["https://example.com:invalid"]},
    {"emergency_resources": []}, {"emergency_resources": {"CO": []}},
    {"emergency_resources": {"co": {}}},
    {"emergency_resources": {"CO": {"support_url": "javascript:alert(1)"}}},
])
def test_invalid_configuration_fails_before_serving(overrides):
    with pytest.raises(RuntimeError):
        Settings(**{"jwt_secret": "test-secret-with-at-least-32-characters", **overrides}).validate()
