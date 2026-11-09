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
