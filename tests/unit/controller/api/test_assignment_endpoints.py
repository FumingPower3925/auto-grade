from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock
import io
import pytest

from src.controller.api.api import app, upload_relevant_document
from src.repository.db.models import AssignmentModel, FileModel
from bson import ObjectId
from datetime import datetime, timezone


class TestAssignmentEndpoints:
    """Tests for assignment-related API endpoints."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.controller.api.api.AssignmentService')
    def test_create_assignment_success(self, mock_service_class: MagicMock) -> None:
        """Test successful assignment creation."""
        mock_service = MagicMock()
        mock_service.create_assignment.return_value = "assignment_id"
        
        mock_assignment = self._create_mock_assignment()
        mock_service.get_assignment.return_value = mock_assignment
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments",
            json={"name": "Test Assignment", "confidence_threshold": 0.75}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(mock_assignment.id)
        assert data["name"] == "Test Assignment"

    @patch('src.controller.api.api.AssignmentService')
    @pytest.mark.parametrize("exception,expected_status,expected_detail", [
        (RuntimeError("DB Error"), 500, "Failed to create assignment"),
        (Exception("Unexpected"), 500, "Failed to create assignment"),
    ])
    def test_create_assignment_exceptions(
        self,
        mock_service_class: MagicMock,
        exception: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test assignment creation with various exceptions."""
        mock_service = MagicMock()
        mock_service.create_assignment.side_effect = exception
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments",
            json={"name": "Test", "confidence_threshold": 0.5}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.AssignmentService')
    def test_create_assignment_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test when assignment retrieval fails after creation."""
        mock_service = MagicMock()
        mock_service.create_assignment.return_value = "assignment_id"
        mock_service.get_assignment.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments",
            json={"name": "Test", "confidence_threshold": 0.5}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to retrieve created assignment"

    @patch('src.controller.api.api.AssignmentService')
    def test_get_assignment(self, mock_service_class: MagicMock) -> None:
        """Test retrieving an assignment."""
        mock_service = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_service.get_assignment.return_value = mock_assignment
        mock_service.list_rubrics.return_value = []
        mock_service.list_relevant_documents.return_value = []
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments/test_id")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Test Assignment"

    @patch('src.controller.api.api.AssignmentService')
    def test_get_assignment_not_found(self, mock_service_class: MagicMock) -> None:
        """Test retrieving non-existent assignment."""
        mock_service = MagicMock()
        mock_service.get_assignment.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments/non_existent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('src.controller.api.api.AssignmentService')
    def test_get_assignment_exception(self, mock_service_class: MagicMock) -> None:
        """Test get assignment with exception."""
        mock_service = MagicMock()
        mock_service.get_assignment.side_effect = Exception("DB error")
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments/test_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to get assignment"

    @patch('src.controller.api.api.AssignmentService')
    def test_list_assignments(self, mock_service_class: MagicMock) -> None:
        """Test listing assignments."""
        mock_service = MagicMock()
        mock_assignments = [
            self._create_mock_assignment("Assignment 1"),
            self._create_mock_assignment("Assignment 2")
        ]
        mock_service.list_assignments.return_value = mock_assignments
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2

    @patch('src.controller.api.api.AssignmentService')
    def test_delete_assignment(self, mock_service_class: MagicMock) -> None:
        """Test deleting an assignment."""
        mock_service = MagicMock()
        mock_service.delete_assignment.return_value = True
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/assignments/test_id")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch('src.controller.api.api.AssignmentService')
    def test_delete_assignment_not_found(self, mock_service_class: MagicMock) -> None:
        """Test deleting non-existent assignment."""
        mock_service = MagicMock()
        mock_service.delete_assignment.return_value = False
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/assignments/non_existent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('src.controller.api.api.AssignmentService')
    def test_delete_assignment_exception(self, mock_service_class: MagicMock) -> None:
        """Test delete assignment with exception."""
        mock_service = MagicMock()
        mock_service.delete_assignment.side_effect = Exception("DB error")
        mock_service_class.return_value = mock_service
        
        response = self.client.delete("/assignments/test_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to delete assignment"

    @patch('src.controller.api.api.AssignmentService')
    @pytest.mark.parametrize("side_effect,expected_status,expected_detail", [
        (Exception("Database error"), 500, "Failed to upload rubric"),
        (RuntimeError("Unexpected error"), 500, "Failed to upload rubric"),
        (ValueError("Assignment not found"), 404, "Assignment not found"),
    ])
    def test_upload_rubric_exceptions(
        self,
        mock_service_class: MagicMock,
        side_effect: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test rubric upload with various exceptions."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = side_effect
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/rubrics",
            files={"file": ("rubric.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.AssignmentService')
    def test_upload_rubric_success(self, mock_service_class: MagicMock) -> None:
        """Test successful rubric upload."""
        mock_service = MagicMock()
        mock_service.upload_rubric.return_value = "file_id"
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/rubrics",
            files={"file": ("rubric.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == "file_id"

    @patch('src.controller.api.api.AssignmentService')
    @pytest.mark.parametrize("side_effect,expected_status,expected_detail", [
        (Exception("Upload error"), 500, "Failed to upload document"),
        (RuntimeError("Unexpected"), 500, "Failed to upload document"),
        (ValueError("Assignment not found"), 404, "Assignment not found"),
    ])
    def test_upload_document_exceptions(
        self,
        mock_service_class: MagicMock,
        side_effect: Exception,
        expected_status: int,
        expected_detail: str
    ) -> None:
        """Test document upload with various exceptions."""
        mock_service = MagicMock()
        mock_service.upload_relevant_document.side_effect = side_effect
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/test_id/documents",
            files={"file": ("doc.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        
        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @patch('src.controller.api.api.AssignmentService')
    def test_download_file(self, mock_service_class: MagicMock) -> None:
        """Test file download."""
        mock_service = MagicMock()
        mock_file = self._create_mock_file()
        mock_service.get_file.return_value = mock_file
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/files/file_id")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"file content"

    @patch('src.controller.api.api.AssignmentService')
    def test_download_file_not_found(self, mock_service_class: MagicMock) -> None:
        """Test downloading non-existent file."""
        mock_service = MagicMock()
        mock_service.get_file.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/files/non_existent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "File not found"

    @patch('src.controller.api.api.AssignmentService')
    def test_download_file_exception(self, mock_service_class: MagicMock) -> None:
        """Test file download with exception."""
        mock_service = MagicMock()
        mock_service.get_file.side_effect = Exception("Download error")
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/files/file_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to download file"

    @patch('src.controller.api.api.AssignmentService')
    def test_list_assignments_exception(self, mock_service_class: MagicMock) -> None:
        """Test listing assignments with exception."""
        mock_service = MagicMock()
        mock_service.list_assignments.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response = self.client.get("/assignments")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to list assignments"

    @patch('src.controller.api.api.AssignmentService')
    def test_create_assignment_value_error(self, mock_service_class: MagicMock) -> None:
        """Test create assignment with ValueError from service."""
        mock_service = MagicMock()
        mock_service.create_assignment.side_effect = ValueError("Database constraint violation")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments",
            json={"name": "Test", "confidence_threshold": 0.5}
        )
        
        assert response.status_code == 422
        assert response.json()["detail"] == "Database constraint violation"

    @patch('src.controller.api.api.AssignmentService')
    @pytest.mark.asyncio
    async def test_upload_document_none_filename_async(self, mock_service_class: MagicMock) -> None:
        """Test upload fallback when filename is None using async test."""
        mock_service = MagicMock()
        mock_service.upload_relevant_document.return_value = "file_id"
        mock_service_class.return_value = mock_service

        mock_file = MagicMock()
        mock_file.filename = None
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"content")

        result = await upload_relevant_document(assignment_id="test_id", file=mock_file)

        assert result.filename == "document"
        assert result.id == "file_id"
        mock_service.upload_relevant_document.assert_called_once_with(
            assignment_id="test_id",
            filename="document",
            content=b"content",
            content_type="application/pdf"
        )

    def _create_mock_assignment(self, name: str = "Test Assignment") -> AssignmentModel:
        """Create a mock AssignmentModel."""
        return AssignmentModel(
            _id=ObjectId(),
            name=name,
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def _create_mock_file(self) -> FileModel:
        """Create a mock FileModel."""
        return FileModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            filename="test.pdf",
            content=b"file content",
            content_type="application/pdf",
            file_type="rubric",
            uploaded_at=datetime.now(timezone.utc)
        )