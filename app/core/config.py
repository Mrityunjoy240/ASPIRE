# app/core/config.py
# ASPIRE configuration via pydantic-settings (DM-API01, DM-LLM01)

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database (PostgreSQL / Supabase)
    database_url: str

    # LLM Service (DM-LLM01: Agent -> LLMService -> OpenRouter)
    llm_provider: Literal["openrouter", "mock"] = "mock"
    llm_model: str = "openai/gpt-4o-mini"
    llm_api_key: str = ""
    llm_max_retries: int = 1
    llm_backoff_base: float = 0.5
    llm_timeout: float = 30.0

    # Embeddings (RAG / Learning Workspace)
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # Supabase (FROZEN names — legacy names forbidden)
    next_public_supabase_url: str = ""
    next_public_supabase_publishable_key: str = ""
    supabase_jwks_uri: str = ""

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # Time-based scheduler (DM-AG03 / 03 §8.3): startup evaluation + every
    # 5 minutes. Production default on; tests disable it (tests/conftest.py)
    # so the test suite never connects to the configured DATABASE_URL.
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
