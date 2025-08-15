from config.config import get_config
from src.repository.db.base import DatabaseRepository


def get_database_repository() -> DatabaseRepository:
    """Factory function to get the configured database repository."""
    config = get_config()
    db_type = config.database.type.lower()

    if db_type == "ferretdb":
        from src.repository.db.ferretdb.repository import FerretDBRepository
        return FerretDBRepository()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")