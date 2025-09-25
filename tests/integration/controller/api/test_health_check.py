import threading
import time

from fastapi import status
from fastapi.testclient import TestClient

from config.config import ConfigManager
from src.controller.api.api import app


class TestHealthCheckIntegration:
    def setup_method(self) -> None:
        ConfigManager.reset()
        self.client = TestClient(app)

    def test_health_endpoint_complete_flow(self) -> None:
        response = self.client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data == {"status": "healthy", "message": "Auto Grade API is running and connected to the database"}
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_performance(self) -> None:
        start_time = time.time()
        response = self.client.get("/health")
        duration = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert duration < 1.0

    def test_health_endpoint_concurrent_requests(self) -> None:
        results: list[int] = []

        def make_request() -> None:
            response = self.client.get("/health")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert all(status_code == status.HTTP_200_OK for status_code in results)

    def test_health_endpoint_load_balancer_compatibility(self) -> None:
        for _ in range(100):
            response = self.client.get("/health")
            assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/health")
        assert response.json()["status"] == "healthy"

    def test_openapi_documentation_availability(self) -> None:
        response = self.client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        schema = response.json()
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "Auto Grade API"
        assert schema["info"]["version"] == "0.1.0"
        assert "/health" in schema["paths"]

        response = self.client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "swagger" in response.text.lower()

        response = self.client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "redoc" in response.text.lower()

    def test_api_error_handling(self) -> None:
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in response.json()

        response = self.client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = self.client.post("/assignments", content="not json", headers={"content-type": "text/plain"})
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_CONTENT, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE]
