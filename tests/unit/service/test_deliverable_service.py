from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from bson import ObjectId

from src.repository.db.models import AssignmentModel, DeliverableModel
from src.service.deliverable_service import DeliverableService


class TestDeliverableService:
    """Tests for DeliverableService - consolidated from multiple test files."""

    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_student_name_from_pdf_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful student name extraction from PDF."""
        with patch("src.service.deliverable_service.PdfReader") as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Name: John Doe"

            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance

            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")

            assert name == "John Doe"
            assert text is not None and "John Doe" in text

    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "pdf_text,expected_name",
        [
            ("Student: Jane Smith\nHomework", "Jane Smith"),
            ("Submitted by: Bob Johnson\nDate", "Bob Johnson"),
            ("Author: Charlie Davis\nIntro", "Charlie Davis"),
            ("Alice Brown\nCS101 Assignment", "Alice Brown"),
        ],
    )
    def test_extract_student_name_patterns(self, mock_get_repo: MagicMock, pdf_text: str, expected_name: str) -> None:
        """Test extracting student name with various patterns."""
        service = DeliverableService()

        with patch("src.service.deliverable_service.PdfReader") as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = pdf_text

            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance

            name, _ = service.extract_student_name_from_pdf(b"pdf content")  # type: ignore
            assert name == expected_name

    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_student_name_from_pdf_exception(self, mock_get_repo: MagicMock) -> None:
        """Test extraction when PDF parsing fails."""
        with patch("src.service.deliverable_service.PdfReader", side_effect=Exception("PDF error")):
            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")

            assert name == "Unknown"
            assert text is None

    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_student_name_from_pdf_no_text(self, mock_get_repo: MagicMock) -> None:
        """Test extraction when PDF has no readable text."""
        with patch("src.service.deliverable_service.PdfReader") as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = []
            mock_pdf_reader.return_value = mock_reader_instance

            service = DeliverableService()
            name, text = service.extract_student_name_from_pdf(b"pdf content")

            assert name == "Unknown"
            assert text is None

    @patch("src.service.deliverable_service.logger")
    @patch("src.service.deliverable_service.PdfReader")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_pdf_with_page_extraction_failure(
        self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test PDF extraction when a page fails to extract."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.side_effect = Exception("Page extraction error")

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Name: Jane Smith"

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance

        service = DeliverableService()
        name, _ = service.extract_student_name_from_pdf(b"pdf content")  # type: ignore

        assert name == "Jane Smith"
        mock_logger.warning.assert_called()

    @patch("src.service.deliverable_service.httpx.post")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_name_with_openai_success(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test successful name extraction with OpenAI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "John Smith"}}]}
        mock_post.return_value = mock_response

        service = DeliverableService()
        service.openai_api_key = "test_key"

        name = service.extract_name_with_openai("Some text")
        assert name == "John Smith"

    @patch("src.service.deliverable_service.httpx.post")
    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "exception,expected_log",
        [
            (Exception("API error"), None),
            (httpx.TimeoutException("Timeout"), "OpenAI API request timed out"),
        ],
    )
    def test_extract_name_with_openai_exceptions(
        self, mock_get_repo: MagicMock, mock_post: MagicMock, exception: Exception, expected_log: str
    ) -> None:
        """Test OpenAI extraction with various exceptions."""
        mock_post.side_effect = exception

        service = DeliverableService()
        service.openai_api_key = "test_key"

        with patch("src.service.deliverable_service.logger") as mock_logger:
            name = service.extract_name_with_openai("Some text")
            assert name == "Unknown"

            if expected_log:
                mock_logger.warning.assert_called_with(expected_log)

    @patch("src.service.deliverable_service.httpx.post")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_name_with_openai_non_200_status(self, mock_get_repo: MagicMock, mock_post: MagicMock) -> None:
        """Test OpenAI API non-200 status code (lines 111-119)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        service = DeliverableService()
        service.openai_api_key = "test_key"

        with patch("src.service.deliverable_service.logger") as mock_logger:
            name = service.extract_name_with_openai("Some text")
            assert name == "Unknown"
            mock_logger.warning.assert_called_with("OpenAI API returned status 400")

    @patch("src.service.deliverable_service.logger")
    @patch("src.service.deliverable_service.httpx.post")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_name_with_openai_cleans_result(
        self, mock_get_repo: MagicMock, mock_post: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test OpenAI result cleaning (line 110)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Name: John Smith"}}]}
        mock_post.return_value = mock_response

        service = DeliverableService()
        service.openai_api_key = "test_key"

        name = service.extract_name_with_openai("Some text")
        assert name == "John Smith"
        mock_logger.info.assert_called_with("OpenAI extracted student name: John Smith")

    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("John Doe", "John Doe"),
            ("Name: Jane Smith", "Jane Smith"),
            ("Student: Bob Johnson", "Bob Johnson"),
            ("Author: Alice Brown", "Alice Brown"),
            ("Submitted by: Charlie Davis", "Charlie Davis"),
            ("By: Emily Wilson", "Emily Wilson"),
            ("", "Unknown"),
            ("unknown", "Unknown"),
            ("not found", "Unknown"),
            ("n/a", "Unknown"),
            ("none", "Unknown"),
            ("123456", "Unknown"),
            ("!@#$%^", "Unknown"),
            ("John@Doe#2024", "John Doe 2024"),
            ("Mary-Jane O'Neill", "Mary-Jane O'Neill"),
            ("A", "Unknown"),
            ("1 2 3", "Unknown"),
            ("A" * 150, "A" * 100),
        ],
    )
    def test_clean_student_name(self, mock_get_repo: MagicMock, input_name: str, expected: str) -> None:
        """Test cleaning student names with various inputs."""
        service = DeliverableService()
        assert service.clean_student_name(input_name) == expected

    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_name_from_text(self, mock_get_repo: MagicMock) -> None:
        """Test extract_name_from_text method."""
        service = DeliverableService()

        assert service.extract_name_from_text("") == "Unknown"
        assert service.extract_name_from_text("Name: John Smith\nAssignment") == "John Smith"
        assert service.extract_name_from_text("Jane Doe\nComputer Science") == "Jane Doe"
        assert service.extract_name_from_text("Random text without name") == "Unknown"
        assert service.extract_name_from_text("Name: 123456\nContent") == "Unknown"

    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_deliverable_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful deliverable upload."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.return_value = "deliverable_id_123"
        mock_get_repo.return_value = mock_repo

        with patch.object(
            DeliverableService, "extract_student_name_from_pdf", return_value=("John Doe", "extracted text")
        ):
            service = DeliverableService()
            deliverable_id = service.upload_deliverable(
                "assignment_id", "submission.pdf", b"pdf content", "pdf", "application/pdf", extract_name=True
            )

        assert deliverable_id == "deliverable_id_123"
        mock_repo.store_deliverable.assert_called_once_with(
            assignment_id="assignment_id",
            filename="submission.pdf",
            content=b"pdf content",
            extension="pdf",
            content_type="application/pdf",
            student_name="John Doe",
            extracted_text="extracted text",
        )

    @patch("src.service.deliverable_service.logger")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_deliverable_with_name_extraction_logging(
        self, mock_get_repo: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test PDF upload with name extraction and logging (lines 168-170)."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.return_value = "deliverable_id"
        mock_get_repo.return_value = mock_repo

        with patch.object(
            DeliverableService, "extract_student_name_from_pdf", return_value=("Alice Johnson", "extracted text")
        ):
            service = DeliverableService()
            result = service.upload_deliverable(
                "assignment_id", "homework.pdf", b"pdf content", "pdf", "application/pdf", extract_name=True
            )

            assert result == "deliverable_id"
            mock_logger.info.assert_called_with("Extracted student name: Alice Johnson")

    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_deliverable_non_pdf_with_extract_name(self, mock_get_repo: MagicMock) -> None:
        """Test upload of non-PDF with extract_name=True (lines 175-177)."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.return_value = "deliverable_id"
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        deliverable_id = service.upload_deliverable(
            "assignment_id", "document.txt", b"text content", "txt", "text/plain", extract_name=True
        )

        assert deliverable_id == "deliverable_id"
        mock_repo.store_deliverable.assert_called_with(
            assignment_id="assignment_id",
            filename="document.txt",
            content=b"text content",
            extension="txt",
            content_type="text/plain",
            student_name="Unknown",
            extracted_text=None,
        )

    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_deliverable_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test deliverable upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_deliverable("test_id", "submission.pdf", b"content", "pdf", "application/pdf")

    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_multiple_deliverables_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful upload of multiple deliverables."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.side_effect = ["id1", "id2", "id3"]
        mock_get_repo.return_value = mock_repo

        files: list[tuple[str, bytes, str, str]] = [
            ("file1.pdf", b"content1", "pdf", "application/pdf"),
            ("file2.pdf", b"content2", "pdf", "application/pdf"),
            ("file3.pdf", b"content3", "pdf", "application/pdf"),
        ]

        with patch.object(DeliverableService, "extract_student_name_from_pdf", return_value=("Student", None)):
            service = DeliverableService()
            deliverable_ids = service.upload_multiple_deliverables("assignment_id", files, extract_names=True)

        assert deliverable_ids == ["id1", "id2", "id3"]
        assert mock_repo.store_deliverable.call_count == 3

    @patch("src.service.deliverable_service.logger")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_multiple_deliverables_with_errors(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test bulk upload with some failures and error logging (line 233, 226)."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_deliverable.side_effect = ["id1", Exception("Storage failed"), "id3"]
        mock_get_repo.return_value = mock_repo

        files: list[tuple[str, bytes, str, str]] = [
            ("file1.pdf", b"content1", "pdf", "application/pdf"),
            ("error_file.pdf", b"content2", "pdf", "application/pdf"),
            ("file3.pdf", b"content3", "pdf", "application/pdf"),
        ]

        service = DeliverableService()
        deliverable_ids = service.upload_multiple_deliverables("assignment_id", files, extract_names=False)

        assert deliverable_ids == ["id1", "id3"]
        mock_logger.error.assert_called_with("Failed to upload error_file.pdf: Storage failed")

    @patch("src.service.deliverable_service.get_database_repository")
    def test_upload_multiple_deliverables_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test bulk upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            service.upload_multiple_deliverables("test_id", [("file.pdf", b"content", "pdf", "application/pdf")], False)

    @patch("src.service.deliverable_service.get_database_repository")
    def test_update_deliverable_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful deliverable update."""
        mock_repo = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_repo.update_deliverable.return_value = True
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.update_deliverable(
            "deliverable_id", student_name="Updated Name", mark=8.55, certainty_threshold=0.95
        )

        assert result is True
        mock_repo.update_deliverable.assert_called_once_with(
            "deliverable_id", student_name="Updated Name", mark=8.55, certainty_threshold=0.95
        )

    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "mark,error_msg",
        [
            (15.0, "Mark must be between 0.0 and 10.0"),
            (-10.0, "Mark must be between 0.0 and 10.0"),
        ],
    )
    def test_update_deliverable_invalid_mark(self, mock_get_repo: MagicMock, mark: float, error_msg: str) -> None:
        """Test deliverable update with invalid mark."""
        mock_repo = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()

        with pytest.raises(ValueError, match=error_msg):
            service.update_deliverable("deliverable_id", mark=mark)

    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "certainty,error_msg",
        [
            (1.5, "Certainty threshold must be between 0.0 and 1.0"),
            (-0.1, "Certainty threshold must be between 0.0 and 1.0"),
        ],
    )
    def test_update_deliverable_invalid_certainty(
        self, mock_get_repo: MagicMock, certainty: float, error_msg: str
    ) -> None:
        """Test deliverable update with invalid certainty threshold."""
        mock_repo = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()

        with pytest.raises(ValueError, match=error_msg):
            service.update_deliverable("deliverable_id", certainty_threshold=certainty)

    @patch("src.service.deliverable_service.get_database_repository")
    def test_update_deliverable_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test updating non-existent deliverable."""
        mock_repo = MagicMock()
        mock_repo.get_deliverable.return_value = None
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.update_deliverable("deliverable_id", student_name="New Name")

        assert result is False
        mock_repo.update_deliverable.assert_not_called()

    @patch("src.service.deliverable_service.get_database_repository")
    def test_update_deliverable_no_changes(self, mock_get_repo: MagicMock) -> None:
        """Test updating deliverable with no changes."""
        mock_repo = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.update_deliverable("deliverable_id")

        assert result is False
        mock_repo.update_deliverable.assert_not_called()

    @patch("src.service.deliverable_service.get_database_repository")
    def test_get_deliverable(self, mock_get_repo: MagicMock) -> None:
        """Test getting a deliverable."""
        mock_repo = MagicMock()
        mock_deliverable = self._create_mock_deliverable()
        mock_repo.get_deliverable.return_value = mock_deliverable
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.get_deliverable("deliverable_id")

        assert result == mock_deliverable
        mock_repo.get_deliverable.assert_called_once_with("deliverable_id")

    @patch("src.service.deliverable_service.get_database_repository")
    def test_list_deliverables(self, mock_get_repo: MagicMock) -> None:
        """Test listing deliverables."""
        mock_repo = MagicMock()
        mock_deliverables = [
            self._create_mock_deliverable("Student 1", mark=8.0),
            self._create_mock_deliverable("Student 2", mark=None),
        ]
        mock_repo.list_deliverables_by_assignment.return_value = mock_deliverables
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.list_deliverables("assignment_id")

        assert result == mock_deliverables
        assert len(result) == 2
        mock_repo.list_deliverables_by_assignment.assert_called_once_with("assignment_id")

    @patch("src.service.deliverable_service.get_database_repository")
    def test_delete_deliverable(self, mock_get_repo: MagicMock) -> None:
        """Test deleting a deliverable."""
        mock_repo = MagicMock()
        mock_repo.delete_deliverable.return_value = True
        mock_get_repo.return_value = mock_repo

        service = DeliverableService()
        result = service.delete_deliverable("deliverable_id")

        assert result is True
        mock_repo.delete_deliverable.assert_called_once_with("deliverable_id")

    @patch("src.service.deliverable_service.PdfReader")
    @patch("src.service.deliverable_service.get_database_repository")
    def test_extract_student_name_from_pdf_calls_openai(
        self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock
    ) -> None:
        """Test that OpenAI is called when initial extraction returns Unknown."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some text without a clear name pattern"

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance

        service = DeliverableService()
        service.openai_api_key = "test_api_key"

        with patch.object(service, "extract_name_with_openai", return_value="John Doe") as mock_openai:
            name, _ = service.extract_student_name_from_pdf(b"pdf content")  # type: ignore

            mock_openai.assert_called_once()
            assert name == "John Doe"

    @patch("src.service.deliverable_service.get_database_repository")
    @pytest.mark.parametrize(
        "filename,content_type,expected_valid,expected_error",
        [
            ("document.pdf", "application/pdf", True, ""),
            ("Document.PDF", "application/pdf", True, ""),
            ("document.docx", "application/vnd.openxmlformats", False, "File format not supported"),
            ("document.pdf", "text/plain", False, "Content type not supported"),
        ],
    )
    def test_validate_file_format(
        self, mock_get_repo: MagicMock, filename: str, content_type: str, expected_valid: bool, expected_error: str
    ) -> None:
        """Test file format validation."""
        service = DeliverableService()
        is_valid, error = service.validate_file_format(filename, content_type)

        assert is_valid == expected_valid
        if expected_error:
            assert expected_error in error

    def _create_mock_assignment(self) -> AssignmentModel:
        """Create a mock AssignmentModel."""
        return AssignmentModel(
            _id=ObjectId(),
            name="Test Assignment",
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def _create_mock_deliverable(self, student_name: str = "John Doe", mark: float | None = None) -> DeliverableModel:
        """Create a mock DeliverableModel."""
        return DeliverableModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            student_name=student_name,
            mark=mark,
            certainty_threshold=None,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
