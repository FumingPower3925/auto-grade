from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

from src.controller.api.api import app

class TestAPIMissingCoverage:
    """Tests for missing coverage in api.py."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch('src.controller.api.api.AssignmentService')
    def test_line_273_rubric_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 273."""
        mock_service = MagicMock()
        mock_service.upload_rubric.side_effect = RuntimeError("DB Error")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/some_id/rubrics",
            files={"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload rubric"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_328_deliverable_not_retrieved(self, mock_service_class: MagicMock) -> None:
        """Test line 328."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_deliverable.return_value = "del_id"
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/some_id/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve uploaded deliverable"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_372_bulk_general_exception(self, mock_service_class: MagicMock) -> None:
        """Test line 372."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, "")
        mock_service.upload_multiple_deliverables.side_effect = RuntimeError("Bulk fail")
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/assignments/some_id/deliverables/bulk",
            files=[("files", ("test.pdf", io.BytesIO(b"data"), "application/pdf"))],
            data={"extract_names": "false"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to upload deliverables"

    @patch('src.controller.api.api.DeliverableService')
    def test_line_451_update_not_retrieved(self, mock_service_class: MagicMock) -> None:
        """Test line 451."""
        mock_service = MagicMock()
        mock_service.update_deliverable.return_value = True
        mock_service.get_deliverable.return_value = None
        mock_service_class.return_value = mock_service
        
        response = self.client.patch(
            "/deliverables/some_id",
            json={"student_name": "Name"}
        )
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve updated deliverable"