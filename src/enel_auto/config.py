from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    imap_host: str = "imap.gmail.com"
    imap_user: str
    imap_pass: str
    contacts_path: str = "config.yaml"
    downloads_dir: str = "downloads"
    state_path: str = "state.json"
    evolution_api_url: str = "http://127.0.0.1:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "Vega"
    poll_interval_seconds: int = 3600

    @field_validator(
        "imap_host",
        "imap_user",
        "imap_pass",
        "contacts_path",
        "downloads_dir",
        "state_path",
        "evolution_api_url",
        "evolution_api_key",
        "evolution_instance",
    )
    @classmethod
    def _strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
