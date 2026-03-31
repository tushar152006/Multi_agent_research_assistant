from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Multi-Agent Research Assistant"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    semantic_scholar_api_key: str | None = None
    llm_provider: str = "heuristic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    local_storage_path: str = "backend/data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for app startup and DI."""

    return Settings()
