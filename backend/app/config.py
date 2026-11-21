from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / '.env',
        env_file_encoding='utf-8-sig', extra='ignore',
    )
    supabase_project_ref: str = 'lapzymfujekspcssruvn'
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    database_url: str = ''
    public_whatsapp: str = '51945928413'


@lru_cache
def get_settings() -> Settings:
    return Settings()
