from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stockchef_app:stockchef_app@localhost:5432/stockchef"
    alembic_database_url: str = "postgresql+psycopg://stockchef:stockchef@localhost:5432/stockchef"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
