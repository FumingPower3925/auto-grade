import io

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config.config import ConfigManager
from src.controller.api.api import app


class TestDeliverableWorkflow:
    def setup_method(self) -> None:
        ConfigManager.reset()
        self.client = TestClient(app)

        response = self.client.post(
            "/assignments", json={"name": "Deliverable Test Assignment", "confidence_threshold": 0.80}
        )
        self.assignment_id = response.json()["id"]
        self.deliverable_ids: list[str] = []

    def teardown_method(self) -> None:
        for deliverable_id in self.deliverable_ids:
            try:
                self.client.delete(f"/deliverables/{deliverable_id}")
            except Exception:
                pass

        try:
            self.client.delete(f"/assignments/{self.assignment_id}")
        except Exception:
            pass

    def test_complete_deliverable_lifecycle(self) -> None:
        pdf_content = b"%PDF-1.4 Test PDF content"
        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables",
            files={"file": ("submission.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"extract_name": "false"},
        )
        assert response.status_code == status.HTTP_200_OK

        deliverable = response.json()
        deliverable_id = deliverable["id"]
        self.deliverable_ids.append(deliverable_id)

        assert deliverable["filename"] == "submission.pdf"
        assert deliverable["student_name"] == "Unknown"

        response = self.client.get(f"/assignments/{self.assignment_id}/deliverables")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 1

        update_data: dict[str, str | float] = {"student_name": "John Doe", "mark": 8.5, "certainty_threshold": 0.9}
        response = self.client.patch(f"/deliverables/{deliverable_id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        updated = response.json()
        assert updated["student_name"] == "John Doe"
        assert updated["mark"] == 8.5
        assert updated["mark_status"] == "Marked"
        assert updated["certainty_threshold"] == 0.9

        response = self.client.get(f"/deliverables/{deliverable_id}/download")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == pdf_content

        response = self.client.delete(f"/deliverables/{deliverable_id}")
        assert response.status_code == status.HTTP_200_OK
        self.deliverable_ids.remove(deliverable_id)

        response = self.client.get(f"/assignments/{self.assignment_id}/deliverables")
        assert response.json()["total"] == 0

    def test_bulk_deliverable_upload(self) -> None:
        files = [
            ("files", (f"submission{i}.pdf", io.BytesIO(f"%PDF-1.4 Content {i}".encode()), "application/pdf"))
            for i in range(3)
        ]

        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables/bulk", files=files, data={"extract_names": "false"}
        )
        assert response.status_code == status.HTTP_200_OK

        result = response.json()
        assert result["total_uploaded"] == 3
        assert len(result["deliverables"]) == 3

        for deliverable in result["deliverables"]:
            self.deliverable_ids.append(deliverable["id"])

        response = self.client.get(f"/assignments/{self.assignment_id}/deliverables")
        assert response.json()["total"] == 3

    @pytest.mark.parametrize(
        "mark,expected_status",
        [
            (0.0, status.HTTP_200_OK),
            (5.5, status.HTTP_200_OK),
            (10.0, status.HTTP_200_OK),
            (-0.1, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (10.1, status.HTTP_422_UNPROCESSABLE_CONTENT),
        ],
    )
    def test_deliverable_mark_validation(self, mark: float, expected_status: int) -> None:
        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"extract_name": "false"},
        )
        deliverable_id = response.json()["id"]
        self.deliverable_ids.append(deliverable_id)

        response = self.client.patch(f"/deliverables/{deliverable_id}", json={"mark": mark})
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "certainty,expected_status",
        [
            (0.0, status.HTTP_200_OK),
            (0.5, status.HTTP_200_OK),
            (1.0, status.HTTP_200_OK),
            (-0.01, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (1.01, status.HTTP_422_UNPROCESSABLE_CONTENT),
        ],
    )
    def test_deliverable_certainty_validation(self, certainty: float, expected_status: int) -> None:
        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"extract_name": "false"},
        )
        deliverable_id = response.json()["id"]
        self.deliverable_ids.append(deliverable_id)

        response = self.client.patch(f"/deliverables/{deliverable_id}", json={"certainty_threshold": certainty})
        assert response.status_code == expected_status

    def test_invalid_file_format_rejection(self) -> None:
        docx_content = b"PK\x03\x04 DOCX content"
        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables",
            files={
                "file": (
                    "document.docx",
                    io.BytesIO(docx_content),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"extract_name": "false"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "not supported" in response.json()["detail"]

    def test_partial_deliverable_updates(self) -> None:
        response = self.client.post(
            f"/assignments/{self.assignment_id}/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"extract_name": "false"},
        )
        deliverable_id = response.json()["id"]
        self.deliverable_ids.append(deliverable_id)

        response = self.client.patch(f"/deliverables/{deliverable_id}", json={"student_name": "Jane Smith"})
        assert response.status_code == status.HTTP_200_OK
        updated = response.json()
        assert updated["student_name"] == "Jane Smith"
        assert updated["mark"] is None

        response = self.client.patch(f"/deliverables/{deliverable_id}", json={"mark": 9.0})
        assert response.status_code == status.HTTP_200_OK
        updated = response.json()
        assert updated["student_name"] == "Jane Smith"
        assert updated["mark"] == 9.0

    def test_assignment_deletion_cascades_to_deliverables(self) -> None:
        response = self.client.post(
            "/assignments", json={"name": "Cascade Test Assignment", "confidence_threshold": 0.75}
        )
        assignment_id = response.json()["id"]

        deliverable_ids: list[str] = []
        for i in range(3):
            response = self.client.post(
                f"/assignments/{assignment_id}/deliverables",
                files={"file": (f"test{i}.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                data={"extract_name": "false"},
            )
            deliverable_ids.append(response.json()["id"])

        response = self.client.delete(f"/assignments/{assignment_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        for deliverable_id in deliverable_ids:
            response = self.client.get(f"/deliverables/{deliverable_id}/download")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deliverable_operations_on_nonexistent_assignment(self) -> None:
        fake_id = "60c72b2f9b1d8e2a1c9d4b7f"

        response = self.client.post(
            f"/assignments/{fake_id}/deliverables",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"extract_name": "false"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
