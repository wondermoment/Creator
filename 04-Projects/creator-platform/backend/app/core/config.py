from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    project_name: str = "Creator Intelligence Platform"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://creator:creator_dev_2025@localhost:5432/creator_db"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # AI
    anthropic_api_key: str = ""

    # Default tenant for dev mode
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"


settings = Settings()
