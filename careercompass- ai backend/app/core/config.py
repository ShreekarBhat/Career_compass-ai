from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CareerCompass AI"
    env: str = "dev"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120
    max_upload_mb: int = 5

    database_url: str = "postgresql+psycopg2://careercompass:careercompass@localhost:5432/careercompass"
    redis_url: str = "redis://localhost:6379/0"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    use_sentence_transformers: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    job_providers: str = "seed,remotive,adzuna"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"

    telegram_bot_token: str = ""

    auto_seed: bool = True
    scheduler_enabled: bool = False

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        # Hosts such as Render give "postgresql://" or "postgres://"; SQLAlchemy 2.1+ would then pick the
        # psycopg3 driver, which is not installed. This project uses psycopg2.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix):]
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def providers_list(self) -> list[str]:
        return [p.strip().lower() for p in self.job_providers.split(",") if p.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.env.lower() == "prod" and s.jwt_secret == "change-me-in-production":
        raise RuntimeError("Set a strong JWT_SECRET before running with ENV=prod")
    return s


settings = get_settings()