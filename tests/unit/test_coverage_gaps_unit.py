from unittest.mock import patch, MagicMock
from src.service.deliverable_service import DeliverableService
from src.controller.api.api import app
from fastapi.testclient import TestClient
from fastapi import status
import io

class TestAPICoverageGaps:
    """Tests for uncovered lines in api.py."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.controller.api.api.AssignmentService')
    def test_line_273_rubric_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 273."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = RuntimeError("Error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/id/rubrics",
            files={"file": ("r.pdf", io.BytesIO(b"c"), "application/pdf")}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch('src.controller.api.api.DeliverableService')
    def test_line_328_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 328."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/id/deliverables",
            files={"file": ("t.pdf", io.BytesIO(b"c"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch('src.controller.api.api.DeliverableService')  
    def test_line_372_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 372."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = RuntimeError("Error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/id/deliverables/bulk",
            files=[("files", ("t.pdf", io.BytesIO(b"c"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch('src.controller.api.api.DeliverableService')
    def test_line_451_update_retrieval_failure(self, mock_service_class: MagicMock) -> None:
        """Test line 451."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/id",
            json={"student_name": "Test"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

class TestDeliverableServiceCoverageGaps:
    """Tests for uncovered lines in deliverable_service.py."""

    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_137_clean_returns_unknown(self, mock_get_repo: MagicMock) -> None:
        """Test line 137 - when all pattern matches return Unknown."""
        service = DeliverableService()
        
        text = "Name: ###\nSome content"
        result = service.extract_name_from_text(text)
        assert result == "Unknown"

    @patch('src.service.deliverable_service.get_database_repository')
    def test_lines_175_177_non_pdf(self, mock_get_repo: MagicMock) -> None:
        """Test lines 175-177."""
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

    @patch('src.service.deliverable_service.logger')
    @patch('src.service.deliverable_service.get_database_repository')
    def test_line_233_exception_logging(self, mock_get_repo: MagicMock, mock_logger: MagicMock) -> None:
        """Test line 233."""
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
        
        with patch.object(service, 'upload_deliverable', side_effect=Exception("Error")):
            files = [("f.pdf", b"c", "pdf", "application/pdf")]
            result = service.upload_multiple_deliverables("id", files, False)
            
            assert result == []
            mock_logger.error.assert_called()