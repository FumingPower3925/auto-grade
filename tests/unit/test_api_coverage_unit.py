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

    @patch('src.controller.api.api.AssignmentService')
    def test_line_273_rubric_upload_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 273 - exception in rubric upload."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/rubrics",
            files={"file": ("rubric.pdf", io.BytesIO(b"pdf"), "application/pdf")}
        )
        
        assert response.status_code == 500
        assert "Failed to upload rubric" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_328_deliverable_retrieval_none(self, mock_service_class: MagicMock) -> None:
        """Test line 328 - deliverable retrieval returns None."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "del_id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"pdf"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == 500
        assert "Failed to retrieve uploaded deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_372_bulk_upload_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 372 - exception in bulk upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = Exception("Bulk error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables/bulk",
            files=[("files", ("test.pdf", io.BytesIO(b"pdf"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == 500
        assert "Failed to upload deliverables" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_451_update_retrieval_none(self, mock_service_class: MagicMock) -> None:
        """Test line 451 - update retrieval returns None."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/test_id",
            json={"student_name": "Test Name"}
        )
        
        assert response.status_code == 500
        assert "Failed to retrieve updated deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.AssignmentService')
    def test_line_273_rubric_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 273."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = Exception("Generic error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/rubrics",
            files={"file": ("file.pdf", io.BytesIO(b"x"), "application/pdf")}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload rubric"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_328_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 328."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables",
            files={"file": ("x.pdf", io.BytesIO(b"x"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve uploaded deliverable"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_372_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 372."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = Exception("Error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables/bulk",
            files=[("files", ("x.pdf", io.BytesIO(b"x"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload deliverables"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_451_update_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 451."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/test_id",
            json={"student_name": "X"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve updated deliverable"

    @patch('src.controller.api.api.AssignmentService')
    def test_line_273_document_no_filename(self, mock_service_class: MagicMock) -> None:
        """Test line 273 - general exception during document upload."""
        mock_service = MagicMock()
        mock_service.upload_relevant_document.side_effect = Exception("Unexpected error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/documents",
            files={"file": ("document.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        
        assert response.status_code == 500
        assert "Failed to upload document" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_328_bulk_upload_no_filename(self, mock_service_class: MagicMock) -> None:
        """Test line 328 - deliverable retrieval fails after upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "deliverable_id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == 500
        assert "Failed to retrieve uploaded deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_372_bulk_upload_value_error(self, mock_service_class: MagicMock) -> None:
        """Test line 372 - bulk upload with ValueError."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = ValueError("Assignment not found")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables/bulk",
            files=[("files", ("test.pdf", io.BytesIO(b"content"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == 404
        assert "Assignment not found" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_line_451_update_deliverable_value_error(self, mock_service_class: MagicMock) -> None:
        """Test line 451 - deliverable retrieval fails after update."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/test_id",
            json={"student_name": "Test Name"}
        )
        
        assert response.status_code == 500
        assert "Failed to retrieve updated deliverable" in response.json()["detail"]