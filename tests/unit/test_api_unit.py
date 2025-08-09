from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any
from httpx import Response

from src.controller.api.api import app
from src.controller.api.models import HealthResponse


class TestHealthEndpoint:
    """Unit tests for the health endpoint."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)
    
    def test_health_endpoint_returns_correct_status_code(self) -> None:
        """Test that health endpoint returns 200 status code."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_health_endpoint_returns_correct_response_model(self) -> None:
        """Test that health endpoint returns correct response structure."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()
        
        # Validate response structure
        assert "status" in data
        assert "message" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
    
    def test_health_endpoint_returns_expected_values(self) -> None:
        """Test that health endpoint returns expected status and message."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()
        
        assert data["status"] == "healthy"
        assert data["message"] == "Auto Grade API is running"
    
    def test_health_endpoint_response_validates_against_model(self) -> None:
        """Test that response can be validated against HealthResponse model."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()
        
        # This should not raise a validation error
        health_response = HealthResponse(**data)
        assert health_response.status == "healthy"
        assert health_response.message == "Auto Grade API is running"
    
    def test_health_endpoint_with_head_method(self) -> None:
        """Test that health endpoint responds to HEAD requests."""
        response: Response = self.client.head("/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_health_endpoint_with_invalid_method(self) -> None:
        """Test that health endpoint rejects invalid HTTP methods."""
        response: Response = self.client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestAPIMetadata:
    """Unit tests for FastAPI application metadata."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)
    
    def test_api_title_is_correct(self) -> None:
        """Test that API has correct title."""
        assert app.title == "Auto Grade API"
    
    def test_api_description_is_correct(self) -> None:
        """Test that API has correct description."""
        assert app.description == "A PoC of an automatic bulk assignment grader LLM engine"
    
    def test_api_version_is_correct(self) -> None:
        """Test that API has correct version."""
        assert app.version == "0.1.0"
    
    def test_openapi_schema_accessible(self) -> None:
        """Test that OpenAPI schema is accessible."""
        response: Response = self.client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        schema: Dict[str, Any] = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Auto Grade API"
    
    def test_docs_endpoint_accessible(self) -> None:
        """Test that API documentation is accessible."""
        response: Response = self.client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]


class TestHealthEndpointErrorHandling:
    """Unit tests for health endpoint error scenarios."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)
    
    def test_health_endpoint_content_type(self) -> None:
        """Test that health endpoint returns correct content type."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]
    
    def test_health_endpoint_response_headers(self) -> None:
        """Test that health endpoint includes expected headers."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert "content-length" in response.headers
        assert "content-type" in response.headers


class TestAPIRouteConfiguration:
    """Unit tests for API route configuration."""
    
    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)
    
    def test_health_route_has_correct_tags(self) -> None:
        """Test that health route has correct OpenAPI tags."""
        response: Response = self.client.get("/openapi.json")
        schema: Dict[str, Any] = response.json()
        
        health_path: Dict[str, Any] = schema["paths"]["/health"]["get"]
        assert "tags" in health_path
        assert "Health" in health_path["tags"]
    
    def test_health_route_has_response_model(self) -> None:
        """Test that health route has correct response model in schema."""
        response: Response = self.client.get("/openapi.json")
        schema: Dict[str, Any] = response.json()
        
        health_path: Dict[str, Any] = schema["paths"]["/health"]["get"]
        assert "responses" in health_path
        assert "200" in health_path["responses"]
    
    def test_nonexistent_route_returns_404(self) -> None:
        """Test that nonexistent routes return 404."""
        response: Response = self.client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND