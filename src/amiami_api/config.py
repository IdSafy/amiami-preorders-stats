from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env", env_prefix="AMIAMI_", extra="ignore")

    username: str = Field(alias="AMIAMI_LOGIN")
    password: str
    store_file_path: Path = Field(default=Path("./orders.json"))
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
