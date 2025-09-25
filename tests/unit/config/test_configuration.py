import os
import tempfile
from typing import Any
from unittest.mock import patch

import pytest

from config.config import Config, ConfigManager, get_config
from config.models import LLMConfig, ServerConfig


class TestConfig:
    """Tests for Config class."""

    def test_config_default_initialization(self) -> None:
        """Test Config initializes with defaults when no TOML exists."""
        with patch("os.path.exists", return_value=False):
            config = Config()

        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.llm, LLMConfig)
        assert config.server.host == "localhost"
        assert config.server.port == 8080
        assert config.llm.provider == "openai"
        assert config.llm.model == "o4-mini"

    def test_config_loads_from_toml_file(self) -> None:
        """Test Config loads values from TOML file."""
        toml_content: dict[str, Any] = {
            "server": {"host": "0.0.0.0", "port": 9000},
            "llm": {"provider": "anthropic", "model": "claude-3"},
        }

        with patch("os.path.exists", return_value=True), patch("tomllib.load", return_value=toml_content):
            config = Config()

        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9000
        assert config.llm.provider == "anthropic"
        assert config.llm.model == "claude-3"

    def test_config_partial_toml_file(self) -> None:
        """Test Config handles partial TOML with defaults."""
        toml_content = {"server": {"port": 3000}}

        with patch("os.path.exists", return_value=True), patch("tomllib.load", return_value=toml_content):
            config = Config()

        assert config.server.port == 3000
        assert config.server.host == "localhost"
        assert config.llm.provider == "openai"
        assert config.llm.model == "o4-mini"

    def test_config_empty_toml_file(self) -> None:
        """Test Config handles empty TOML file."""
        with patch("os.path.exists", return_value=True), patch("tomllib.load", return_value={}):
            config = Config()

        assert config.server.host == "localhost"
        assert config.server.port == 8080
        assert config.llm.provider == "openai"
        assert config.llm.model == "o4-mini"

    def test_toml_load_exception_handling(self) -> None:
        """Test Config handles TOML loading exceptions."""
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "tomllib.load",
                side_effect=ValueError("TOML parse error"),
            ),
        ):
            with pytest.raises(ValueError):
                Config()

    def test_config_with_invalid_toml_structure(self) -> None:
        """Test handling of TOML with invalid structure."""
        invalid_toml = {"server": {"host": "localhost", "port": "not_a_number"}}

        with patch("os.path.exists", return_value=True), patch("tomllib.load", return_value=invalid_toml):
            with pytest.raises((TypeError, ValueError)):
                Config()

    def test_real_toml_file_loading(self) -> None:
        """Test loading from an actual temporary TOML file."""
        toml_content = """
[server]
host = "test.example.com"
port = 5000

[llm]
provider = "test_provider"
model = "test_model"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            with patch("os.path.join", return_value=temp_path), patch("os.path.exists", return_value=True):
                config = Config()

            assert config.server.host == "test.example.com"
            assert config.server.port == 5000
            assert config.llm.provider == "test_provider"
            assert config.llm.model == "test_model"
        finally:
            os.unlink(temp_path)


class TestConfigManager:
    """Tests for ConfigManager singleton."""

    def setup_method(self) -> None:
        """Reset singleton instance before each test."""
        ConfigManager.reset()

    def test_singleton_behavior(self) -> None:
        """Test ConfigManager maintains singleton pattern."""
        with patch("os.path.exists", return_value=False):
            config1 = ConfigManager.get_config()
            config2 = ConfigManager.get_config()

        assert config1 is config2
        assert isinstance(config1, Config)

    def test_reload_config_creates_new_instance(self) -> None:
        """Test reload_config creates a new config instance."""
        with patch("os.path.exists", return_value=False):
            config1 = ConfigManager.get_config()
            config2 = ConfigManager.reload_config()
            config3 = ConfigManager.get_config()

        assert config1 is not config2
        assert config2 is config3
        assert isinstance(config2, Config)

    def test_multiple_reload_calls(self) -> None:
        """Test multiple reload calls work correctly."""
        with patch("os.path.exists", return_value=False):
            original = ConfigManager.get_config()
            reloaded1 = ConfigManager.reload_config()
            reloaded2 = ConfigManager.reload_config()
            current = ConfigManager.get_config()

        assert original is not reloaded1
        assert reloaded1 is not reloaded2
        assert reloaded2 is current


class TestGetConfigFunction:
    """Tests for get_config convenience function."""

    def setup_method(self) -> None:
        """Reset singleton instance before each test."""
        ConfigManager.reset()

    def test_get_config_returns_config_instance(self) -> None:
        """Test get_config function returns Config instance."""
        with patch("os.path.exists", return_value=False):
            config = get_config()

        assert isinstance(config, Config)

    def test_get_config_uses_singleton(self) -> None:
        """Test get_config function uses ConfigManager singleton."""
        with patch("os.path.exists", return_value=False):
            config1 = get_config()
            config2 = get_config()

        assert config1 is config2
