from fastapi.testclient import TestClient
from fastapi import status
from typing import Dict, Any, List
from httpx import Response
import io

from src.controller.api.api import app
from config.config import ConfigManager


class TestAssignmentAPIIntegration:
    """Integration tests for assignment API endpoints."""

    def setup_method(self) -> None:
        """Set up test client and reset config."""
        ConfigManager.reset()
        self.client: TestClient = TestClient(app)
        self.test_assignment_id: str = ""

    def test_create_assignment(self) -> None:
        """Test creating a new assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment Integration",
            "confidence_threshold": 0.85
        }
        
        response: Response = self.client.post("/assignments", json=assignment_data)
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        
        assert "id" in data
        assert data["name"] == "Test Assignment Integration"
        assert data["confidence_threshold"] == 0.85
        assert data["deliverables"] == []
        assert data["evaluation_rubrics_count"] == 0
        assert data["relevant_documents_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data
        
        self.test_assignment_id = data["id"]

    def test_create_assignment_invalid_name(self) -> None:
        """Test creating assignment with invalid name."""
        assignment_data: Dict[str, Any] = {
            "name": "",
            "confidence_threshold": 0.75
        }
        
        response: Response = self.client.post("/assignments", json=assignment_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_assignment_invalid_threshold(self) -> None:
        """Test creating assignment with invalid threshold."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment",
            "confidence_threshold": 1.5
        }
        
        response: Response = self.client.post("/assignments", json=assignment_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_assignments(self) -> None:
        """Test listing all assignments."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for List",
            "confidence_threshold": 0.90
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        
        response: Response = self.client.get("/assignments")
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        
        assert "assignments" in data
        assert "total" in data
        assert isinstance(data["assignments"], list)
        assert data["total"] >= 1
        
        assignments: List[Dict[str, Any]] = data["assignments"]  # type: ignore[assignment]
        assignment_ids: List[str] = [assignment["id"] for assignment in assignments]
        assert created_assignment["id"] in assignment_ids
        
        self.client.delete(f"/assignments/{created_assignment['id']}")

    def test_get_assignment(self) -> None:
        """Test getting a specific assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for Get",
            "confidence_threshold": 0.70
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        assignment_id = created_assignment["id"]
        
        response: Response = self.client.get(f"/assignments/{assignment_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        
        assert data["id"] == assignment_id
        assert data["name"] == "Test Assignment for Get"
        assert data["confidence_threshold"] == 0.70
        assert "evaluation_rubrics" in data
        assert "relevant_documents" in data
        assert isinstance(data["evaluation_rubrics"], list)
        assert isinstance(data["relevant_documents"], list)
        
        self.client.delete(f"/assignments/{assignment_id}")

    def test_get_assignment_not_found(self) -> None:
        """Test getting a non-existent assignment."""
        response: Response = self.client.get("/assignments/60c72b2f9b1d8e2a1c9d4b7f")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data: Dict[str, Any] = response.json()
        assert "detail" in data

    def test_delete_assignment(self) -> None:
        """Test deleting an assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for Delete",
            "confidence_threshold": 0.60
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        assignment_id = created_assignment["id"]
        
        response: Response = self.client.delete(f"/assignments/{assignment_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        get_response: Response = self.client.get(f"/assignments/{assignment_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_assignment_not_found(self) -> None:
        """Test deleting a non-existent assignment."""
        response: Response = self.client.delete("/assignments/60c72b2f9b1d8e2a1c9d4b7f")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_rubric(self) -> None:
        """Test uploading a rubric for an assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for Rubric",
            "confidence_threshold": 0.80
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        assignment_id = created_assignment["id"]
        
        file_content = b"This is a test rubric content"
        files = {
            "file": ("test_rubric.pdf", io.BytesIO(file_content), "application/pdf")
        }
        
        response: Response = self.client.post(
            f"/assignments/{assignment_id}/rubrics",
            files=files
        )
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        
        assert "id" in data
        assert data["filename"] == "test_rubric.pdf"
        assert "uploaded_at" in data
        assert data["message"] == "Rubric uploaded successfully"
        
        self.client.delete(f"/assignments/{assignment_id}")

    def test_upload_rubric_assignment_not_found(self) -> None:
        """Test uploading a rubric for non-existent assignment."""
        file_content = b"Test content"
        files = {
            "file": ("test.pdf", io.BytesIO(file_content), "application/pdf")
        }
        
        response: Response = self.client.post(
            "/assignments/60c72b2f9b1d8e2a1c9d4b7f/rubrics",
            files=files
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_relevant_document(self) -> None:
        """Test uploading a relevant document for an assignment."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for Document",
            "confidence_threshold": 0.75
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        assignment_id = created_assignment["id"]
        
        file_content = b"This is a test document content"
        files = {
            "file": ("example.docx", io.BytesIO(file_content), 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        response: Response = self.client.post(
            f"/assignments/{assignment_id}/documents",
            files=files
        )
        
        assert response.status_code == status.HTTP_200_OK
        data: Dict[str, Any] = response.json()
        
        assert "id" in data
        assert data["filename"] == "example.docx"
        assert "uploaded_at" in data
        assert data["message"] == "Document uploaded successfully"
        
        self.client.delete(f"/assignments/{assignment_id}")

    def test_download_file(self) -> None:
        """Test downloading a file."""
        assignment_data: Dict[str, Any] = {
            "name": "Test Assignment for Download",
            "confidence_threshold": 0.85
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        created_assignment: Dict[str, Any] = create_response.json()
        assignment_id = created_assignment["id"]
        
        file_content = b"Download test content"
        files = {
            "file": ("download_test.txt", io.BytesIO(file_content), "text/plain")
        }
        
        upload_response: Response = self.client.post(
            f"/assignments/{assignment_id}/documents",
            files=files
        )
        file_data: Dict[str, Any] = upload_response.json()
        file_id = file_data["id"]
        
        response: Response = self.client.get(f"/files/{file_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == file_content
        assert response.headers["content-type"].startswith("text/plain")
        assert "attachment; filename=download_test.txt" in response.headers["content-disposition"]
        
        self.client.delete(f"/assignments/{assignment_id}")

    def test_download_file_not_found(self) -> None:
        """Test downloading a non-existent file."""
        response: Response = self.client.get("/files/60c72b2f9b1d8e2a1c9d4b7f")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_full_assignment_workflow(self) -> None:
        """Test complete assignment workflow."""
        assignment_data: Dict[str, Any] = {
            "name": "Complete Workflow Test",
            "confidence_threshold": 0.95
        }
        create_response: Response = self.client.post("/assignments", json=assignment_data)
        assignment: Dict[str, Any] = create_response.json()
        assignment_id = assignment["id"]
        
        rubric_content = b"Rubric content"
        rubric_files = {
            "file": ("rubric.pdf", io.BytesIO(rubric_content), "application/pdf")
        }
        rubric_response: Response = self.client.post(
            f"/assignments/{assignment_id}/rubrics",
            files=rubric_files
        )
        assert rubric_response.status_code == status.HTTP_200_OK
        
        doc_content = b"Document content"
        doc_files = {
            "file": ("document.txt", io.BytesIO(doc_content), "text/plain")
        }
        doc_response: Response = self.client.post(
            f"/assignments/{assignment_id}/documents",
            files=doc_files
        )
        assert doc_response.status_code == status.HTTP_200_OK
        
        get_response: Response = self.client.get(f"/assignments/{assignment_id}")
        assignment_detail: Dict[str, Any] = get_response.json()
        
        assert len(assignment_detail["evaluation_rubrics"]) == 1
        assert len(assignment_detail["relevant_documents"]) == 1
        assert assignment_detail["evaluation_rubrics"][0]["filename"] == "rubric.pdf"
        assert assignment_detail["relevant_documents"][0]["filename"] == "document.txt"
        
        self.client.delete(f"/assignments/{assignment_id}")