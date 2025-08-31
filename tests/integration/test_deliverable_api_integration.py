from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any, List
from httpx import Response
import io
import pytest

from src.controller.api.api import app
from config.config import ConfigManager


class TestDeliverableAPIIntegration:
    """Integration tests for deliverable API endpoints."""

    def setup_method(self) -> None:
        """Set up test client and reset config."""
        ConfigManager.reset()
        self.client: TestClient = TestClient(app)
        self.test_assignment_id: str = ""
        self.test_deliverable_ids: List[str] = []

    def teardown_method(self) -> None:
        """Clean up test data."""
        # Delete test deliverables
        for deliverable_id in self.test_deliverable_ids:
            try:
                self.client.delete(f"/deliverables/{deliverable_id}")
            except Exception:
                pass
        
        # Delete test assignment
        if self.test_assignment_id:
            try:
                self.client.delete(f"/assignments/{self.test_assignment_id}")
            except Exception:
                pass

    def test_full_deliverable_workflow(self) -> None:
        """Test complete deliverable workflow from upload to deletion."""
        # Step 1: Create an assignment
        assignment_data: Dict[str, Any] = {
            "name": "Integration Test Assignment",
            "confidence_threshold": 0.85
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assert create_response.status_code == status.HTTP_200_OK
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Step 2: Upload a single deliverable
        pdf_content = b"%PDF-1.4 Test PDF content"
        upload_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables",
            files={"file": ("submission1.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"}  # Don't extract name to avoid API calls
        )
        
        assert upload_response.status_code == status.HTTP_200_OK
        deliverable: Dict[str, Any] = upload_response.json()
        assert deliverable["filename"] == "submission1.pdf"
        assert deliverable["student_name"] == "Unknown"
        self.test_deliverable_ids.append(deliverable["id"])
        
        # Step 3: List deliverables
        list_response: Response = self.client.get(f"/assignments/{self.test_assignment_id}/deliverables")
        assert list_response.status_code == status.HTTP_200_OK
        deliverables_list: Dict[str, Any] = list_response.json()
        assert deliverables_list["total"] == 1
        assert len(deliverables_list["deliverables"]) == 1
        assert deliverables_list["deliverables"][0]["id"] == deliverable["id"]
        assert deliverables_list["deliverables"][0]["mark_status"] == "Unmarked"
        
        # Step 4: Update the deliverable
        update_data = {
            "student_name": "John Doe",
            "mark": 85.5,
            "certainty_threshold": 0.95
        }
        update_response: Response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json=update_data
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        updated_deliverable: Dict[str, Any] = update_response.json()
        assert updated_deliverable["student_name"] == "John Doe"
        assert updated_deliverable["mark"] == 85.5
        assert updated_deliverable["mark_status"] == "Marked"
        assert updated_deliverable["certainty_threshold"] == 0.95
        
        # Step 5: Download the deliverable
        download_response: Response = self.client.get(f"/deliverables/{deliverable['id']}/download")
        assert download_response.status_code == status.HTTP_200_OK
        assert download_response.content == pdf_content
        assert download_response.headers["content-type"] == "application/pdf"
        
        # Step 6: Delete the deliverable
        delete_response: Response = self.client.delete(f"/deliverables/{deliverable['id']}")
        assert delete_response.status_code == status.HTTP_200_OK
        assert delete_response.json()["message"] == "Deliverable deleted successfully"
        self.test_deliverable_ids.remove(deliverable['id'])
        
        # Step 7: Verify deletion
        list_response = self.client.get(f"/assignments/{self.test_assignment_id}/deliverables")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.json()["total"] == 0

    def test_bulk_upload_deliverables(self) -> None:
        """Test uploading multiple deliverables at once."""
        # Create an assignment
        assignment_data: Dict[str, Any] = {
            "name": "Bulk Upload Test Assignment",
            "confidence_threshold": 0.75
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assert create_response.status_code == status.HTTP_200_OK
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Upload multiple deliverables
        files = [
            ("files", ("submission1.pdf", io.BytesIO(b"%PDF-1.4 Content 1"), "application/pdf")),
            ("files", ("submission2.pdf", io.BytesIO(b"%PDF-1.4 Content 2"), "application/pdf")),
            ("files", ("submission3.pdf", io.BytesIO(b"%PDF-1.4 Content 3"), "application/pdf"))
        ]
        
        bulk_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables/bulk",
            files=files,
            data={"extract_names": "false"}
        )
        
        assert bulk_response.status_code == status.HTTP_200_OK
        bulk_result: Dict[str, Any] = bulk_response.json()
        assert bulk_result["total_uploaded"] == 3
        assert len(bulk_result["deliverables"]) == 3
        
        # Store IDs for cleanup
        for deliverable in bulk_result["deliverables"]:
            self.test_deliverable_ids.append(deliverable["id"])
        
        # Verify all were uploaded
        list_response: Response = self.client.get(f"/assignments/{self.test_assignment_id}/deliverables")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.json()["total"] == 3

    def test_invalid_file_format_rejection(self) -> None:
        """Test that non-PDF files are rejected."""
        # Create an assignment
        assignment_data: Dict[str, Any] = {
            "name": "Format Test Assignment",
            "confidence_threshold": 0.80
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assert create_response.status_code == status.HTTP_200_OK
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Try to upload a non-PDF file
        docx_content = b"PK\x03\x04 DOCX content"  # DOCX magic bytes
        upload_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables",
            files={"file": ("document.docx", io.BytesIO(docx_content), 
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"extract_name": "false"}
        )
        
        assert upload_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not supported" in upload_response.json()["detail"]

    def test_assignment_not_found_error(self) -> None:
        """Test uploading deliverable to non-existent assignment."""
        pdf_content = b"%PDF-1.4 Test content"
        upload_response: Response = self.client.post(
            "/assignments/60c72b2f9b1d8e2a1c9d4b7f/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        assert upload_response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in upload_response.json()["detail"]

    def test_update_partial_deliverable_info(self) -> None:
        """Test updating only some fields of a deliverable."""
        # Create assignment
        assignment_data: Dict[str, Any] = {
            "name": "Partial Update Test",
            "confidence_threshold": 0.70
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Upload deliverable
        pdf_content = b"%PDF-1.4 Test PDF"
        upload_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        deliverable: Dict[str, Any] = upload_response.json()
        self.test_deliverable_ids.append(deliverable["id"])
        
        # Update only student name
        update_response: Response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"student_name": "Jane Smith"}
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        updated: Dict[str, Any] = update_response.json()
        assert updated["student_name"] == "Jane Smith"
        assert updated["mark"] is None  # Should remain unchanged
        
        # Update only mark
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"mark": 92.0}
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()
        assert updated["student_name"] == "Jane Smith"  # Should retain previous update
        assert updated["mark"] == 92.0
        assert updated["mark_status"] == "Marked"

    def test_assignment_with_deliverables_deletion(self) -> None:
        """Test that deleting an assignment also deletes its deliverables."""
        # Create assignment
        assignment_data: Dict[str, Any] = {
            "name": "Deletion Test Assignment",
            "confidence_threshold": 0.85
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assignment: Dict[str, Any] = create_response.json()
        assignment_id = assignment["id"]
        
        # Upload deliverables
        pdf_content = b"%PDF-1.4 Test content"
        for i in range(3):
            upload_response: Response = self.client.post(
                f"/assignments/{assignment_id}/deliverables",
                files={"file": (f"submission{i}.pdf", io.BytesIO(pdf_content), "application/pdf")},
                data={"extract_name": "false"}
            )
            assert upload_response.status_code == status.HTTP_200_OK
            self.test_deliverable_ids.append(upload_response.json()["id"])
        
        # Delete assignment
        delete_response: Response = self.client.delete(f"/assignments/{assignment_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deliverables are also deleted
        for deliverable_id in self.test_deliverable_ids:
            download_response: Response = self.client.get(f"/deliverables/{deliverable_id}/download")
            assert download_response.status_code == status.HTTP_404_NOT_FOUND
        
        # Clear the list since they're already deleted
        self.test_deliverable_ids.clear()

    def test_deliverable_mark_validation(self) -> None:
        """Test mark validation boundaries."""
        # Create assignment
        assignment_data: Dict[str, Any] = {
            "name": "Mark Validation Test",
            "confidence_threshold": 0.75
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Upload deliverable
        pdf_content = b"%PDF-1.4 Test"
        upload_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        deliverable: Dict[str, Any] = upload_response.json()
        self.test_deliverable_ids.append(deliverable["id"])
        
        # Test valid marks at boundaries
        update_response: Response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"mark": 0.0}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"mark": 100.0}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # Test invalid marks
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"mark": -0.1}
        )
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"mark": 100.1}
        )
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_certainty_threshold_validation(self) -> None:
        """Test certainty threshold validation boundaries."""
        # Create assignment
        assignment_data: Dict[str, Any] = {
            "name": "Certainty Validation Test",
            "confidence_threshold": 0.80
        }
        
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assignment: Dict[str, Any] = create_response.json()
        self.test_assignment_id = assignment["id"]
        
        # Upload deliverable
        pdf_content = b"%PDF-1.4 Test"
        upload_response: Response = self.client.post(
            f"/assignments/{self.test_assignment_id}/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"}
        )
        
        deliverable: Dict[str, Any] = upload_response.json()
        self.test_deliverable_ids.append(deliverable["id"])
        
        # Test valid certainty thresholds at boundaries
        update_response: Response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"certainty_threshold": 0.0}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"certainty_threshold": 1.0}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # Test invalid certainty thresholds
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"certainty_threshold": -0.01}
        )
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        update_response = self.client.patch(
            f"/deliverables/{deliverable['id']}",
            json={"certainty_threshold": 1.01}
        )
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY