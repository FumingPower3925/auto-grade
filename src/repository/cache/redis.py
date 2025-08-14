from typing import Any
import redis
from src.repository.cache.client import CacheClient

class RedisCacheClient(CacheClient):
    """Redis implementation of the cache client."""

    def __init__(self, host: str, port: int, db: int):
        self.client = redis.Redis(host=host, port=port, db=db)

    def health(self) -> dict[str, Any]:
        """Check the health of the Redis cache."""
        try:
            self.client.ping() # type: ignore
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}