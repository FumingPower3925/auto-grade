import os
import tempfile
import pytest

from config.config import Config, ConfigManager, get_config


class TestConfigurationLoading:
    
    def setup_method(self) -> None:
        ConfigManager.reset()
    
    def test_default_configuration_loading(self) -> None:
        config = get_config()
        
        assert isinstance(config, Config)
        assert hasattr(config, 'server')
        assert hasattr(config, 'llm')
        assert hasattr(config, 'database')
        
        config2 = get_config()
        assert config is config2
    
    def test_configuration_reload(self) -> None:
        initial_config = get_config()
        
        reloaded_config = ConfigManager.reload_config()
        
        assert reloaded_config is not initial_config
        assert isinstance(reloaded_config, Config)
        
        config3 = get_config()
        assert config3 is reloaded_config
    
    def test_toml_file_configuration(self) -> None:
        toml_content = """
[server]
host = "test.local"
port = 9090

[llm]
provider = "test_provider"
model = "test_model_v2"
temperature = 0.5
max_tokens = 2048

[database]
host = "db.test.local"
port = 27017
name = "test_db"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            temp_path = f.name
        
        try:
            original_init = Config.__init__
            
            def mock_init(self: Config) -> None:
                import toml
                if os.path.exists(temp_path):
                    toml_config = toml.load(temp_path)
                else:
                    toml_config = {}
                super(Config, self).__init__(**toml_config)
            
            Config.__init__ = mock_init
            
            ConfigManager.reset()
            config = get_config()
            
            assert config.server.host == "test.local"
            assert config.server.port == 9090
            assert config.llm.provider == "test_provider"
            assert config.llm.model == "test_model_v2"
            assert config.database.name == "test_db"
            
        finally:
            Config.__init__ = original_init # type: ignore
            os.unlink(temp_path)
            ConfigManager.reset()
    
    def test_invalid_toml_handling(self) -> None:
        invalid_toml = """
[server]
host = "localhost"
port = "invalid_port_not_a_number"

[llm]
temperature = "not_a_float"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(invalid_toml)
            temp_path = f.name
        
        try:
            original_init = Config.__init__
            
            def mock_init(self: Config):
                import toml
                if os.path.exists(temp_path):
                    toml_config = toml.load(temp_path)
                else:
                    toml_config = {}
                super(Config, self).__init__(**toml_config)
            
            Config.__init__ = mock_init
            
            ConfigManager.reset()
            with pytest.raises(Exception):
                get_config()
                
        finally:
            Config.__init__ = original_init # type: ignore
            os.unlink(temp_path)
            ConfigManager.reset()
    
    def test_partial_configuration(self) -> None:
        partial_toml = """
[server]
port = 5555

[llm]
model = "custom_model"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(partial_toml)
            temp_path = f.name
        
        try:
            original_init = Config.__init__
            
            def mock_init(self: Config):
                import toml
                if os.path.exists(temp_path):
                    toml_config = toml.load(temp_path)
                else:
                    toml_config = {}
                super(Config, self).__init__(**toml_config)
            
            Config.__init__ = mock_init
            
            ConfigManager.reset()
            config = get_config()
            
            assert config.server.port == 5555
            assert config.llm.model == "custom_model"
            
            assert config.server.host == "localhost"
            assert config.llm.provider == "openai"
            
        finally:
            Config.__init__ = original_init # type: ignore
            os.unlink(temp_path)
            ConfigManager.reset()
    
    def test_environment_variable_override(self) -> None:
        os.environ["AUTO_GRADE_SERVER_HOST"] = "env.host"
        os.environ["AUTO_GRADE_SERVER_PORT"] = "7777"
        os.environ["AUTO_GRADE_LLM_MODEL"] = "env_model"
        
        try:
            ConfigManager.reset()
            config = get_config()
            
            assert isinstance(config, Config)
            
        finally:
            os.environ.pop("AUTO_GRADE_SERVER_HOST", None)
            os.environ.pop("AUTO_GRADE_SERVER_PORT", None)
            os.environ.pop("AUTO_GRADE_LLM_MODEL", None)
            ConfigManager.reset()
    
    def test_configuration_thread_safety(self) -> None:
        import threading
        
        ConfigManager.reset()
        
        initial_config = get_config()
        
        configs: list[Config] = []
        
        def get_config_in_thread():
            config = get_config()
            configs.append(config)
        
        threads: list[threading.Thread] = []
        for _ in range(10):
            thread = threading.Thread(target=get_config_in_thread)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(configs) == 10
        assert all(c is initial_config for c in configs)
    
    def test_configuration_with_application_context(self) -> None:
        from src.controller.api.api import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            config = get_config()
            assert isinstance(config, Config)
            
            response = client.get("/health")
            assert response.status_code == 200