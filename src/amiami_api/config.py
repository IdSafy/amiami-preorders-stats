from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env", env_prefix="AMIAMI_", extra="ignore")

    username: str = Field(alias="AMIAMI_LOGIN")
    password: str = Field(alias="AMIAMI_PASSWORD")
    store_file_path: Path = Field(default=Path("./orders.json"))
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_white_list: list[str] = Field(default_factory=list, alias="TELEGRAM_BOT_WHITE_LIST")
