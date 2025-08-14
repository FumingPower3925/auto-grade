import pytest
from unittest.mock import patch, MagicMock
from typing import Type

from src.repository.db.redis import RedisDBClient
from src.repository.vdb.redis import RedisVDBClient
from src.repository.cache.redis import RedisCacheClient
from src.repository.db.factory import get_db_client
from src.repository.vdb.factory import get_vdb_client
from src.repository.cache.factory import get_cache_client
from config.config import ConfigManager


class TestRedisClients:
    """Unit tests for Redis clients."""

    @pytest.mark.parametrize("client_class", [RedisDBClient, RedisVDBClient, RedisCacheClient])
    def test_health_check_healthy(self, client_class: Type[RedisDBClient | RedisVDBClient | RedisCacheClient]) -> None:
        """Test health check when Redis is healthy."""
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.ping.return_value = True
            
            client = client_class(host="localhost", port=6379, db=0)
            health = client.health()
            
            assert health == {"status": "healthy"}
            mock_instance.ping.assert_called_once()

    @pytest.mark.parametrize("client_class", [RedisDBClient, RedisVDBClient, RedisCacheClient])
    def test_health_check_unhealthy(self, client_class: Type[RedisDBClient | RedisVDBClient | RedisCacheClient]) -> None:
        """Test health check when Redis is unhealthy."""
        with patch('redis.Redis') as mock_redis:
            mock_instance = mock_redis.return_value
            mock_instance.ping.side_effect = Exception("Connection error")
            
            client = client_class(host="localhost", port=6379, db=0)
            health = client.health()
            
            assert health["status"] == "unhealthy"
            assert "Connection error" in health["error"]
            mock_instance.ping.assert_called_once()


class TestFactories:
    """Unit tests for repository factories."""

    def setup_method(self) -> None:
        """Reset config manager before each test."""
        ConfigManager.reset()

    @patch('src.repository.db.factory.get_config')
    def test_get_db_client_factory(self, mock_get_config: MagicMock) -> None:
        """Test the DB client factory."""
        mock_config = MagicMock()
        mock_config.db.provider = "redis"
        mock_config.redis.host = "redis_host"
        mock_config.redis.port = 6379
        mock_config.db.db = 0
        mock_get_config.return_value = mock_config

        with patch('src.repository.db.factory.RedisDBClient') as mock_redis_client:
            client = get_db_client()
            mock_redis_client.assert_called_once_with(host="redis_host", port=6379, db=0)
            assert client == mock_redis_client.return_value

    @patch('src.repository.vdb.factory.get_config')
    def test_get_vdb_client_factory(self, mock_get_config: MagicMock) -> None:
        """Test the VDB client factory."""
        mock_config = MagicMock()
        mock_config.vdb.provider = "redis"
        mock_config.redis.host = "redis_host"
        mock_config.redis.port = 6379
        mock_config.vdb.db = 1
        mock_get_config.return_value = mock_config

        with patch('src.repository.vdb.factory.RedisVDBClient') as mock_redis_client:
            client = get_vdb_client()
            mock_redis_client.assert_called_once_with(host="redis_host", port=6379, db=1)
            assert client == mock_redis_client.return_value

    @patch('src.repository.cache.factory.get_config')
    def test_get_cache_client_factory(self, mock_get_config: MagicMock) -> None:
        """Test the Cache client factory."""
        mock_config = MagicMock()
        mock_config.cache.provider = "redis"
        mock_config.redis.host = "redis_host"
        mock_config.redis.port = 6379
        mock_config.cache.db = 2
        mock_get_config.return_value = mock_config

        with patch('src.repository.cache.factory.RedisCacheClient') as mock_redis_client:
            client = get_cache_client()
            mock_redis_client.assert_called_once_with(host="redis_host", port=6379, db=2)
            assert client == mock_redis_client.return_value

    @patch('src.repository.db.factory.get_config')
    def test_db_factory_unsupported_provider(self, mock_get_config: MagicMock) -> None:
        """Test DB factory raises error for unsupported provider."""
        mock_config = MagicMock()
        mock_config.db.provider = "unsupported_db"
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="Unsupported DB provider: unsupported_db"):
            get_db_client()

    @patch('src.repository.vdb.factory.get_config')
    def test_vdb_factory_unsupported_provider(self, mock_get_config: MagicMock) -> None:
        """Test VDB factory raises error for unsupported provider."""
        mock_config = MagicMock()
        mock_config.vdb.provider = "unsupported_vdb"
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="Unsupported VDB provider: unsupported_vdb"):
            get_vdb_client()

    @patch('src.repository.cache.factory.get_config')
    def test_cache_factory_unsupported_provider(self, mock_get_config: MagicMock) -> None:
        """Test Cache factory raises error for unsupported provider."""
        mock_config = MagicMock()
        mock_config.cache.provider = "unsupported_cache"
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="Unsupported cache provider: unsupported_cache"):
            get_cache_client()
