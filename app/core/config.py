import json
from functools import lru_cache
from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Events Manager API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str = Field(
        default="postgresql+asyncpg://production:nFM6sNgzHkzEWNS@eventsmanager.cij22sscyvr9.us-east-1.rds.amazonaws.com:5432/postgres"
    )
    sync_database_url: str = Field(
        default="postgresql://production:nFM6sNgzHkzEWNS@eventsmanager.cij22sscyvr9.us-east-1.rds.amazonaws.com:5432/postgres"
    )

    # String en .env para evitar que pydantic-settings haga json.loads antes de validar.
    cors_origins_str: str = Field(
        default="http://44.203.12.113:4200",
        validation_alias="CORS_ORIGINS",
    )

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        s = self.cors_origins_str.strip()
        if not s:
            return ["http://44.203.12.113:4200"]
        if s.startswith("["):
            return json.loads(s)
        return [x.strip() for x in s.split(",") if x.strip()]

    upload_dir: str = "uploads"
    max_upload_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
