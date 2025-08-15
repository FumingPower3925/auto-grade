from fastapi.testclient import TestClient
from fastapi import status
import threading
import time
from typing import Dict, Any, List
from httpx import Response

from src.controller.api.api import app
from config.config import ConfigManager


class TestAPIIntegration:
    """Integration tests for the API application."""

    def setup_method(self) -> None:
        """Set up test client and reset config."""
        ConfigManager.reset()
        self.client: TestClient = TestClient(app)

    def test_full_application_startup(self) -> None:
        """Test that the full FastAPI application starts correctly."""
        # Test that we can create a client and make requests
        with TestClient(app) as client:
            response: Response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_end_to_end(self) -> None:
        """Test health endpoint from end to end."""
        response: Response = self.client.get("/health")

        # Test status code
        assert response.status_code == status.HTTP_200_OK

        # Test response structure
        data: Dict[str, Any] = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "message" in data

        # Test response values
        assert data["status"] == "healthy"
        assert data["message"] == "Auto Grade API is running and connected to the database"

        # Test response headers
        assert response.headers["content-type"] == "application/json"

    def test_openapi_integration(self) -> None:
        """Test OpenAPI schema generation and access."""
        # Test OpenAPI JSON endpoint
        openapi_response: Response = self.client.get("/openapi.json")
        assert openapi_response.status_code == status.HTTP_200_OK

        schema: Dict[str, Any] = openapi_response.json()

        # Validate schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Validate our health endpoint is documented
        assert "/health" in schema["paths"]
        assert "get" in schema["paths"]["/health"]

        # Test docs endpoint
        docs_response: Response = self.client.get("/docs")
        assert docs_response.status_code == status.HTTP_200_OK
        assert "swagger" in docs_response.text.lower()

    def test_redoc_documentation(self) -> None:
        """Test ReDoc documentation endpoint."""
        response: Response = self.client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "redoc" in response.text.lower()

    def test_api_with_configuration_integration(self) -> None:
        """Test that API integrates properly with configuration system."""
        # This test ensures the API can work with the config system
        # even though the health endpoint doesn't use config directly

        from config.config import get_config
        config = get_config()

        # Config should be accessible
        assert config is not None
        assert hasattr(config, 'server')
        assert hasattr(config, 'llm')
        assert hasattr(config, 'database')

        # API should still work
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_cors_headers_if_configured(self) -> None:
        """Test CORS headers if they would be configured."""
        response: Response = self.client.get("/health")

        # For now, just test that we get a valid response
        # In the future, if CORS is added, we can test those headers here
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_concurrent_requests(self) -> None:
        """Test that API can handle multiple requests."""
        results: List[int] = []

        def make_request() -> None:
            response: Response = self.client.get("/health")
            results.append(response.status_code)

        # Create multiple threads
        threads: List[threading.Thread] = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        assert all(status_code == status.HTTP_200_OK for status_code in results)

    def test_api_error_handling_integration(self) -> None:
        """Test API error handling for various scenarios."""
        # Test 404 for unknown endpoints
        response: Response = self.client.get("/unknown-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test method not allowed
        response = self.client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test invalid JSON handling (if we had POST endpoints)
        # For now, just ensure our GET endpoint works
        response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK


class TestAPIPerformance:
    """Performance-related integration tests."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)

    def test_health_endpoint_response_time(self) -> None:
        """Test that health endpoint responds quickly."""
        start_time: float = time.time()
        response: Response = self.client.get("/health")
        end_time: float = time.time()

        response_time: float = end_time - start_time

        # Health check should be fast (less than 1 second)
        assert response_time < 1.0
        assert response.status_code == status.HTTP_200_OK

    def test_repeated_requests_performance(self) -> None:
        """Test performance of repeated requests."""
        start_time: float = time.time()

        # Make 100 requests
        for _ in range(100):
            response: Response = self.client.get("/health")
            assert response.status_code == status.HTTP_200_OK

        end_time: float = time.time()
        total_time: float = end_time - start_time

        # 100 requests should complete in reasonable time (less than 10 seconds)
        assert total_time < 10.0

        # Average response time should be reasonable
        avg_response_time: float = total_time / 100
        assert avg_response_time < 0.1  # Less than 100ms average


class TestAPIDeploymentReadiness:
    """Tests to verify API is ready for deployment."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)

    def test_health_endpoint_for_load_balancer(self) -> None:
        """Test health endpoint suitability for load balancer health checks."""
        response: Response = self.client.get("/health")

        # Should return 200 for healthy service
        assert response.status_code == status.HTTP_200_OK

        # Should have consistent response format
        data: Dict[str, Any] = response.json()
        assert data["status"] == "healthy"

        # Should respond quickly
        start: float = time.time()
        response = self.client.get("/health")
        duration: float = time.time() - start
        assert duration < 0.5  # Less than 500ms

    def test_api_metadata_for_monitoring(self) -> None:
        """Test API metadata useful for monitoring."""
        # Test OpenAPI schema has required info
        response: Response = self.client.get("/openapi.json")
        schema: Dict[str, Any] = response.json()

        assert schema["info"]["title"] == "Auto Grade API"
        assert schema["info"]["version"] == "0.1.0"
        assert "description" in schema["info"]

    def test_error_responses_format(self) -> None:
        """Test that error responses follow expected format."""
        # Test 404 response format
        response: Response = self.client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data: Dict[str, Any] = response.json()
        assert "detail" in error_data
        # Test 404 response format
        response = self.client.get("/nonexistent")
        assert response.status_code == 404

        error_data = response.json()
        assert "detail" in error_data