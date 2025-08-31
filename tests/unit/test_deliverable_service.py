from unittest.mock import patch, MagicMock
import pytest
from typing import List, Tuple
from src.service.deliverable_service import DeliverableService
from src.repository.db.models import DeliverableModel, AssignmentModel
from bson import ObjectId
from datetime import datetime, timezone


class TestDeliverableService:
    """Unit tests for the DeliverableService."""

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_no_api_key(self, mock_get_repo: MagicMock) -> None:
        """Test extracting student name when no API key is available."""
        with patch('os.getenv', return_value=""):
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")
            
            assert name == "Unknown"
            assert text is None

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful student name extraction from PDF using PyPDF2."""
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Name: John Doe\nAssignment 1\nIntroduction..."
            
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")
            
            assert name == "John Doe"
            assert text is not None
            assert "John Doe" in text

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_api_error(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test extraction when API returns an error."""
        with patch('os.getenv', return_value="test_api_key"):
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_post.return_value = mock_response
            
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")
            
            assert name == "Unknown"
            assert text is None

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_exception(self, mock_get_repo: MagicMock) -> None:
        """Test extraction when an exception occurs."""
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_pdf_reader.side_effect = Exception("PDF parsing error")
            
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")
            
            assert name == "Unknown"
            assert text is None

    @patch('src.service.deliverable_service.get_database_repository')
    def test_clean_student_name(self, mock_get_repo: MagicMock) -> None:
        """Test cleaning student names."""
        service = DeliverableService()
        
        assert service.clean_student_name("John Doe") == "John Doe"
        assert service.clean_student_name("Name: Jane Smith") == "Jane Smith"
        assert service.clean_student_name("Student: Bob Johnson") == "Bob Johnson"
        assert service.clean_student_name("Author: Alice Brown") == "Alice Brown"
        assert service.clean_student_name("Submitted by: Charlie Davis") == "Charlie Davis"
        assert service.clean_student_name("By: Emily Wilson") == "Emily Wilson"
        
        assert service.clean_student_name("") == "Unknown"
        assert service.clean_student_name("unknown") == "Unknown"
        assert service.clean_student_name("not found") == "Unknown"
        assert service.clean_student_name("n/a") == "Unknown"
        assert service.clean_student_name("none") == "Unknown"
        assert service.clean_student_name("123456") == "Unknown"
        assert service.clean_student_name("!@#$%^") == "Unknown"
        
        assert service.clean_student_name("John@Doe#2024") == "John Doe 2024"
        assert service.clean_student_name("Mary-Jane O'Neill") == "Mary-Jane O'Neill"
        
        long_name = "A" * 150
        cleaned = service.clean_student_name(long_name)
        assert len(cleaned) == 100

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful deliverable upload."""
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
        mock_repo.store_deliverable.return_value = "deliverable_id_123"
        mock_get_repo.return_value = mock_repo
        
        with patch.object(DeliverableService, 'extract_student_name_from_pdf', return_value=("John Doe", None)):
            service = DeliverableService()
            deliverable_id = service.upload_deliverable(
                "assignment_id",
                "submission.pdf",
                b"pdf content",
                "pdf",
                "application/pdf",
                extract_name=True
            )
        
        assert deliverable_id == "deliverable_id_123"
        mock_repo.store_deliverable.assert_called_once_with(
            assignment_id="assignment_id",
            filename="submission.pdf",
            content=b"pdf content",
            extension="pdf",
            content_type="application/pdf",
            student_name="John Doe",
            extracted_text=None
        )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_no_extraction(self, mock_get_repo: MagicMock) -> None:
        """Test deliverable upload without name extraction."""
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
        mock_repo.store_deliverable.return_value = "deliverable_id_456"
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        deliverable_id = service.upload_deliverable(
            "assignment_id",
            "submission.docx",
            b"docx content",
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extract_name=False
        )
        
        assert deliverable_id == "deliverable_id_456"
        mock_repo.store_deliverable.assert_called_once_with(
            assignment_id="assignment_id",
            filename="submission.docx",
            content=b"docx content",
            extension="docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            student_name="Unknown",
            extracted_text=None
        )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test deliverable upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_deliverable(
                "test_id",
                "submission.pdf",
                b"content",
                "pdf",
                "application/pdf"
            )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful upload of multiple deliverables."""
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
        mock_repo.store_deliverable.side_effect = ["id1", "id2", "id3"]
        mock_get_repo.return_value = mock_repo
        
        files: List[Tuple[str, bytes, str, str]] = [
            ("file1.pdf", b"content1", "pdf", "application/pdf"),
            ("file2.pdf", b"content2", "pdf", "application/pdf"),
            ("file3.pdf", b"content3", "pdf", "application/pdf")
        ]
        
        with patch.object(DeliverableService, 'extract_student_name_from_pdf', return_value=("Student", None)):
            service = DeliverableService()
            deliverable_ids = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=True
            )
        
        assert deliverable_ids == ["id1", "id2", "id3"]
        assert mock_repo.store_deliverable.call_count == 3

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_partial_failure(self, mock_get_repo: MagicMock) -> None:
        """Test upload of multiple deliverables with some failures."""
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
        mock_repo.store_deliverable.side_effect = ["id1", Exception("Error"), "id3"]
        mock_get_repo.return_value = mock_repo
        
        files: List[Tuple[str, bytes, str, str]] = [
            ("file1.pdf", b"content1", "pdf", "application/pdf"),
            ("file2.pdf", b"content2", "pdf", "application/pdf"),
            ("file3.pdf", b"content3", "pdf", "application/pdf")
        ]
        
        with patch.object(DeliverableService, 'extract_student_name_from_pdf', return_value=("Student", None)):
            service = DeliverableService()
            deliverable_ids = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
        
        assert deliverable_ids == ["id1", "id3"]

    @patch('src.service.deliverable_service.get_database_repository')
    def test_update_deliverable_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful deliverable update."""
        mock_repo = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="Original Name",
            mark=None,
            certainty_threshold=None,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_repo.update_deliverable.return_value = True
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.update_deliverable(
            "deliverable_id",
            student_name="Updated Name",
            mark=85.5,
            certainty_threshold=0.95
        )
        
        assert result is True
        mock_repo.update_deliverable.assert_called_once_with(
            "deliverable_id",
            student_name="Updated Name",
            mark=85.5,
            certainty_threshold=0.95
        )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_update_deliverable_invalid_mark(self, mock_get_repo: MagicMock) -> None:
        """Test deliverable update with invalid mark."""
        mock_repo = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="Test",
            mark=None,
            certainty_threshold=None,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with pytest.raises(ValueError, match="Mark must be between 0.0 and 100.0"):
            service.update_deliverable("deliverable_id", mark=150.0)
        
        with pytest.raises(ValueError, match="Mark must be between 0.0 and 100.0"):
            service.update_deliverable("deliverable_id", mark=-10.0)

    @patch('src.service.deliverable_service.get_database_repository')
    def test_update_deliverable_invalid_certainty(self, mock_get_repo: MagicMock) -> None:
        """Test deliverable update with invalid certainty threshold."""
        mock_repo = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="Test",
            mark=None,
            certainty_threshold=None,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with pytest.raises(ValueError, match="Certainty threshold must be between 0.0 and 1.0"):
            service.update_deliverable("deliverable_id", certainty_threshold=1.5)
        
        with pytest.raises(ValueError, match="Certainty threshold must be between 0.0 and 1.0"):
            service.update_deliverable("deliverable_id", certainty_threshold=-0.1)

    @patch('src.service.deliverable_service.get_database_repository')
    def test_update_deliverable_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test updating a non-existent deliverable."""
        mock_repo = MagicMock()
        mock_repo.get_deliverable.return_value = None
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.update_deliverable("deliverable_id", student_name="New Name")
        
        assert result is False
        mock_repo.update_deliverable.assert_not_called()

    @patch('src.service.deliverable_service.get_database_repository')
    def test_update_deliverable_no_changes(self, mock_get_repo: MagicMock) -> None:
        """Test updating deliverable with no changes."""
        mock_repo = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="Test",
            mark=None,
            certainty_threshold=None,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.update_deliverable("deliverable_id")
        
        assert result is False
        mock_repo.update_deliverable.assert_not_called()

    @patch('src.service.deliverable_service.get_database_repository')
    def test_get_deliverable(self, mock_get_repo: MagicMock) -> None:
        """Test getting a deliverable by ID."""
        mock_repo = MagicMock()
        mock_deliverable = DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name="Test Student",
            mark=90.0,
            certainty_threshold=0.85,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.get_deliverable("deliverable_id")
        
        assert result == mock_deliverable
        mock_repo.get_deliverable.assert_called_once_with("deliverable_id")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_list_deliverables(self, mock_get_repo: MagicMock) -> None:
        """Test listing deliverables for an assignment."""
        mock_repo = MagicMock()
        mock_deliverables = [
            DeliverableModel(
                _id=ObjectId(),
                assignment_id=ObjectId(),
                student_name="Student 1",
                mark=80.0,
                certainty_threshold=0.75,
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
        mock_repo.list_deliverables_by_assignment.return_value = mock_deliverables
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.list_deliverables("assignment_id")
        
        assert result == mock_deliverables
        assert len(result) == 2
        mock_repo.list_deliverables_by_assignment.assert_called_once_with("assignment_id")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_delete_deliverable(self, mock_get_repo: MagicMock) -> None:
        """Test deleting a deliverable."""
        mock_repo = MagicMock()
        mock_repo.delete_deliverable.return_value = True
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.delete_deliverable("deliverable_id")
        
        assert result is True
        mock_repo.delete_deliverable.assert_called_once_with("deliverable_id")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_validate_file_format_valid_pdf(self, mock_get_repo: MagicMock) -> None:
        """Test validating a valid PDF file."""
        service = DeliverableService()
        
        is_valid, error = service.validate_file_format("document.pdf", "application/pdf")
        assert is_valid is True
        assert error == ""
        
        is_valid, error = service.validate_file_format("Document.PDF", "application/pdf")
        assert is_valid is True
        assert error == ""

    @patch('src.service.deliverable_service.get_database_repository')
    def test_validate_file_format_invalid_extension(self, mock_get_repo: MagicMock) -> None:
        """Test validating file with invalid extension."""
        service = DeliverableService()
        
        is_valid, error = service.validate_file_format("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert is_valid is False
        assert "File format not supported" in error
        assert ".pdf" in error

    @patch('src.service.deliverable_service.get_database_repository')
    def test_validate_file_format_invalid_mime_type(self, mock_get_repo: MagicMock) -> None:
        """Test validating file with invalid MIME type."""
        service = DeliverableService()
        
        is_valid, error = service.validate_file_format("document.pdf", "text/plain")
        assert is_valid is False
        assert "Content type not supported" in error
        assert "application/pdf" in error

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_no_text(self, mock_get_repo: MagicMock) -> None:
        """Test extracting student name when PDF has no readable text."""
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = []
            mock_pdf_reader.return_value = mock_reader_instance
            
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")
            
            assert name == "Unknown"
            assert text is None
    
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_with_pattern(self, mock_get_repo: MagicMock) -> None:
        """Test extracting student name with various patterns."""
        test_cases = [
            ("Student: Jane Smith\nHomework Assignment", "Jane Smith"),
            ("Submitted by: Bob Johnson\nDate: 2024", "Bob Johnson"),
            ("Alice Brown\nCS101 Assignment", "Alice Brown"),
            ("Author: Charlie Davis\n\nIntroduction", "Charlie Davis"),
        ]
        
        service = DeliverableService()
        
        for pdf_text, expected_name in test_cases:
            with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = pdf_text
                
                mock_reader_instance = MagicMock()
                mock_reader_instance.pages = [mock_page]
                mock_pdf_reader.return_value = mock_reader_instance
                
                name = service.extract_student_name_from_pdf(b"pdf content")
                assert name == expected_name, f"Failed for pattern: {pdf_text}"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_text(self, mock_get_repo: MagicMock) -> None:
        """Test the _extract_name_from_text method."""
        service = DeliverableService()
        
        assert service.extract_name_from_text("") == "Unknown"
        
        text = "Name: John Smith\nAssignment 1"
        assert service.extract_name_from_text(text) == "John Smith"
        
        text = "Jane Doe\nComputer Science Assignment"
        assert service.extract_name_from_text(text) == "Jane Doe"
        
        text = "This is just some random text without a name"
        assert service.extract_name_from_text(text) == "Unknown"
    
    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_with_name_extraction_logging(self, mock_get_repo: MagicMock) -> None:
        """Test that name extraction logs the extracted name."""
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
        mock_repo.store_deliverable.return_value = "deliverable_id_123"
        mock_get_repo.return_value = mock_repo
        
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Name: John Doe\nAssignment"
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            with patch('src.service.deliverable_service.logger') as mock_logger:
                service = DeliverableService()
                service.upload_deliverable(
                    "assignment_id",
                    "submission.pdf",
                    b"pdf content",
                    "pdf",
                    "application/pdf",
                    extract_name=True
                )
                
                mock_logger.info.assert_called_with("Extracted student name: John Doe")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_pdf_with_page_extraction_failure(self, mock_get_repo: MagicMock) -> None:
        """Test PDF extraction when a page fails to extract."""
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_page1 = MagicMock()
            mock_page1.extract_text.side_effect = Exception("Page extraction error")
            
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "Name: Jane Smith"
            
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page1, mock_page2]
            mock_pdf_reader.return_value = mock_reader_instance
            
            with patch('src.service.deliverable_service.logger') as mock_logger:
                service = DeliverableService()
                name = service.extract_student_name_from_pdf(b"pdf content")
                
                assert name == "Jane Smith"
                mock_logger.warning.assert_called()

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_with_failure_logging(self, mock_get_repo: MagicMock) -> None:
        """Test that failed uploads in bulk are logged."""
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
        
        mock_repo.store_deliverable.side_effect = ["id1", Exception("Upload failed"), "id3"]
        mock_get_repo.return_value = mock_repo
        
        files: List[Tuple[str, bytes, str, str]] = [
            ("file1.pdf", b"content1", "pdf", "application/pdf"),
            ("file2.pdf", b"content2", "pdf", "application/pdf"),
            ("file3.pdf", b"content3", "pdf", "application/pdf")
        ]
        
        with patch('src.service.deliverable_service.logger') as mock_logger:
            service = DeliverableService()
            deliverable_ids = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
            
            assert deliverable_ids == ["id1", "id3"]
            mock_logger.error.assert_called()