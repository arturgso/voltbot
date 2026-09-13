from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    imap_host: str = "imap.gmail.com"
    imap_user: str
    imap_pass: str

    @field_validator("imap_user", "imap_pass")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

@lru_cache()
def get_settings() -> Settings:
    return Settings() # type: ignore
