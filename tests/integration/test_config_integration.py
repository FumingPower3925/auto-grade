import os
import tempfile
import pytest

from config.config import Config, ConfigManager, get_config


class TestConfigIntegration:
    """Integration tests for the configuration system."""
    
    def setup_method(self) -> None:
        """Reset singleton instance before each test."""
        ConfigManager.reset()
    
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            temp_path: str = f.name
        
        original_init = None
        try:
            # Store original method
            original_init = Config.__init__
            
            def mock_init(self: Config) -> None:
                import toml
                if os.path.exists(temp_path):
                    toml_config = toml.load(temp_path)
                else:
                    toml_config = {}
                super(Config, self).__init__(**toml_config)
            
            Config.__init__ = mock_init
            config = Config()
                
            assert config.server.host == "test.example.com"
            assert config.server.port == 5000
            assert config.llm.provider == "test_provider"
            assert config.llm.model == "test_model"
        finally:
            if original_init is not None:
                Config.__init__ = original_init
            os.unlink(temp_path)
    
    def test_config_with_invalid_toml_structure(self) -> None:
        """Test handling of TOML with invalid structure for our models."""
        invalid_toml_content = """
[server]
host = "localhost"
port = "not_a_number"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(invalid_toml_content)
            temp_path: str = f.name
        # Store original method
        original_init = Config.__init__
        try:
            def mock_init(self: Config) -> None:
                import toml
                if os.path.exists(temp_path):
                    toml_config = toml.load(temp_path)
                else:
                    toml_config = {}
                super(Config, self).__init__(**toml_config)
            
            Config.__init__ = mock_init  # type: ignore[method-assign]
            
            # Should raise validation error from Pydantic
            with pytest.raises(Exception):
                Config()
        finally:
            Config.__init__ = original_init
            os.unlink(temp_path)
    
    def test_config_manager_with_real_config_file(self) -> None:
        """Test ConfigManager with actual config file."""
        # Test with the actual config.toml file if it exists
        config = get_config()
        
        assert isinstance(config, Config)
        assert hasattr(config, 'server')
        assert hasattr(config, 'llm')
        
        # Test that subsequent calls return the same instance
        config2 = get_config()
        assert config is config2
        
        # Test reload functionality
        config3 = ConfigManager.reload_config()
        assert config3 is not config
        assert isinstance(config3, Config)
        config3 = ConfigManager.reload_config()
        assert config3 is not config
        assert isinstance(config3, Config)
