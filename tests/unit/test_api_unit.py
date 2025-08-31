from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any
from httpx import Response
from unittest.mock import patch, MagicMock

from src.controller.api.api import app
from src.controller.api.models import HealthResponse


class TestHealthEndpoint:
    """Unit tests for the health endpoint."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_returns_correct_status_code_when_healthy(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns 200 status code when healthy."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    @patch('src.service.health_service.HealthService.check_health', return_value=False)
    def test_health_endpoint_returns_correct_status_code_when_unhealthy(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns 200 status code when unhealthy."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_returns_correct_response_model(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns correct response structure."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()

        # Validate response structure
        assert "status" in data
        assert "message" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_returns_expected_values_when_healthy(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns expected status and message when healthy."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()

        assert data["status"] == "healthy"
        assert data["message"] == "Auto Grade API is running and connected to the database"

    @patch('src.service.health_service.HealthService.check_health', return_value=False)
    def test_health_endpoint_returns_expected_values_when_unhealthy(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns expected status and message when unhealthy."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()

        assert data["status"] == "unhealthy"
        assert data["message"] == "Auto Grade API is running but could not connect to the database"

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_response_validates_against_model(self, mock_check_health: Any) -> None:
        """Test that response can be validated against HealthResponse model."""
        response: Response = self.client.get("/health")
        data: Dict[str, Any] = response.json()

        # This should not raise a validation error
        health_response = HealthResponse(**data)
        assert health_response.status == "healthy"
        assert health_response.message == "Auto Grade API is running and connected to the database"

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_with_head_method(self, mock_check_health: Any) -> None:
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

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_content_type(self, mock_check_health: Any) -> None:
        """Test that health endpoint returns correct content type."""
        response: Response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

    @patch('src.service.health_service.HealthService.check_health', return_value=True)
    def test_health_endpoint_response_headers(self, mock_check_health: Any) -> None:
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

    @patch('src.service.assignment_service.AssignmentService.create_assignment', side_effect=Exception("Database error"))
    def test_create_assignment_exception(self, mock_create_assignment: MagicMock) -> None:
        """Test exception handling for create_assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment",
            "confidence_threshold": 0.85
        }
        response: Response = self.client.post("/assignments", json=assignment_data)
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to create assignment"

    @patch('src.service.assignment_service.AssignmentService.get_assignment', side_effect=Exception("Database error"))
    def test_get_assignment_exception(self, mock_get_assignment: MagicMock) -> None:
        """Test exception handling for get_assignment."""
        response: Response = self.client.get("/assignments/some_id")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to get assignment"

    @patch('src.service.assignment_service.AssignmentService.list_assignments', side_effect=Exception("Database error"))
    def test_list_assignments_exception(self, mock_list_assignments: MagicMock) -> None:
        """Test exception handling for list_assignments."""
        response: Response = self.client.get("/assignments")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to list assignments"

    @patch('src.service.assignment_service.AssignmentService.delete_assignment', side_effect=Exception("Database error"))
    def test_delete_assignment_exception(self, mock_delete_assignment: MagicMock) -> None:
        """Test exception handling for delete_assignment."""
        response: Response = self.client.delete("/assignments/some_id")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to delete assignment"

    @patch('src.service.assignment_service.AssignmentService.upload_rubric', side_effect=Exception("Upload error"))
    def test_upload_rubric_exception(self, mock_upload_rubric: MagicMock) -> None:
        """Test exception handling for upload_rubric."""
        response: Response = self.client.post("/assignments/some_id/rubrics", files={"file": ("test.txt", b"content", "text/plain")})
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload rubric"

    @patch('src.service.assignment_service.AssignmentService.upload_relevant_document', side_effect=Exception("Upload error"))
    def test_upload_relevant_document_exception(self, mock_upload_relevant_document: MagicMock) -> None:
        """Test exception handling for upload_relevant_document."""
        response: Response = self.client.post("/assignments/some_id/documents", files={"file": ("test.txt", b"content", "text/plain")})
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload document"

    @patch('src.service.assignment_service.AssignmentService.get_file', side_effect=Exception("Download error"))
    def test_download_file_exception(self, mock_get_file: MagicMock) -> None:
        """Test exception handling for download_file."""
        response: Response = self.client.get("/files/some_id")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to download file"

    @patch('src.controller.api.api.AssignmentService.get_assignment', return_value=None)
    def test_create_assignment_retrieval_failure(self, mock_get_assignment: MagicMock) -> None:
        """Test the case where the assignment is not found after creation."""
        with patch('src.controller.api.api.AssignmentService.create_assignment', return_value="new_id"):
            response = self.client.post("/assignments", json={"name": "test", "confidence_threshold": 0.5})
            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to retrieve created assignment"

    @patch('src.controller.api.api.AssignmentService.get_file', return_value=None)
    def test_download_file_not_found_exception(self, mock_get_file: MagicMock) -> None:
        """Test the case where the file is not found for download."""
        response = self.client.get("/files/non_existent_id")
        assert response.status_code == 404
        assert response.json()["detail"] == "File not found"

    @patch('src.service.assignment_service.AssignmentService.upload_relevant_document')
    def test_upload_document_no_filename(self, mock_upload_document: MagicMock) -> None:
        """Test uploading a document with no filename."""
        mock_upload_document.return_value = "file_id_123"
        
        file_content = b"some content"
        response = self.client.post(
            "/assignments/some_id/documents",
            files={"file": (None, file_content, "application/octet-stream")}
        )
        assert response.status_code == 422

    @patch('src.service.assignment_service.AssignmentService.upload_relevant_document', side_effect=ValueError("Assignment not found"))
    def test_upload_document_value_error(self, mock_upload_document: MagicMock) -> None:
        """Test ValueError handling for upload_relevant_document."""
        file_content = b"some content"
        response = self.client.post(
            "/assignments/some_id/documents",
            files={"file": ("test.txt", file_content, "text/plain")}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Assignment not found"