from config.config import get_config
from src.repository.db.client import DBClient
from src.repository.db.redis import RedisDBClient

def get_db_client() -> DBClient:
    """Factory function to get the configured database client."""
    config = get_config()
    if config.db.provider == "redis":
        return RedisDBClient(
            host=config.redis.host,
            port=config.redis.port,
            db=config.db.db
        )
    raise ValueError(f"Unsupported DB provider: {config.db.provider}")