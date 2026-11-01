from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Multi-Agent Research Assistant"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    allowed_origins: str | list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return self.allowed_origins

    semantic_scholar_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    llm_provider: str = "groq"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:latest"
    local_storage_path: str = "backend/data"
    max_results_limit: int = 20
    session_ttl_days: int = 30
    auth_required: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for app startup and DI."""

    return Settings()
