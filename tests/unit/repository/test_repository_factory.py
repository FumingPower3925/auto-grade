from unittest.mock import MagicMock, patch

import pytest

from src.repository.db.factory import get_database_repository


class TestRepositoryFactory:
    """Tests for database repository factory."""

    @patch("src.repository.db.factory.get_config")
    def test_get_ferretdb_repository(self, mock_get_config: MagicMock) -> None:
        """Test getting a FerretDB repository."""
        mock_get_config.return_value.database.type = "ferretdb"

        repo = get_database_repository()

        from src.repository.db.ferretdb.repository import FerretDBRepository

        assert isinstance(repo, FerretDBRepository)

    @patch("src.repository.db.factory.get_config")
    def test_unsupported_database_type(self, mock_get_config: MagicMock) -> None:
        """Test that unsupported database type raises error."""
        mock_get_config.return_value.database.type = "unsupported_db"

        with pytest.raises(ValueError, match="Unsupported database type: unsupported_db"):
            get_database_repository()
