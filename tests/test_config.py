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
    settings = Settings(jwt_secret="private-jwt-value", groq_key="private-groq-value",
                        database_url="postgresql://user:private-database-value@localhost/db",
                        redis_url="redis://:private-redis-value@localhost/0")
    assert "private-jwt-value" not in repr(settings)
    assert "private-groq-value" not in repr(settings)
    assert "private-database-value" not in repr(settings)
    assert "private-redis-value" not in repr(settings)


@pytest.mark.parametrize("overrides", [
    {"jwt_secret": " " * 64}, {"token_minutes": 0}, {"daily_limit": 0},
    {"groq_rpm": -1}, {"groq_timeout": 0}, {"groq_timeout": float("nan")},
    {"groq_timeout": float("inf")}, {"groq_timeout": 301},
    {"jwt_issuer": " "}, {"jwt_audience": ""}, {"groq_model": "../models/test"},
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


def test_groq_environment_configuration(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "mock-only")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("GROQ_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("GROQ_REQUESTS_PER_MINUTE", "7")
    settings = Settings(jwt_secret="test-secret-with-at-least-32-characters")
    settings.validate()
    assert settings.groq_key == "mock-only"
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.groq_timeout == 12.5
    assert settings.groq_rpm == 7
    assert "mock-only" not in repr(settings)


def test_groq_defaults_do_not_read_old_provider_configuration(monkeypatch):
    for key in ("GROQ_API_KEY", "GROQ_MODEL", "GROQ_TIMEOUT_SECONDS", "GROQ_REQUESTS_PER_MINUTE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "obsolete-mock-only")
    monkeypatch.setenv("GEMINI_MODEL", "obsolete-model")
    settings = Settings(jwt_secret="test-secret-with-at-least-32-characters")
    settings.validate()
    assert settings.groq_key == ""
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.groq_timeout == 20
    assert settings.groq_rpm == 5


@pytest.mark.parametrize(("key", "value"), [
    ("GROQ_TIMEOUT_SECONDS", "0"), ("GROQ_TIMEOUT_SECONDS", "nan"),
    ("GROQ_TIMEOUT_SECONDS", "inf"), ("GROQ_TIMEOUT_SECONDS", "301"),
    ("GROQ_TIMEOUT_SECONDS", "invalid"), ("GROQ_REQUESTS_PER_MINUTE", "0"),
    ("GROQ_REQUESTS_PER_MINUTE", "-1"), ("GROQ_REQUESTS_PER_MINUTE", "1.5"),
    ("GROQ_MODEL", ""), ("GROQ_MODEL", "../models/test"),
    ("GROQ_MODEL", "openai//model"), ("GROQ_MODEL", "https://example.com/model"),
    ("GROQ_MODEL", "openai/model?key=value"),
])
def test_invalid_groq_environment_fails_before_start(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises((RuntimeError, ValueError)):
        Settings(jwt_secret="test-secret-with-at-least-32-characters").validate()


def test_health_indicator_uses_groq(client):
    payload = client.get("/api/healthz").json()
    assert payload == {"status": "ok", "database": "ok", "redis": True, "groq_configured": False}


def test_legacy_client_import_delegates_to_groq():
    from app.ai.gemini import GeminiAnalyzer
    from app.ai.groq import GroqAnalyzer
    assert GeminiAnalyzer is GroqAnalyzer


def test_sqlite_preserves_instants_as_aware_utc():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import literal, select
    from app.database.session import UTCDateTime, create_database
    engine, factory = create_database("sqlite:///:memory:")
    original = datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=-5)))
    try:
        with factory() as db:
            result = db.scalar(select(literal(original, type_=UTCDateTime(timezone=True))))
            assert result == original
            assert result.hour == 17
            assert result.tzinfo == timezone.utc
    finally:
        engine.dispose()
