import io
import math
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config.config import ConfigManager
from src.controller.api.api import app


class TestAssignmentWorkflow:
    def setup_method(self) -> None:
        ConfigManager.reset()
        self.client = TestClient(app)
        self.test_assignments: list[str] = []

    def teardown_method(self) -> None:
        for assignment_id in self.test_assignments:
            try:
                self.client.delete(f"/assignments/{assignment_id}")
            except Exception:
                pass

    def test_complete_assignment_lifecycle(self) -> None:
        assignment_data: dict[str, str | float] = {
            "name": "Integration Test Assignment",
            "confidence_threshold": 0.85,
        }

        response = self.client.post("/assignments", json=assignment_data)
        assert response.status_code == status.HTTP_200_OK

        assignment = response.json()
        assignment_id = assignment["id"]
        self.test_assignments.append(assignment_id)

        assert assignment["name"] == "Integration Test Assignment"
        assert math.isclose(assignment["confidence_threshold"], 0.85, rel_tol=1e-6, abs_tol=1e-12)
        assert assignment["deliverables"] == []

        response = self.client.get(f"/assignments/{assignment_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == assignment_id

        response = self.client.get("/assignments")
        assert response.status_code == status.HTTP_200_OK
        assert any(a["id"] == assignment_id for a in response.json()["assignments"])

        response = self.client.delete(f"/assignments/{assignment_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = self.client.get(f"/assignments/{assignment_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.test_assignments.remove(assignment_id)

    def test_assignment_with_files_workflow(self) -> None:
        assignment_data: dict[str, str | float] = {"name": "Assignment with Files", "confidence_threshold": 0.75}

        response = self.client.post("/assignments", json=assignment_data)
        assert response.status_code == status.HTTP_200_OK
        assignment_id = response.json()["id"]
        self.test_assignments.append(assignment_id)

        rubric_content = b"Test rubric content"
        response = self.client.post(
            f"/assignments/{assignment_id}/rubrics",
            files={"file": ("rubric.pdf", io.BytesIO(rubric_content), "application/pdf")},
        )
        assert response.status_code == status.HTTP_200_OK
        rubric_id = response.json()["id"]

        doc_content = b"Test document content"
        response = self.client.post(
            f"/assignments/{assignment_id}/documents",
            files={"file": ("doc.txt", io.BytesIO(doc_content), "text/plain")},
        )
        assert response.status_code == status.HTTP_200_OK
        doc_id = response.json()["id"]

        response = self.client.get(f"/assignments/{assignment_id}")
        assert response.status_code == status.HTTP_200_OK
        assignment_detail = response.json()

        assert len(assignment_detail["evaluation_rubrics"]) == 1
        assert len(assignment_detail["relevant_documents"]) == 1
        assert assignment_detail["evaluation_rubrics"][0]["filename"] == "rubric.pdf"
        assert assignment_detail["relevant_documents"][0]["filename"] == "doc.txt"

        response = self.client.get(f"/files/{rubric_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == rubric_content

        response = self.client.get(f"/files/{doc_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == doc_content

    @pytest.mark.parametrize(
        "invalid_data,expected_status",
        [
            ({"name": "", "confidence_threshold": 0.75}, status.HTTP_422_UNPROCESSABLE_CONTENT),
            ({"name": "Test", "confidence_threshold": 1.5}, status.HTTP_422_UNPROCESSABLE_CONTENT),
            ({"name": "Test", "confidence_threshold": -0.1}, status.HTTP_422_UNPROCESSABLE_CONTENT),
            ({"confidence_threshold": 0.75}, status.HTTP_422_UNPROCESSABLE_CONTENT),
            ({"name": "Test"}, status.HTTP_422_UNPROCESSABLE_CONTENT),
        ],
    )
    def test_assignment_validation(self, invalid_data: dict[str, Any], expected_status: int) -> None:
        response = self.client.post("/assignments", json=invalid_data)
        assert response.status_code == expected_status

    def test_assignment_not_found_handling(self) -> None:
        fake_id = "60c72b2f9b1d8e2a1c9d4b7f"

        response = self.client.get(f"/assignments/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = self.client.delete(f"/assignments/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = self.client.post(
            f"/assignments/{fake_id}/rubrics", files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_multiple_assignments_management(self) -> None:
        assignments: list[dict[str, Any]] = []
        for i in range(5):
            response = self.client.post(
                "/assignments", json={"name": f"Batch Assignment {i}", "confidence_threshold": 0.70 + i * 0.05}
            )
            assert response.status_code == status.HTTP_200_OK
            assignment = response.json()
            assignments.append(assignment)
            self.test_assignments.append(assignment["id"])

        response = self.client.get("/assignments")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 5

        listed_ids = [a["id"] for a in data["assignments"]]
        for assignment in assignments:
            assert assignment["id"] in listed_ids

        for assignment in assignments:
            response = self.client.delete(f"/assignments/{assignment['id']}")
            assert response.status_code == status.HTTP_204_NO_CONTENT
            self.test_assignments.remove(assignment["id"])

    def test_file_download_not_found(self) -> None:
        response = self.client.get("/files/60c72b2f9b1d8e2a1c9d4b7f")
        assert response.status_code == status.HTTP_404_NOT_FOUND
