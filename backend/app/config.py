"""Application settings and YAML config loading for municipalities and keywords."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class Settings(BaseSettings):
    """Environment-driven settings."""

    model_config = SettingsConfigDict(env_prefix="EK_", env_file=".env", extra="ignore")

    app_name: str = "Etelä-Karjala ICT - yrityshaku"
    prh_base_url: str = Field(default="https://avoindata.prh.fi/opendata-ytj-api/v3")
    prh_timeout_seconds: float = 120.0
    prh_max_retries: int = 5
    # Julkinen hostaus: aseta molemmat → kaikki pyynnöt (paitsi OPTIONS) vaativat Authorization: Basic …
    basic_auth_user: str | None = Field(default=None)
    basic_auth_password: str | None = Field(default=None)
    # Monivaiheinen Docker: aseta repo-juuri (esim. /srv), jossa on frontend/dist/
    project_root: str | None = Field(default=None)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"]
    )
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.is_file():
        logger.warning("Config file missing: %s", path)
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_region_config() -> dict[str, Any]:
    return _load_yaml("region.yaml")


@lru_cache
def get_keywords_config() -> dict[str, Any]:
    return _load_yaml("keywords.yaml")


def clear_config_cache() -> None:
    """Clear caches (e.g. for tests)."""
    get_settings.cache_clear()
    get_region_config.cache_clear()
    get_keywords_config.cache_clear()
