from abc import ABC, abstractmethod
from typing import Any

class VDBClient(ABC):
    """Abstract base class for a vector database client."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Check the health of the vector database."""
        raise NotImplementedError