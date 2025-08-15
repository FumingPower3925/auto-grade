from unittest.mock import patch, MagicMock
from src.service.health_service import HealthService


class TestHealthService:
    """Unit tests for the HealthService."""

    @patch('src.service.health_service.get_database_repository')
    def test_check_health_when_database_is_healthy(self, mock_get_repo: MagicMock) -> None:
        """Test the health check when the database repository reports healthy."""
        mock_repo = MagicMock()
        mock_repo.health.return_value = True
        mock_get_repo.return_value = mock_repo

        service = HealthService()
        is_healthy = service.check_health()

        assert is_healthy is True
        mock_repo.health.assert_called_once()

    @patch('src.service.health_service.get_database_repository')
    def test_check_health_when_database_is_unhealthy(self, mock_get_repo: MagicMock) -> None:
        """Test the health check when the database repository reports unhealthy."""
        mock_repo = MagicMock()
        mock_repo.health.return_value = False
        mock_get_repo.return_value = mock_repo

        service = HealthService()
        is_healthy = service.check_health()

        assert is_healthy is False
        mock_repo.health.assert_called_once()