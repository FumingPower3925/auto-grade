from typing import Any
import redis
from src.repository.vdb.client import VDBClient

class RedisVDBClient(VDBClient):
    """Redis implementation of the vector database client."""

    def __init__(self, host: str, port: int, db: int):
        self.client = redis.Redis(host=host, port=port, db=db)

    def health(self) -> dict[str, Any]:
        """Check the health of the Redis vector database."""
        try:
            self.client.ping() # type: ignore
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}