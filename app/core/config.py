"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
via pydantic-settings. Env var names follow ``.env.example`` exactly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Prometheus backend (mock-first MVP)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- core ---
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # --- providers ---
    llm_provider: str = "mock"
    embedding_provider: str = "mock"
    vector_store_provider: str = "local"
    cache_provider: str = "local"

    # --- storage ---
    database_url: str = "sqlite:///./prometheus.db"
    data_dir: str = "data"

    # --- models ---
    default_model: str = "mock-small"
    strong_model: str = "mock-large"
    bedrock_model_id: str = ""
    aws_region: str = "us-east-1"

    # --- security ---
    admin_api_key: str = "***"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- cache ---
    cache_similarity_threshold: float = 0.82
    cache_ttl_seconds: int = 3600
    cache_version: str = "v1"

    # --- budget ---
    daily_budget_usd: float = 2.0
    request_budget_usd: float = 0.05
    budget_warning_ratio: float = 0.7
    budget_critical_ratio: float = 0.9

    # --- limits ---
    rate_limit_per_minute: int = 30
    idempotency_ttl_seconds: int = 600

    # --- mock latency (ms) ---
    mock_latency_cheap_ms: int = 100
    mock_latency_strong_ms: int = 500

    # --- frontend plumbing (optional extras; safe defaults) ---
    server_api_url: str = "http://localhost:8000"
    next_public_api_url: str = "http://localhost:8000/api/v1"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> Any:
        """Accept a JSON array (``["http://a","http://b"]``) or a CSV string."""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # --- helpers ---
    def is_local(self) -> bool:
        return self.app_env == "local"

    def is_mock_mode(self) -> bool:
        return self.llm_provider == "mock"

    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def data_path(self, *parts: str) -> Path:
        return Path(self.data_dir).joinpath(*parts)


settings = Settings()
