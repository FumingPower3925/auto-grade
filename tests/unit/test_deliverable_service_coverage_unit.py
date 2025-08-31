from unittest.mock import patch, MagicMock
from src.service.deliverable_service import DeliverableService

class TestDeliverableServiceCoverage:
    """Tests for uncovered lines in deliverable_service.py."""

    @patch('src.service.deliverable_service.get_database_repository')
    def test_extract_name_from_text_line_137(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - when clean_student_name returns Unknown."""
        service = DeliverableService()
        
        with patch.object(service, 'clean_student_name', return_value="Unknown"):
            result = service.extract_name_from_text("Name: 123456")
            assert result == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_deliverable_lines_175_177(self, mock_get_repo: MagicMock) -> None:
        """Test lines 175-177 - non-PDF with extract_name=True."""
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
        
        service = DeliverableService()
        
        result = service.upload_deliverable(
            "assignment_id",
            "file.txt",
            b"content",
            "txt",
            "text/plain",
            extract_name=True
        )
        
        assert result == "id"
        mock_repo.store_deliverable.assert_called_with(
            assignment_id="assignment_id",
            filename="file.txt",
            content=b"content",
            extension="txt",
            content_type="text/plain",
            student_name="Unknown",
            extracted_text=None
        )

    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_line_233(self, mock_get_repo: MagicMock) -> None:
        """Test line 233 - exception during bulk upload."""
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
        mock_repo.store_deliverable.side_effect = [Exception("Error")]
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        files = [("file.pdf", b"content", "pdf", "application/pdf")]
        
        with patch('src.service.deliverable_service.logger') as mock_logger:
            result = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
            
            assert result == []
            mock_logger.error.assert_called()

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_170_extracted_text_logging(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 170 - logging extracted student name."""
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
        
        with patch.object(DeliverableService, 'extract_student_name_from_pdf', return_value=("John Smith", "extracted text")):
            service = DeliverableService()
            service.upload_deliverable(
                "assignment_id",
                "file.pdf",
                b"content",
                "pdf",
                "application/pdf",
                extract_name=True
            )
            
            mock_logger.info.assert_called_with("Extracted student name: John Smith")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_upload_multiple_deliverables_line_226(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 226 - exception logging during bulk upload."""
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
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with patch.object(service, 'upload_deliverable', side_effect=Exception("Upload error")):
            files = [("file.pdf", b"content", "pdf", "application/pdf")]
            
            result = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
            
            assert result == []
            mock_logger.error.assert_called_with("Failed to upload file.pdf: Upload error")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_137_pattern_match_returns_unknown(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - when pattern matches but clean_student_name returns Unknown."""
        service = DeliverableService()
        
        text = "Name: 12345\nSome content"
        result = service.extract_name_from_text(text)
        assert result == "Unknown"

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.PdfReader')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_lines_168_170_pdf_extraction_with_logging(self, mock_get_repo: MagicMock, mock_pdf_reader: MagicMock, mock_logger: MagicMock) -> None:
        """Test lines 168-170 - PDF extraction with logging."""
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
        mock_page.extract_text.return_value = "Name: Jane Doe"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        service = DeliverableService()
        result = service.upload_deliverable(
            "assignment_id",
            "file.pdf",
            b"pdf content",
            "pdf",
            "application/pdf",
            extract_name=True
        )
        
        assert result == "id"
        mock_logger.info.assert_called_with("Extracted student name: Jane Doe")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_226_exception_message_logging(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 226 - exception message logging during bulk upload."""
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
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with patch.object(service, 'upload_deliverable', side_effect=Exception("Database connection failed")):
            files = [("test_file.pdf", b"content", "pdf", "application/pdf")]
            
            result = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
            
            assert result == []
            mock_logger.error.assert_called_with("Failed to upload test_file.pdf: Database connection failed")

    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_137_pattern_matches_but_clean_returns_unknown(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - pattern matches but clean_student_name returns Unknown."""
        service = DeliverableService()
        
        with patch.object(service, 'clean_student_name', return_value="Unknown"):
            text = "Name: SomeName\nContent"
            result = service.extract_name_from_text(text)
            assert result == "Unknown"

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_lines_168_170_extract_and_log_student_name(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test lines 168-170 - extract student name from PDF and log it."""
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
        
        service = DeliverableService()
        
        with patch.object(service, 'extract_student_name_from_pdf', return_value=("Alice Smith", "text")):
            result = service.upload_deliverable(
                "assignment_id",
                "document.pdf",
                b"pdf content",
                "pdf",
                "application/pdf",
                extract_name=True
            )
        
        assert result == "id"
        mock_logger.info.assert_called_with("Extracted student name: Alice Smith")

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_226_log_upload_failure(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 226 - log error message when upload fails."""
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
        mock_get_repo.return_value = mock_repo
        
        service = DeliverableService()
        
        with patch.object(service, 'upload_deliverable', side_effect=Exception("Test error")):
            files = [("failed_file.pdf", b"content", "pdf", "application/pdf")]
            
            result = service.upload_multiple_deliverables(
                "assignment_id",
                files,
                extract_names=False
            )
        
        assert result == []
        mock_logger.error.assert_called_with("Failed to upload failed_file.pdf: Test error")