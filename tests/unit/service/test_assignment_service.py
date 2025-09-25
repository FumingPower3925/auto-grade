from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from src.repository.db.models import AssignmentModel, FileModel
from src.service.assignment_service import AssignmentService


class TestAssignmentService:
    """Tests for AssignmentService."""

    @patch("src.service.assignment_service.get_database_repository")
    def test_create_assignment_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful assignment creation."""
        mock_repo = MagicMock()
        mock_repo.create_assignment.return_value = "test_id_123"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        assignment_id = service.create_assignment("Test Assignment", 0.75)

        assert assignment_id == "test_id_123"
        mock_repo.create_assignment.assert_called_once_with("Test Assignment", 0.75)

    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.parametrize(
        "name,error_msg",
        [
            ("", "Assignment name must be between 1 and 255 characters"),
            ("a" * 256, "Assignment name must be between 1 and 255 characters"),
        ],
    )
    def test_create_assignment_invalid_name(self, mock_get_repo: MagicMock, name: str, error_msg: str) -> None:
        """Test assignment creation with invalid name."""
        service = AssignmentService()

        with pytest.raises(ValueError, match=error_msg):
            service.create_assignment(name, 0.75)

    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.parametrize(
        "threshold,error_msg",
        [
            (-0.1, "Confidence threshold must be between 0.0 and 1.0"),
            (1.1, "Confidence threshold must be between 0.0 and 1.0"),
        ],
    )
    def test_create_assignment_invalid_threshold(
        self, mock_get_repo: MagicMock, threshold: float, error_msg: str
    ) -> None:
        """Test assignment creation with invalid threshold."""
        service = AssignmentService()

        with pytest.raises(ValueError, match=error_msg):
            service.create_assignment("Test", threshold)

    @patch("src.service.assignment_service.get_database_repository")
    def test_get_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test getting an assignment."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_assignment("test_id")

        assert result == mock_assignment
        mock_repo.get_assignment.assert_called_once_with("test_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_assignments(self, mock_get_repo: MagicMock) -> None:
        """Test listing assignments."""
        mock_repo = MagicMock()
        mock_assignments = [self._create_mock_assignment("Assignment 1"), self._create_mock_assignment("Assignment 2")]
        mock_repo.list_assignments.return_value = mock_assignments
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_assignments()

        assert result == mock_assignments
        assert len(result) == 2
        mock_repo.list_assignments.assert_called_once()

    @patch("src.service.assignment_service.get_database_repository")
    def test_delete_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test deleting an assignment."""
        mock_repo = MagicMock()
        mock_repo.delete_assignment.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.delete_assignment("test_id")

        assert result is True
        mock_repo.delete_assignment.assert_called_once_with("test_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_upload_rubric_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful rubric upload."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_123"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        file_id = service.upload_rubric("assignment_id", "rubric.pdf", b"content", "application/pdf")

        assert file_id == "file_id_123"
        mock_repo.store_file.assert_called_once_with(
            "assignment_id", "rubric.pdf", b"content", "application/pdf", "rubric"
        )

    @patch("src.service.assignment_service.get_database_repository")
    def test_upload_rubric_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test rubric upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_rubric("test_id", "rubric.pdf", b"content", "application/pdf")

    @patch("src.service.assignment_service.get_database_repository")
    def test_upload_relevant_document_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful relevant document upload."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_456"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        file_id = service.upload_relevant_document(
            "assignment_id",
            "example.docx",
            b"content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        assert file_id == "file_id_456"
        mock_repo.store_file.assert_called_once_with(
            "assignment_id",
            "example.docx",
            b"content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "relevant_document",
        )

    @patch("src.service.assignment_service.get_database_repository")
    def test_upload_relevant_document_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test document upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_relevant_document("test_id", "doc.pdf", b"content", "application/pdf")

    @patch("src.service.assignment_service.get_database_repository")
    def test_get_file(self, mock_get_repo: MagicMock) -> None:
        """Test getting a file."""
        mock_repo = MagicMock()
        mock_file = self._create_mock_file()
        mock_repo.get_file.return_value = mock_file
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_file("file_id")

        assert result == mock_file
        mock_repo.get_file.assert_called_once_with("file_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_rubrics(self, mock_get_repo: MagicMock) -> None:
        """Test listing rubrics."""
        mock_repo = MagicMock()
        mock_files = [self._create_mock_file("rubric1.pdf"), self._create_mock_file("rubric2.pdf")]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_rubrics("assignment_id")

        assert result == mock_files
        assert len(result) == 2
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "rubric")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_relevant_documents(self, mock_get_repo: MagicMock) -> None:
        """Test listing relevant documents."""
        mock_repo = MagicMock()
        mock_files = [self._create_mock_file("example.docx")]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_relevant_documents("assignment_id")

        assert result == mock_files
        assert len(result) == 1
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "relevant_document")

    def _create_mock_assignment(self, name: str = "Test Assignment") -> AssignmentModel:
        """Create a mock AssignmentModel."""
        return AssignmentModel(
            _id=ObjectId(),
            name=name,
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def _create_mock_file(self, filename: str = "test.pdf") -> FileModel:
        """Create a mock FileModel."""
        return FileModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            filename=filename,
            content=b"content",
            content_type="application/pdf",
            file_type="rubric",
            uploaded_at=datetime.now(UTC),
        )
