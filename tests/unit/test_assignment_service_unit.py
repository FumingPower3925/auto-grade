from unittest.mock import patch, MagicMock
import pytest
from src.service.assignment_service import AssignmentService
from src.repository.db.models import AssignmentModel, FileModel
from bson import ObjectId
from datetime import datetime, timezone


class TestAssignmentService:
    """Unit tests for the AssignmentService."""

    @patch('src.service.assignment_service.get_database_repository')
    def test_create_assignment_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful assignment creation."""
        mock_repo = MagicMock()
        mock_repo.create_assignment.return_value = "test_id_123"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        assignment_id = service.create_assignment("Test Assignment", 0.75)

        assert assignment_id == "test_id_123"
        mock_repo.create_assignment.assert_called_once_with("Test Assignment", 0.75)

    @patch('src.service.assignment_service.get_database_repository')
    def test_create_assignment_invalid_name_empty(self, mock_get_repo: MagicMock) -> None:
        """Test assignment creation with empty name."""
        service = AssignmentService()
        
        with pytest.raises(ValueError, match="Assignment name must be between 1 and 255 characters"):
            service.create_assignment("", 0.75)

    @patch('src.service.assignment_service.get_database_repository')
    def test_create_assignment_invalid_name_too_long(self, mock_get_repo: MagicMock) -> None:
        """Test assignment creation with name too long."""
        service = AssignmentService()
        long_name = "a" * 256
        
        with pytest.raises(ValueError, match="Assignment name must be between 1 and 255 characters"):
            service.create_assignment(long_name, 0.75)

    @patch('src.service.assignment_service.get_database_repository')
    def test_create_assignment_invalid_threshold_negative(self, mock_get_repo: MagicMock) -> None:
        """Test assignment creation with negative threshold."""
        service = AssignmentService()
        
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            service.create_assignment("Test", -0.1)

    @patch('src.service.assignment_service.get_database_repository')
    def test_create_assignment_invalid_threshold_too_high(self, mock_get_repo: MagicMock) -> None:
        """Test assignment creation with threshold > 1."""
        service = AssignmentService()
        
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            service.create_assignment("Test", 1.1)

    @patch('src.service.assignment_service.get_database_repository')
    def test_get_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test getting an assignment by ID."""
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test Assignment",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_assignment("test_id")

        assert result == mock_assignment
        mock_repo.get_assignment.assert_called_once_with("test_id")

    @patch('src.service.assignment_service.get_database_repository')
    def test_list_assignments(self, mock_get_repo: MagicMock) -> None:
        """Test listing all assignments."""
        mock_repo = MagicMock()
        mock_assignments = [
            AssignmentModel(
                _id=ObjectId(),
                name="Assignment 1",
                confidence_threshold=0.75,
                deliverables=[],
                evaluation_rubrics=[],
                relevant_documents=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            AssignmentModel(
                _id=ObjectId(),
                name="Assignment 2",
                confidence_threshold=0.80,
                deliverables=[],
                evaluation_rubrics=[],
                relevant_documents=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        mock_repo.list_assignments.return_value = mock_assignments
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_assignments()

        assert result == mock_assignments
        assert len(result) == 2
        mock_repo.list_assignments.assert_called_once()

    @patch('src.service.assignment_service.get_database_repository')
    def test_delete_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test deleting an assignment."""
        mock_repo = MagicMock()
        mock_repo.delete_assignment.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.delete_assignment("test_id")

        assert result is True
        mock_repo.delete_assignment.assert_called_once_with("test_id")

    @patch('src.service.assignment_service.get_database_repository')
    def test_upload_rubric_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful rubric upload."""
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test Assignment",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_123"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        file_id = service.upload_rubric(
            "assignment_id",
            "rubric.pdf",
            b"file content",
            "application/pdf"
        )

        assert file_id == "file_id_123"
        mock_repo.store_file.assert_called_once_with(
            "assignment_id",
            "rubric.pdf",
            b"file content",
            "application/pdf",
            "rubric"
        )

    @patch('src.service.assignment_service.get_database_repository')
    def test_upload_rubric_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test rubric upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        
        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_rubric("test_id", "rubric.pdf", b"content", "application/pdf")

    @patch('src.service.assignment_service.get_database_repository')
    def test_upload_relevant_document_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful relevant document upload."""
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test Assignment",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_456"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        file_id = service.upload_relevant_document(
            "assignment_id",
            "example.docx",
            b"document content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        assert file_id == "file_id_456"
        mock_repo.store_file.assert_called_once_with(
            "assignment_id",
            "example.docx",
            b"document content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "relevant_document"
        )

    @patch('src.service.assignment_service.get_database_repository')
    def test_get_file(self, mock_get_repo: MagicMock) -> None:
        """Test getting a file by ID."""
        mock_repo = MagicMock()
        mock_file = FileModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            file_type="rubric",
            uploaded_at=datetime.now(timezone.utc)
        )
        mock_repo.get_file.return_value = mock_file
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_file("file_id")

        assert result == mock_file
        mock_repo.get_file.assert_called_once_with("file_id")

    @patch('src.service.assignment_service.get_database_repository')
    def test_list_rubrics(self, mock_get_repo: MagicMock) -> None:
        """Test listing rubrics for an assignment."""
        mock_repo = MagicMock()
        mock_files = [
            FileModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                filename="rubric1.pdf",
                content=b"content1",
                content_type="application/pdf",
                file_type="rubric",
                uploaded_at=datetime.now(timezone.utc)
            ),
            FileModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                filename="rubric2.pdf",
                content=b"content2",
                content_type="application/pdf",
                file_type="rubric",
                uploaded_at=datetime.now(timezone.utc)
            )
        ]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_rubrics("assignment_id")

        assert result == mock_files
        assert len(result) == 2
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "rubric")

    @patch('src.service.assignment_service.get_database_repository')
    def test_list_relevant_documents(self, mock_get_repo: MagicMock) -> None:
        """Test listing relevant documents for an assignment."""
        mock_repo = MagicMock()
        mock_files = [
            FileModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                filename="example.docx",
                content=b"content",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_type="relevant_document",
                uploaded_at=datetime.now(timezone.utc)
            )
        ]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_relevant_documents("assignment_id")

        assert result == mock_files
        assert len(result) == 1
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "relevant_document")

    @patch('src.service.assignment_service.get_database_repository')
    def test_upload_relevant_document_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test relevant document upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        
        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_relevant_document("test_id", "doc.pdf", b"content", "application/pdf")