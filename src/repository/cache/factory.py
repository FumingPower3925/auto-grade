from config.config import get_config
from src.repository.cache.client import CacheClient
from src.repository.cache.redis import RedisCacheClient

def get_cache_client() -> CacheClient:
    """Factory function to get the configured cache client."""
    config = get_config()
    if config.cache.provider == "redis":
        return RedisCacheClient(
            host=config.redis.host,
            port=config.redis.port,
            db=config.cache.db
        )
    raise ValueError(f"Unsupported cache provider: {config.cache.provider}")