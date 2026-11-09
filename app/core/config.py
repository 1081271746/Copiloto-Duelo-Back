import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("APP_DATABASE_URL", "sqlite:///./copilot.db"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or os.getenv("SESSION_SECRET", ""), repr=False)
    jwt_issuer: str = field(default_factory=lambda: os.getenv("JWT_ISSUER", "grief-copilot"))
    jwt_audience: str = field(default_factory=lambda: os.getenv("JWT_AUDIENCE", "grief-copilot-api"))
    token_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_MINUTES", "30")))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    cors_origins: list[str] = field(default_factory=lambda: [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:4200").split(",") if origin.strip()
    ])
    gemini_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""), repr=False)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    gemini_timeout: float = field(default_factory=lambda: float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20")))
    gemini_rpm: int = field(default_factory=lambda: int(os.getenv("GEMINI_REQUESTS_PER_MINUTE", "5")))
    daily_limit: int = field(default_factory=lambda: int(os.getenv("AI_DAILY_USER_LIMIT", "20")))
    default_country: str = field(default_factory=lambda: os.getenv("DEFAULT_COUNTRY", "CO"))
    emergency_resources: dict = field(default_factory=lambda: json.loads(os.getenv(
        "EMERGENCY_RESOURCES_JSON",
        '{"CO":{"emergency_number":"123","support_name":"Directorio de líneas territoriales de salud mental","support_url":"https://www.minsalud.gov.co/"}}',
    )))

    def validate(self) -> None:
        if len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 characters")
        if self.token_minutes < 1 or self.daily_limit < 1 or self.gemini_rpm < 1:
            raise RuntimeError("Configured limits must be positive")
        if "*" in self.cors_origins:
            raise RuntimeError("Explicit CORS origins are required")


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    settings = Settings()
    settings.validate()
    return settings
