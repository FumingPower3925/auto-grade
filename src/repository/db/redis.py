from typing import Any
import redis
from src.repository.db.client import DBClient

class RedisDBClient(DBClient):
    """Redis implementation of the database client."""

    def __init__(self, host: str, port: int, db: int):
        self.client = redis.Redis(host=host, port=port, db=db)

    def health(self) -> dict[str, Any]:
        """Check the health of the Redis database."""
        try:
            self.client.ping() # type: ignore
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}