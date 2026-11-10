import json
import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("APP_DATABASE_URL", "sqlite:///./copilot.db"), repr=False)
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or os.getenv("SESSION_SECRET", ""), repr=False)
    jwt_issuer: str = field(default_factory=lambda: os.getenv("JWT_ISSUER", "grief-copilot"))
    jwt_audience: str = field(default_factory=lambda: os.getenv("JWT_AUDIENCE", "grief-copilot-api"))
    token_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_MINUTES", "30")))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), repr=False)
    cors_origins: list[str] = field(default_factory=lambda: [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:4200").split(",") if origin.strip()
    ])
    groq_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""), repr=False)
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
    groq_timeout: float = field(default_factory=lambda: float(os.getenv("GROQ_TIMEOUT_SECONDS", "20")))
    groq_rpm: int = field(default_factory=lambda: int(os.getenv("GROQ_REQUESTS_PER_MINUTE", "5")))
    daily_limit: int = field(default_factory=lambda: int(os.getenv("AI_DAILY_USER_LIMIT", "20")))
    default_country: str = field(default_factory=lambda: os.getenv("DEFAULT_COUNTRY", "CO"))
    emergency_resources: dict = field(default_factory=lambda: json.loads(os.getenv(
        "EMERGENCY_RESOURCES_JSON",
        '{"CO":{"emergency_number":"123","support_name":"Directorio de líneas territoriales de salud mental","support_url":"https://www.minsalud.gov.co/"}}',
    )))

    def validate(self) -> None:
        if len(self.jwt_secret.strip()) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 characters")
        if self.token_minutes < 1 or self.daily_limit < 1 or self.groq_rpm < 1:
            raise RuntimeError("Configured limits must be positive")
        if not math.isfinite(self.groq_timeout) or not 0 < self.groq_timeout <= 300:
            raise RuntimeError("Groq timeout must be finite and between 0 and 300 seconds")
        if not self.jwt_issuer.strip() or not self.jwt_audience.strip():
            raise RuntimeError("JWT issuer and audience are required")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,99})?", self.groq_model):
            raise RuntimeError("Invalid Groq model identifier")
        if not re.fullmatch(r"[A-Z]{2}", self.default_country):
            raise RuntimeError("Invalid default country")
        if not self.cors_origins or any("*" in origin for origin in self.cors_origins):
            raise RuntimeError("Explicit CORS origins are required")
        for origin in self.cors_origins:
            try:
                parsed = urlsplit(origin)
                parsed.port
                valid = (parsed.scheme in ("http", "https") and parsed.hostname
                         and not parsed.username and not parsed.password
                         and not parsed.path and not parsed.query and not parsed.fragment)
            except ValueError:
                valid = False
            if not valid:
                raise RuntimeError("CORS entries must be exact HTTP origins")
        if not isinstance(self.emergency_resources, dict):
            raise RuntimeError("Emergency resources must be a country mapping")
        for country, resources in self.emergency_resources.items():
            if not re.fullmatch(r"[A-Z]{2}", country) or not isinstance(resources, dict):
                raise RuntimeError("Invalid emergency resource configuration")
            if any(not isinstance(value, str) or not value.strip() for value in resources.values()):
                raise RuntimeError("Emergency resource values must be nonempty text")
            if "support_url" in resources:
                parsed = urlsplit(resources["support_url"])
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                    raise RuntimeError("Invalid emergency support URL")


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    settings = Settings()
    settings.validate()
    return settings
