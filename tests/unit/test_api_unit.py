from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any
from httpx import Response
from unittest.mock import patch, MagicMock

from src.controller.api.api import app
from src.controller.api.models import HealthResponse


@patch('src.controller.api.api.get_db_client')
@patch('src.controller.api.api.get_vdb_client')
@patch('src.controller.api.api.get_cache_client')
class TestHealthEndpoint:
    """Unit tests for the health endpoint."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)

    def test_health_endpoint_all_healthy(self, mock_cache_client: MagicMock, mock_vdb_client: MagicMock, mock_db_client: MagicMock) -> None:
        """Test health endpoint when all services are healthy."""
        mock_db_client.return_value.health.return_value = {"status": "healthy"}
        mock_vdb_client.return_value.health.return_value = {"status": "healthy"}
        mock_cache_client.return_value.health.return_value = {"status": "healthy"}

        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["status"] == "healthy"
        assert len(data["services"]) == 3
        for service in data["services"]:
            assert service["status"] == "healthy"

    def test_health_endpoint_one_unhealthy(self, mock_cache_client: MagicMock, mock_vdb_client: MagicMock, mock_db_client: MagicMock) -> None:
        """Test health endpoint when one service is unhealthy."""
        mock_db_client.return_value.health.return_value = {"status": "healthy"}
        mock_vdb_client.return_value.health.return_value = {"status": "unhealthy", "error": "VDB down"}
        mock_cache_client.return_value.health.return_value = {"status": "healthy"}

        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data: Dict[str, Any] = response.json()
        assert data["status"] == "unhealthy"
        assert any(s["service"] == "vector_db" and s["status"] == "unhealthy" for s in data["services"])

    def test_health_endpoint_factory_exception(self, mock_cache_client: MagicMock, mock_vdb_client: MagicMock, mock_db_client: MagicMock) -> None:
        """Test health endpoint when a factory raises an exception."""
        mock_db_client.side_effect = ValueError("Config error")
        mock_vdb_client.return_value.health.return_value = {"status": "healthy"}
        mock_cache_client.return_value.health.return_value = {"status": "healthy"}

        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data: Dict[str, Any] = response.json()
        assert data["status"] == "unhealthy"
        db_service = next(s for s in data["services"] if s["service"] == "database")
        assert db_service["status"] == "unhealthy"
        assert "Config error" in db_service["details"]

    def test_health_endpoint_response_validates_against_model(self, mock_cache_client: MagicMock, mock_vdb_client: MagicMock, mock_db_client: MagicMock) -> None:
        """Test that response can be validated against HealthResponse model."""
        mock_db_client.return_value.health.return_value = {"status": "healthy"}
        mock_vdb_client.return_value.health.return_value = {"status": "healthy"}
        mock_cache_client.return_value.health.return_value = {"status": "healthy"}
        
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()
        
        health_response = HealthResponse(**data)
        assert health_response.status == "healthy"

class TestAPIMetadata:
    """Unit tests for FastAPI application metadata."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)
    
    def test_api_title_is_correct(self) -> None:
        """Test that API has correct title."""
        assert app.title == "Auto Grade API"
