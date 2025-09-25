from src.repository.db.factory import get_database_repository


class HealthService:
    """Service for handling health checks."""

    def __init__(self) -> None:
        self.db_repository = get_database_repository()

    def check_health(self) -> bool:
        """Check the health of all dependencies."""
        return self.db_repository.health()
