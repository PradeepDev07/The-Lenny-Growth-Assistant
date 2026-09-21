from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Application Configuration.
    Reads environment variables from the OS and falls back to .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./growth_assistant.db"

    # Ollama (Local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Cloud Providers (Secrets - never expose directly in public endpoints)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    OPENROUTER_API_KEY: str = Field(default="")
    OPENROUTER_MODEL: str = "anthropic/claude-3.7-sonnet"

    # Task Router Mappings
    MODEL_FOR_INTENT: str = "gemini-2.5-flash-lite"
    MODEL_FOR_RETRIEVAL_QA: str = "gemini-2.5-flash"
    MODEL_FOR_ESSAY: str = "anthropic/claude-3.7-sonnet"
    MODEL_FOR_ARTIFACT: str = "gemini-2.5-flash"

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def has_openrouter(self) -> bool:
        return bool(self.OPENROUTER_API_KEY and self.OPENROUTER_API_KEY.strip())

    @property
    def cloud_llm_configured(self) -> bool:
        return self.has_gemini or self.has_openrouter


settings = Settings()
