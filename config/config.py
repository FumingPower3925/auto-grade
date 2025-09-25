import os
import tomllib
from typing import Any

from pydantic import BaseModel

from config.models import DatabaseConfig, LLMConfig, ServerConfig


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()

    def __init__(self) -> None:
        toml_config = self._load_toml_config()
        super().__init__(**toml_config)

    def _load_toml_config(self) -> dict[str, Any]:
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        if os.path.exists(config_path):
            with open(config_path, "rb") as f:
                return tomllib.load(f)
        return {}


class ConfigManager:
    """Singleton configuration manager."""

    _instance: Config | None = None

    @classmethod
    def get_config(cls) -> Config:
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance

    @classmethod
    def reload_config(cls) -> Config:
        cls._instance = None
        return cls.get_config()

    @classmethod
    def reset(cls) -> None:
        cls._instance = None


def get_config() -> Config:
    return ConfigManager.get_config()
