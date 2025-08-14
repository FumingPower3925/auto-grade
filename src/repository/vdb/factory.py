from config.config import get_config
from src.repository.vdb.client import VDBClient
from src.repository.vdb.redis import RedisVDBClient

def get_vdb_client() -> VDBClient:
    """Factory function to get the configured vector database client."""
    config = get_config()
    if config.vdb.provider == "redis":
        return RedisVDBClient(
            host=config.redis.host,
            port=config.redis.port,
            db=config.vdb.db
        )
    raise ValueError(f"Unsupported VDB provider: {config.vdb.provider}")