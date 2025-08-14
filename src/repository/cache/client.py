from abc import ABC, abstractmethod
from typing import Any

class CacheClient(ABC):
    """Abstract base class for a cache client."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Check the health of the cache."""
        raise NotImplementedError