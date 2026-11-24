from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables / backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MH Companion API"
    environment: str = "development"

    # Postgres (Supabase). Use the pooler URL in transaction mode, with the
    # asyncpg driver: postgresql+asyncpg://user:pass@host:6543/postgres
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"

    # Supabase Auth
    supabase_url: str = "http://127.0.0.1:54321"
    # Only for projects still on the legacy shared HS256 secret. Leave empty to
    # verify with the project's asymmetric keys (JWKS), which is the default.
    supabase_jwt_secret: str = ""
    jwt_audience: str = "authenticated"

    # Bumped whenever the terms / privacy text changes; students re-consent.
    current_policy_version: str = "2026-11-v1"

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
