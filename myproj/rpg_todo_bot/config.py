"""
Application settings management.
Following the pattern from backend/settings.py using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    bot_token: str
    db_name: str = "rpg_bot.db"

    # LLM API settings (optional)
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # Game balance settings
    max_daily_od: int = 50  # Maximum OD that can be earned per day

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
