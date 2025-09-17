from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock

from src.controller.api.api import app
from src.controller.api.models import HealthResponse


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.service.health_service.HealthService.check_health')
    def test_health_check_healthy(self, mock_check_health: MagicMock) -> None:
        """Test health endpoint when service is healthy."""
        mock_check_health.return_value = True
        
        response = self.client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "Auto Grade API is running and connected to the database"

    @patch('src.service.health_service.HealthService.check_health')
    def test_health_check_unhealthy(self, mock_check_health: MagicMock) -> None:
        """Test health endpoint when service is unhealthy."""
        mock_check_health.return_value = False
        
        response = self.client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["message"] == "Auto Grade API is running but could not connect to the database"

    def test_health_endpoint_validates_response_model(self) -> None:
        """Test that health response validates against HealthResponse model."""
        with patch('src.service.health_service.HealthService.check_health', return_value=True):
            response = self.client.get("/health")
            data = response.json()
            
            health_response = HealthResponse(**data)
            assert health_response.status == "healthy"

    def test_health_endpoint_with_head_method(self) -> None:
        """Test HEAD request to health endpoint."""
        with patch('src.service.health_service.HealthService.check_health', return_value=True):
            response = self.client.head("/health")
            assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_invalid_method(self) -> None:
        """Test health endpoint rejects invalid HTTP methods."""
        response = self.client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_health_endpoint_headers(self) -> None:
        """Test health endpoint response headers."""
        with patch('src.service.health_service.HealthService.check_health', return_value=True):
            response = self.client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            assert "application/json" in response.headers["content-type"]
            assert "content-length" in response.headers


class TestAPIMetadata:
    """Tests for API metadata and documentation."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_api_title(self) -> None:
        """Test API has correct title."""
        assert app.title == "Auto Grade API"

    def test_api_description(self) -> None:
        """Test API has correct description."""
        assert app.description == "A PoC of an automatic bulk assignment grader LLM engine"

    def test_api_version(self) -> None:
        """Test API has correct version."""
        assert app.version == "0.1.0"

    def test_openapi_schema_accessible(self) -> None:
        """Test OpenAPI schema is accessible."""
        response = self.client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        schema = response.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "Auto Grade API"

    def test_docs_endpoint_accessible(self) -> None:
        """Test API documentation is accessible."""
        response = self.client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_health_route_openapi_tags(self) -> None:
        """Test health route has correct OpenAPI tags."""
        response = self.client.get("/openapi.json")
        schema = response.json()
        
        health_path = schema["paths"]["/health"]["get"]
        assert "Health" in health_path["tags"]
        assert "200" in health_path["responses"]

    def test_nonexistent_route_returns_404(self) -> None:
        """Test that nonexistent routes return 404."""
        response = self.client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND