from abc import ABC, abstractmethod
from typing import Any

class DBClient(ABC):
    """Abstract base class for a database client."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Check the health of the database."""
        raise NotImplementedError