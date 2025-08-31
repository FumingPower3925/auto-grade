from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock
import io

from src.controller.api.api import app

class TestAPICoverage:
    """Tests for uncovered lines in api.py."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.controller.api.api.AssignmentService')
    def test_upload_rubric_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 273 - general exception during rubric upload."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = RuntimeError("Unexpected error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/rubrics",
            files={"file": ("rubric.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to upload rubric" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 328 - deliverable retrieval fails after upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "deliverable_id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve uploaded deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 335 - general exception during deliverable upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.side_effect = RuntimeError("Unexpected")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to upload deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 451 - deliverable retrieval fails after update."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/deliverable_id",
            json={"student_name": "Test"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve updated deliverable" in response.json()["detail"]