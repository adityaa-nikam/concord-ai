import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "TAT Guardian (CONCORD AI)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://concord_user:concord_secret@localhost:5432/concord_tat_db"
    
    # SQLite fallback for testing/local standalone running without postgres docker
    SQLITE_FALLBACK_URL: str = "sqlite:///./tat_guardian.db"
    USE_SQLITE_FALLBACK: bool = False

    # LLM Settings
    LLM_PROVIDER: str = "mistral"
    MISTRAL_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "mistral-small-latest"

    # Mock Fintech Settings
    MOCK_BANK_LATENCY_MS: int = 50
    MOCK_SIMULATE_DELAYS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
