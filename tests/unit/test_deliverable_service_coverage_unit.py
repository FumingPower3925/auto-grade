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