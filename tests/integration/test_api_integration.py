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
        with TestClient(app) as client:
            response: Response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK
    
    def test_health_endpoint_end_to_end_healthy(self) -> None:
        """Test health endpoint end-to-end, expecting healthy status."""
        response: Response = self.client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        data: Dict[str, Any] = response.json()
        assert data["status"] == "healthy"
        assert len(data["services"]) == 3
        
        for service in data["services"]:
            assert service["status"] == "healthy"
            assert service["details"] is None

        assert response.headers["content-type"] == "application/json"

    def test_openapi_integration(self) -> None:
        """Test OpenAPI schema generation and access."""
        openapi_response: Response = self.client.get("/openapi.json")
        assert openapi_response.status_code == status.HTTP_200_OK
        
        schema: Dict[str, Any] = openapi_response.json()
        
        assert "/health" in schema["paths"]
        
        docs_response: Response = self.client.get("/docs")
        assert docs_response.status_code == status.HTTP_200_OK
        assert "swagger" in docs_response.text.lower()

    def test_multiple_concurrent_requests(self) -> None:
        """Test that API can handle multiple requests."""
        results: List[int] = []
        
        def make_request() -> None:
            response: Response = self.client.get("/health")
            results.append(response.status_code)
        
        threads: List[threading.Thread] = [threading.Thread(target=make_request) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert len(results) == 5
        assert all(status_code == status.HTTP_200_OK for status_code in results)

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
        
        assert response_time < 1.0
        assert response.status_code == status.HTTP_200_OK
