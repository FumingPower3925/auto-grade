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
        with patch('src.service.deliverable_service.os.getenv', return_value=""):
            with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = ""
                mock_reader_instance = MagicMock()
                mock_reader_instance.pages = [mock_page]
                mock_pdf_reader.return_value = mock_reader_instance
                
                service = DeliverableService()
                name, text = service.extract_student_name_from_pdf(b"pdf content") # type: ignore

                assert name == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful student name extraction from PDF using PyPDF2."""
        with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Name: John Doe" 
            
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
        with patch('src.service.deliverable_service.os.getenv', return_value="test_api_key"):
            with patch('src.service.deliverable_service.PdfReader') as mock_pdf_reader:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Some random text without a clear name"
                mock_reader_instance = MagicMock()
                mock_reader_instance.pages = [mock_page]
                mock_pdf_reader.return_value = mock_reader_instance
                
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_post.return_value = mock_response
                
                service = DeliverableService()
                service.openai_api_key = "test_api_key"
                name, text = service.extract_student_name_from_pdf(b"pdf content") # type: ignore

                assert name == "Unknown"

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
            mark=8.55,
            certainty_threshold=0.95
        )
        
        assert result is True
        mock_repo.update_deliverable.assert_called_once_with(
            "deliverable_id",
            student_name="Updated Name",
            mark=8.55,
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
        
        with pytest.raises(ValueError, match="Mark must be between 0.0 and 10.0"):
            service.update_deliverable("deliverable_id", mark=15.0)
        
        with pytest.raises(ValueError, match="Mark must be between 0.0 and 10.0"):
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
            mark=9.0,
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
                mark=8.0,
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
                
                name, text = service.extract_student_name_from_pdf(b"pdf content") # type: ignore
                assert name == expected_name, f"Failed for pattern: {pdf_text}"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_text(self, mock_get_repo: MagicMock) -> None:
        """Test the extract_name_from_text method."""
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
                name, text = service.extract_student_name_from_pdf(b"pdf content") # type: ignore
                
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

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_success(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test successful name extraction with OpenAI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "John Smith"}}
            ]
        }
        mock_post.return_value = mock_response
        
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        name = service.extract_name_with_openai("Some text about a student")
        assert name == "John Smith"

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_failure(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI extraction failure."""
        mock_post.side_effect = Exception("API error")
        
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        name = service.extract_name_with_openai("Some text")
        assert name == "Unknown"

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_timeout(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI API timeout (line 77)."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        from src.service.deliverable_service import DeliverableService
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        with patch('src.service.deliverable_service.logger') as mock_logger:
            name = service.extract_name_with_openai("Some text")
            assert name == "Unknown"
            mock_logger.warning.assert_called_with("OpenAI API request timed out")

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_non_200_status(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI API non-200 status code (lines 111-119)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        from src.service.deliverable_service import DeliverableService
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        with patch('src.service.deliverable_service.logger') as mock_logger:
            name = service.extract_name_with_openai("Some text")
            assert name == "Unknown"
            mock_logger.warning.assert_called_with("OpenAI API returned status 400")

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_cleans_result(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI result cleaning (line 110)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Name: John Smith"}}
            ]
        }
        mock_post.return_value = mock_response
        
        from src.service.deliverable_service import DeliverableService
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        with patch('src.service.deliverable_service.logger') as mock_logger:
            name = service.extract_name_with_openai("Some text")
            assert name == "John Smith"
            mock_logger.info.assert_called_with("OpenAI extracted student name: John Smith")

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_with_openai_returns_unknown(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI returning 'Unknown' (line 112-113)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Unknown"}}
            ]
        }
        mock_post.return_value = mock_response
        
        from src.service.deliverable_service import DeliverableService
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        name = service.extract_name_with_openai("Some text")
        assert name == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_non_pdf_with_extract_name(self, mock_get_repo: MagicMock) -> None:
        """Test upload of non-PDF with extract_name=True (line 173)."""
        from src.service.deliverable_service import DeliverableService
        from src.repository.db.models import AssignmentModel
        
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
        mock_repo.store_deliverable.return_value = "deliverable_id"
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        deliverable_id = service.upload_deliverable(
            "assignment_id",
            "document.txt",
            b"text content",
            "txt",
            "text/plain",
            extract_name=True
        )
        
        assert deliverable_id == "deliverable_id"
        
        mock_repo.store_deliverable.assert_called_once_with(
            assignment_id="assignment_id",
            filename="document.txt",
            content=b"text content",
            extension="txt",
            content_type="text/plain",
            student_name="Unknown",
            extracted_text=None
        )

    @patch('src.service.deliverable_service.requests.post')
    @patch('src.service.deliverable_service.PdfReader')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_student_name_from_pdf_with_openai_integration(
        self, 
        mock_get_repo: MagicMock, 
        mock_pdf_reader: MagicMock,
        mock_post: MagicMock
    ) -> None:
        """Test full integration of PDF extraction with OpenAI fallback."""
        from src.service.deliverable_service import DeliverableService
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some random assignment text without clear name pattern"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Jane Doe"}}
            ]
        }
        mock_post.return_value = mock_response
        
        service = DeliverableService()
        service.openai_api_key = "test_key"
        
        name, text = service.extract_student_name_from_pdf(b"pdf content")

        assert name == "Jane Doe"
        assert text is not None
        
        mock_post.assert_called_once()

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_pattern_found_but_invalid(self, mock_get_repo: MagicMock) -> None:
        """Test when pattern matches but name is invalid (line 137)."""
        service = DeliverableService()
        
        text = "Name: 123456\nAssignment"
        result = service.extract_name_from_text(text)
        assert result == "Unknown"

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.PdfReader')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_pdf_with_name_extraction(self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock, mock_logger: MagicMock) -> None:
        """Test PDF upload with name extraction and logging (lines 168-170)."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
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
        mock_repo.store_deliverable.return_value = "deliverable_id"
        mock_get_repo.return_value = mock_repo
        
        # Setup PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Student: Bob Smith\nHomework"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        service = DeliverableService()
        result = service.upload_deliverable(
            "assignment_id",
            "homework.pdf",
            b"pdf bytes",
            "pdf",
            "application/pdf",
            extract_name=True
        )
        
        assert result == "deliverable_id"
        mock_logger.info.assert_called_with("Extracted student name: Bob Smith")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_with_error_logging(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test bulk upload with error logging (line 226)."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
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
        mock_repo.store_deliverable.side_effect = Exception("Storage failed")
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        files = [("error_file.pdf", b"content", "pdf", "application/pdf")]
        
        result = service.upload_multiple_deliverables(
            "assignment_id",
            files,
            extract_names=False
        )
        
        assert result == []
        mock_logger.error.assert_called_with("Failed to upload error_file.pdf: Storage failed")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_all_patterns_return_unknown(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - all patterns return Unknown after cleaning."""
        service = DeliverableService()
        
        text = "Name: 123\nSome content here"
        result = service.extract_name_from_text(text)
        assert result == "Unknown"

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.PdfReader')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_pdf_extraction_with_name_logging(self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock, mock_logger: MagicMock) -> None:
        """Test lines 168-170 - PDF extraction with name logging."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.return_value = "id123"
        mock_get_repo.return_value = mock_repo
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Author: Mary Johnson"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        service = DeliverableService()
        service.upload_deliverable(
            "assignment_id",
            "test.pdf",
            b"pdf_bytes",
            "pdf",
            "application/pdf",
            extract_name=True
        )
        
        mock_logger.info.assert_called_with("Extracted student name: Mary Johnson")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_bulk_upload_error_logging(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 226 - error logging in bulk upload."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.side_effect = ValueError("Storage error")
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.upload_multiple_deliverables(
            "assignment_id",
            [("failing.pdf", b"content", "pdf", "application/pdf")],
            extract_names=False
        )
        
        assert result == []
        mock_logger.error.assert_called_with("Failed to upload failing.pdf: Storage error")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.PdfReader')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_pdf_logs_extracted_name(self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock, mock_logger: MagicMock) -> None:
        """Test lines 168-170 - logging extracted name."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.return_value = "id"
        mock_get_repo.return_value = mock_repo
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Name: Sarah Connor"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        service = DeliverableService()
        service.upload_deliverable(
            "assignment_id",
            "doc.pdf",
            b"pdf",
            "pdf",
            "application/pdf",
            extract_name=True
        )
        
        mock_logger.info.assert_called_with("Extracted student name: Sarah Connor")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_bulk_upload_logs_error(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 226 - logging upload error."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
        mock_repo = MagicMock()
        mock_assignment = AssignmentModel(
            _id=ObjectId(),
            name="Test",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.side_effect = RuntimeError("DB fail")
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        result = service.upload_multiple_deliverables(
            "assignment_id",
            [("bad.pdf", b"x", "pdf", "application/pdf")],
            extract_names=False
        )
        
        assert result == []
        mock_logger.error.assert_called_with("Failed to upload bad.pdf: DB fail")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_clean_student_name_too_short(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - name too short or all digits."""
        service = DeliverableService()
        
        assert service.clean_student_name("A") == "Unknown"
        
        assert service.clean_student_name("1 2 3") == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test line 226 - assignment not found in bulk upload."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_multiple_deliverables(
                "test_id",
                [("file.pdf", b"content", "pdf", "application/pdf")],
                extract_names=False
            )

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_lines_168_170_pdf_extraction_coverage(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test lines 168-170 - PDF extraction with name extraction and logging."""
        from src.repository.db.models import AssignmentModel
        from bson import ObjectId
        from datetime import datetime, timezone
        
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
        mock_repo.store_deliverable.return_value = "deliverable_id"
        mock_get_repo.return_value = mock_repo
        
        with patch.object(DeliverableService, 'extract_student_name_from_pdf', return_value=("Alice Johnson", "extracted text")):
            service = DeliverableService()
            result = service.upload_deliverable(
                "assignment_id",
                "homework.pdf",
                b"pdf content",
                "pdf",
                "application/pdf",
                extract_name=True
            )
            
            assert result == "deliverable_id"
            mock_logger.info.assert_called_with("Extracted student name: Alice Johnson")
            mock_repo.store_deliverable.assert_called_with(
                assignment_id="assignment_id",
                filename="homework.pdf",
                content=b"pdf content",
                extension="pdf",
                content_type="application/pdf",
                student_name="Alice Johnson",
                extracted_text="extracted text"
            )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_text_lines_168_170(self, mock_get_repo: MagicMock) -> None:
        """Test lines 168-170 - extract name from line matching pattern."""
        service = DeliverableService()
        
        text = "assignment title\nMary Johnson\ndate: 2024"
        result = service.extract_name_from_text(text)
        assert result == "Mary Johnson"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_line_by_line_pattern(self, mock_get_repo: MagicMock) -> None:
        """Test lines 168-170 - line by line pattern matching."""
        service = DeliverableService()
        
        text = "homework assignment\nSarah Williams\nsubmission date"
        result = service.extract_name_from_text(text)
        assert result == "Sarah Williams"
        
        with patch.object(service, 'clean_student_name', return_value="Unknown"):
            text = "some text\nJohn Doe\nmore text"
            result = service.extract_name_from_text(text)
            assert result == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_169_170_clean_returns_unknown(self, mock_get_repo: MagicMock) -> None:
        """Test lines 169-170 - when line matches but clean returns Unknown."""
        service = DeliverableService()
        
        text = "not a name\nA B\nmore text"

        with patch.object(service, 'clean_student_name', side_effect=lambda x: "Unknown" if x == "A B" else x): # type: ignore
            result = service.extract_name_from_text(text)
            assert result == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_line_successful(self, mock_get_repo: MagicMock) -> None:
        """Test line 170 - successfully extract name from individual line."""
        service = DeliverableService()
        
        text = "some random text\nJames Bond\nmore content here"
        result = service.extract_name_from_text(text)
        assert result == "James Bond"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_individual_line_success(self, mock_get_repo: MagicMock) -> None:
        """Test line 170 - successfully return name from individual line."""
        service = DeliverableService()
        
        text = "just some text\nJohn Smith\nmore text here"
        result = service.extract_name_from_text(text)
        assert result == "John Smith"