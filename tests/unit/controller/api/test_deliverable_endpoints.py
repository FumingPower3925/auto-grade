from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock
import io
import pytest

from src.controller.api.api import app
from src.repository.db.models import DeliverableModel
from bson import ObjectId
from datetime import datetime, timezone


class TestDeliverableEndpoints:
    """Tests for deliverable-related API endpoints."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "deliverable_id"
        
        mock_deliverable = self._create_mock_deliverable()
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(b"content"), "application/pdf")},
            data={"extract_name": "true"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "deliverable_id"
        assert data["message"] == "Deliverable uploaded successfully"

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_invalid_format(self, mock_service_class: MagicMock) -> None:
        """Test deliverable upload with invalid format."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (False, "Invalid format")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("doc.docx", io.BytesIO(b"content"), "application/msword")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "Invalid format" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    @pytest.mark.parametrize("exception,expected_status,expected_detail", [
        (ValueError("Assignment not found"), 404, "Assignment not found"),
        (RuntimeError("Upload failed"), 500, "Failed to upload deliverable"),
        (Exception("Unexpected"), 500, "Failed to upload deliverable"),
    ])
    def test_upload_deliverable_exceptions(
        self,
        mock_service_class: MagicMock,
        exception: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test deliverable upload with various exceptions."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.side_effect = exception
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.DeliverableService')
    def test_upload_deliverable_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test when deliverable retrieval fails after upload (line 328)."""
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
        assert response.json()["detail"] == "Failed to retrieve uploaded deliverable"

    @patch('src.controller.api.api.DeliverableService')
    def test_bulk_upload_success(self, mock_service_class: MagicMock) -> None:
        """Test successful bulk deliverable upload."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.return_value = ["id1", "id2"]
        
        mock_deliverables = [
            self._create_mock_deliverable("Student 1"),
            self._create_mock_deliverable("Student 2")
        ]
        mock_service.get_deliverable.side_effect = mock_deliverables
        mock_service_class.return_value = mock_service
        
        files = [
            ("files", ("file1.pdf", io.BytesIO(b"content1"), "application/pdf")),
            ("files", ("file2.pdf", io.BytesIO(b"content2"), "application/pdf"))
        ]
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables/bulk",
            files=files,
            data={"extract_names": "true"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_uploaded"] == 2

    @patch('src.controller.api.api.DeliverableService')
    @pytest.mark.parametrize("exception,expected_status,expected_detail", [
        (ValueError("Assignment not found"), 404, "Assignment not found"),
        (RuntimeError("Bulk error"), 500, "Failed to upload deliverables"),
        (Exception("Error"), 500, "Failed to upload deliverables"),
    ])
    def test_bulk_upload_exceptions(
        self,
        mock_service_class: MagicMock,
        exception: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test bulk upload with various exceptions (line 372)."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = exception
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/deliverables/bulk",
            files=[("files", ("test.pdf", io.BytesIO(b"content"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.DeliverableService')
    def test_bulk_upload_no_valid_files(self, mock_service_class: MagicMock) -> None:
        """Test bulk upload with no valid files."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (False, "Invalid format")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/assignment_id/deliverables/bulk",
            files=[("files", ("doc.docx", io.BytesIO(b"content"), "application/msword"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "No valid files provided" in response.json()["detail"]

    @patch('src.controller.api.api.DeliverableService')
    def test_list_deliverables(self, mock_service_class: MagicMock) -> None:
        """Test listing deliverables."""
        mock_service = MagicMock()
        mock_deliverables = [
            self._create_mock_deliverable("Student 1", mark=8.5),
            self._create_mock_deliverable("Student 2", mark=None)
        ]
        mock_service.list_deliverables.return_value = mock_deliverables
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments/assignment_id/deliverables")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["deliverables"][0]["mark_status"] == "Marked"
        assert data["deliverables"][1]["mark_status"] == "Unmarked"

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable update."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_deliverable = self._create_mock_deliverable("Updated Name", mark=9.0)
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/deliverable_id",
            json={"student_name": "Updated Name", "mark": 9.0}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["student_name"] == "Updated Name"
        assert data["mark"] == 9.0

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test updating non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = False
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/non_existent",
            json={"student_name": "Name"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test when deliverable retrieval fails after update (line 451)."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/deliverable_id",
            json={"student_name": "Test"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to retrieve updated deliverable"

    @patch('src.controller.api.api.DeliverableService')
    @pytest.mark.parametrize("exception,expected_status,expected_detail", [
        (ValueError("Custom validation"), 422, "Custom validation"),
        (Exception("DB error"), 500, "Failed to update deliverable"),
    ])
    def test_update_deliverable_exceptions(
        self,
        mock_service_class: MagicMock,
        exception: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test update deliverable with exceptions."""
        mock_service = MagicMock()
        mock_service.update_deliverable.side_effect = exception
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/test_id",
            json={"student_name": "Test"}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.DeliverableService')
    def test_update_deliverable_invalid_mark(self, mock_service_class: MagicMock) -> None:
        """Test updating deliverable with invalid mark."""
        response = self.client.patch(
            "/deliverables/deliverable_id",
            json={"mark": 15.0}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "less than or equal to 10" in str(response.json()["detail"])

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable deletion."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.return_value = True
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/deliverables/deliverable_id")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Deliverable deleted successfully"

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test deleting non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.return_value = False
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/deliverables/non_existent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_success(self, mock_service_class: MagicMock) -> None:
        """Test successful deliverable download."""
        mock_service = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_service.get_deliverable.return_value = mock_deliverable
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/deliverables/deliverable_id/download")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"PDF content"
        assert response.headers["content-type"] == "application/pdf"

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_not_found(self, mock_service_class: MagicMock) -> None:
        """Test downloading non-existent deliverable."""
        mock_service = MagicMock()
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/deliverables/non_existent/download")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('src.controller.api.api.DeliverableService')
    def test_list_deliverables_exception(self, mock_service_class: MagicMock) -> None:
        """Test listing deliverables with exception (covers lines 405-406)."""
        mock_service = MagicMock()
        mock_service.list_deliverables.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments/assignment_id/deliverables")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to list deliverables"

    @patch('src.controller.api.api.DeliverableService')
    def test_delete_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test delete deliverable with exception (covers lines 468-469)."""
        mock_service = MagicMock()
        mock_service.delete_deliverable.side_effect = Exception("DB error")
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/deliverables/test_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to delete deliverable"

    @patch('src.controller.api.api.DeliverableService')
    def test_download_deliverable_exception(self, mock_service_class: MagicMock) -> None:
        """Test download deliverable with exception (covers lines 491-492)."""
        mock_service = MagicMock()
        mock_service.get_deliverable.side_effect = Exception("DB error")
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/deliverables/test_id/download")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to download deliverable"

    def _create_mock_deliverable(
        self,
        student_name: str = "John Doe",
        mark: float | None = None,
        certainty: float | None = None
    ) -> DeliverableModel:
        """Create a mock DeliverableModel."""
        return DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name=student_name,
            mark=mark,
            certainty_threshold=certainty,
            filename="submission.pdf",
            content=b"PDF content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )