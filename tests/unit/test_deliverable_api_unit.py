from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any
from httpx import Response
from unittest.mock import patch, MagicMock
import io

from src.controller.api.api import app
from src.repository.db.models import DeliverableModel
from bson import ObjectId
from datetime import datetime, timezone


class TestDeliverableEndpoints:
    """Unit tests for deliverable API endpoints."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client: TestClient = TestClient(app)

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_single_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful upload of a single deliverable."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "deliverable_id_123"
        
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="John Doe",
            mark=None,
            certainty_threshold=None,
            filename="submission.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        file_content = b"PDF content"
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"extract_name": "true"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["id"] == "deliverable_id_123"
        assert data["filename"] == "submission.pdf"
        assert data["student_name"] == "John Doe"
        assert "uploaded_at" in data
        assert data["message"] == "Deliverable uploaded successfully"

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_no_filename(self, mock_service_class: MagicMock) -> None:
        """Test upload with missing filename."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        file_content = b"PDF content"
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": (None, io.BytesIO(file_content), "application/pdf")},
            data={"extract_name": "true"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert any("file" in str(error) for error in response.json()["detail"])

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_invalid_format(self, mock_service_class: MagicMock) -> None:
        """Test upload with invalid file format."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (False, "Invalid format")
        mock_service_class.return_value = mock_service
        
        file_content = b"DOCX content"
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("submission.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"extract_name": "true"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid format" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_assignment_not_found(self, mock_service_class: MagicMock) -> None:
        """Test upload when assignment doesn't exist."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.side_effect = ValueError("Assignment not found")
        mock_service_class.return_value = mock_service
        
        file_content = b"PDF content"
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Assignment not found" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_multiple_deliverables_success(self, mock_service_class: MagicMock) -> None:
        """Test successful upload of multiple deliverables."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.return_value = ["id1", "id2"]
        
        mock_deliverables = [
            DeliverableModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                student_name="Student 1",
                mark=None,
                certainty_threshold=None,
                filename="submission1.pdf",
                content=b"content1",
                extension="pdf",
                content_type="application/pdf",
                uploaded_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            DeliverableModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                student_name="Student 2",
                mark=None,
                certainty_threshold=None,
                filename="submission2.pdf",
                content=b"content2",
                extension="pdf",
                content_type="application/pdf",
                uploaded_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        mock_service.get_deliverable.side_effect = mock_deliverables
        mock_service_class.return_value = mock_service
        
        files = [
            ("files", ("submission1.pdf", io.BytesIO(b"content1"), "application/pdf")),
            ("files", ("submission2.pdf", io.BytesIO(b"content2"), "application/pdf"))
        ]
        
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables/bulk",
            files=files,
            data={"extract_names": "true"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["total_uploaded"] == 2
        assert len(data["deliverables"]) == 2
        assert data["deliverables"][0]["student_name"] == "Student 1"
        assert data["deliverables"][1]["student_name"] == "Student 2"
        assert "Successfully uploaded 2 deliverable(s)" in data["message"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_multiple_deliverables_no_valid_files(self, mock_service_class: MagicMock) -> None:
        """Test bulk upload with no valid files."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (False, "Invalid format")
        mock_service_class.return_value = mock_service
        
        files = [
            ("files", ("document.docx", io.BytesIO(b"content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
        ]
        
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables/bulk",
            files=files,
            data={"extract_names": "true"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "No valid files provided" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_list_deliverables_success(self, mock_service_class: MagicMock) -> None:
        """Test listing deliverables for an assignment."""
        mock_service = MagicMock()
        mock_deliverables = [
            DeliverableModel(
                _id=ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
                assignment_id=ObjectId("50c72b2f9b1d8e2a1c9d4b7f"),
                student_name="John Doe",
                mark=85.5,
                certainty_threshold=0.95,
                filename="submission1.pdf",
                content=b"content1",
                extension="pdf",
                content_type="application/pdf",
                uploaded_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            DeliverableModel(
                _id=ObjectId("60c72b2f9b1d8e2a1c9d4b80"),
                assignment_id=ObjectId("50c72b2f9b1d8e2a1c9d4b7f"),
                student_name="Jane Smith",
                mark=None,
                certainty_threshold=None,
                filename="submission2.pdf",
                content=b"content2",
                extension="pdf",
                content_type="application/pdf",
                uploaded_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        mock_service.list_deliverables.return_value = mock_deliverables
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.get("/assignments/assignment_id/deliverables")
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["total"] == 2
        assert len(data["deliverables"]) == 2
        
        assert data["deliverables"][0]["student_name"] == "John Doe"
        assert data["deliverables"][0]["mark"] == 85.5
        assert data["deliverables"][0]["mark_status"] == "Marked"
        assert data["deliverables"][0]["certainty_threshold"] == 0.95
        
        assert data["deliverables"][1]["student_name"] == "Jane Smith"
        assert data["deliverables"][1]["mark"] is None
        assert data["deliverables"][1]["mark_status"] == "Unmarked"
        assert data["deliverables"][1]["certainty_threshold"] is None

    @patch('src.controller.api.api.DeliverableService')
    def test_list_deliverables_exception(self, mock_service_class: MagicMock) -> None:
        """Test listing deliverables with exception."""
        mock_service = MagicMock()
        mock_service.list_deliverables.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.get("/assignments/assignment_id/deliverables")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list deliverables" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable update."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        
        mock_deliverable = DeliverableModel(
            _id=ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
            assignment_id=ObjectId("50c72b2f9b1d8e2a1c9d4b7f"),
            student_name="Updated Name",
            mark=90.0,
            certainty_threshold=0.85,
            filename="submission.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        update_data: Dict[str, Any] = {
            "student_name": "Updated Name",
            "mark": 90.0,
            "certainty_threshold": 0.85
        }
        
        response: Response = self.client.patch("/deliverables/deliverable_id", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["student_name"] == "Updated Name"
        assert data["mark"] == 90.0
        assert data["mark_status"] == "Marked"
        assert data["certainty_threshold"] == 0.85

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test updating non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = False
        mock_service_class.return_value = mock_service
        
        update_data = {"student_name": "New Name"}
        
        response: Response = self.client.patch("/deliverables/deliverable_id", json=update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Deliverable not found" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_invalid_mark(self, mock_service_class: MagicMock) -> None:
        """Test updating deliverable with invalid mark."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        update_data = {"mark": 150.0}
        
        response: Response = self.client.patch("/deliverables/deliverable_id", json=update_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("less than or equal to 100" in str(error.get("msg", "")) for error in errors)

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable deletion."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.return_value = True
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.delete("/deliverables/deliverable_id")
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        assert data["message"] == "Deliverable deleted successfully"

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test deleting non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.return_value = False
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.delete("/deliverables/deliverable_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Deliverable not found" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable download."""
        mock_service = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="John Doe",
            mark=None,
            certainty_threshold=None,
            filename="submission.pdf",
            content=b"PDF content here",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.get("/deliverables/deliverable_id/download")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"PDF content here"
        assert response.headers["content-type"] == "application/pdf"
        assert "inline; filename=submission.pdf" in response.headers["content-disposition"]

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test downloading non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.get("/deliverables/deliverable_id/download")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Deliverable not found" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test exception handling for upload_deliverable."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        file_content = b"PDF content"
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(file_content), "application/pdf")},
            data={"extract_name": "true"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to upload deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_multiple_deliverables_exception(self, mock_service_class: MagicMock) -> None:
        """Test exception handling for bulk upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        files = [
            ("files", ("submission.pdf", io.BytesIO(b"content"), "application/pdf"))
        ]
        
        response: Response = self.client.post(
            "/assignments/assignment_id/deliverables/bulk",
            files=files,
            data={"extract_names": "true"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to upload deliverables" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test exception handling for update_deliverable."""
        mock_service = MagicMock()
        mock_service.update_deliverable.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        update_data = {"student_name": "New Name"}
        
        response: Response = self.client.patch("/deliverables/deliverable_id", json=update_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test exception handling for delete_deliverable."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.delete("/deliverables/deliverable_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test exception handling for download_deliverable."""
        mock_service = MagicMock()
        mock_service.get_deliverable.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response: Response = self.client.get("/deliverables/deliverable_id/download")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to download deliverable" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_bulk_upload_skip_no_filename_line_328(self, mock_service_class: MagicMock) -> None:
        """Test line 328 - bulk upload skips files without filename."""
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables/bulk",
            files=[("files", (None, io.BytesIO(b"content"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == 422

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_value_error_line_451(self, mock_service_class: MagicMock) -> None:
        """Test line 451 - update deliverable raises ValueError."""
        mock_service = MagicMock()
        mock_service.update_deliverable.side_effect = ValueError("Custom validation error")
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/test_id",
            json={"student_name": "Test Name"}
        )
        
        assert response.status_code == 422
        assert "Custom validation error" in response.json()["detail"]