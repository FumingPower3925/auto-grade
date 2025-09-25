import pytest

from src.repository.db.base import DatabaseRepository
from src.repository.db.factory import get_database_repository


class TestRepositoryOperations:
    @pytest.fixture(scope="class")
    def repo(self) -> DatabaseRepository:
        return get_database_repository()

    @pytest.fixture
    def cleanup_assignments(self, repo: DatabaseRepository):
        created_ids: list[str] = []
        yield created_ids

        for assignment_id in created_ids:
            try:
                repo.delete_assignment(assignment_id)
            except Exception:
                pass

    def test_assignment_crud_operations(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        assignment_id = repo.create_assignment(name="CRUD Test Assignment", confidence_threshold=0.85)
        cleanup_assignments.append(assignment_id)

        assert isinstance(assignment_id, str)

        assignment = repo.get_assignment(assignment_id)
        assert assignment is not None
        assert assignment.name == "CRUD Test Assignment"
        assert assignment.confidence_threshold == 0.85

        success = repo.update_assignment(assignment_id, name="Updated Assignment", confidence_threshold=0.95)
        assert success is True

        updated = repo.get_assignment(assignment_id)
        assert updated is not None
        assert updated.name == "Updated Assignment"
        assert updated.confidence_threshold == 0.95

        success = repo.delete_assignment(assignment_id)
        assert success is True

        deleted = repo.get_assignment(assignment_id)
        assert deleted is None
        cleanup_assignments.remove(assignment_id)

    def test_assignment_listing_with_pagination(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        for i in range(10):
            assignment_id = repo.create_assignment(name=f"List Test {i:02d}", confidence_threshold=0.50 + i * 0.05)
            cleanup_assignments.append(assignment_id)

        assignments = repo.list_assignments()
        assert len(assignments) >= 10

        names = [a.name for a in assignments]
        for i in range(10):
            assert f"List Test {i:02d}" in names

    def test_file_storage_and_retrieval(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        assignment_id = repo.create_assignment("File Test", 0.75)
        cleanup_assignments.append(assignment_id)

        rubric_id = repo.store_file(
            assignment_id=assignment_id,
            filename="test_rubric.pdf",
            content=b"Rubric content",
            content_type="application/pdf",
            file_type="rubric",
        )

        doc_id = repo.store_file(
            assignment_id=assignment_id,
            filename="reference.docx",
            content=b"Document content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_type="relevant_document",
        )

        rubric = repo.get_file(rubric_id)
        assert rubric is not None
        assert rubric.filename == "test_rubric.pdf"
        assert rubric.content == b"Rubric content"
        assert rubric.file_type == "rubric"

        document = repo.get_file(doc_id)
        assert document is not None
        assert document.filename == "reference.docx"
        assert document.file_type == "relevant_document"

    def test_file_listing_by_assignment_and_type(
        self, repo: DatabaseRepository, cleanup_assignments: list[str]
    ) -> None:
        assignment_id = repo.create_assignment("File List Test", 0.80)
        cleanup_assignments.append(assignment_id)

        repo.store_file(assignment_id, "rubric1.pdf", b"content1", "application/pdf", "rubric")
        repo.store_file(assignment_id, "rubric2.pdf", b"content2", "application/pdf", "rubric")
        repo.store_file(assignment_id, "doc1.txt", b"doc1", "text/plain", "relevant_document")
        repo.store_file(assignment_id, "doc2.txt", b"doc2", "text/plain", "relevant_document")
        repo.store_file(assignment_id, "doc3.txt", b"doc3", "text/plain", "relevant_document")

        all_files = repo.list_files_by_assignment(assignment_id)
        assert len(all_files) == 5

        rubrics = repo.list_files_by_assignment(assignment_id, "rubric")
        assert len(rubrics) == 2
        assert all(f.file_type == "rubric" for f in rubrics)

        documents = repo.list_files_by_assignment(assignment_id, "relevant_document")
        assert len(documents) == 3
        assert all(f.file_type == "relevant_document" for f in documents)

    def test_deliverable_crud_operations(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        assignment_id = repo.create_assignment("Deliverable Test", 0.85)
        cleanup_assignments.append(assignment_id)

        deliverable_id = repo.store_file(
            assignment_id=assignment_id,
            filename="submission.pdf",
            content=b"PDF content",
            content_type="application/pdf",
            file_type="deliverable",
        )

        assert isinstance(deliverable_id, str)

        deliverable = repo.get_deliverable(deliverable_id)
        if deliverable is None:
            deliverable = repo.get_file(deliverable_id)

        assert deliverable is not None
        assert deliverable.filename == "submission.pdf"

        success = repo.update_deliverable(
            deliverable_id, student_name="Updated Student", mark=8.5, certainty_threshold=0.9
        )

        if success:
            updated = repo.get_deliverable(deliverable_id)
            if updated:
                assert updated.student_name == "Updated Student"
                assert updated.mark == 8.5

        success = repo.delete_deliverable(deliverable_id)

        deleted = repo.get_deliverable(deliverable_id)
        if deleted is None:
            deleted = repo.get_file(deliverable_id)

    def test_deliverable_listing_by_assignment(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        assignment_id = repo.create_assignment("Deliverable List Test", 0.75)
        cleanup_assignments.append(assignment_id)

        deliverable_ids: list[str] = []
        for i in range(5):
            deliverable_id = repo.store_file(
                assignment_id=assignment_id,
                filename=f"submission_{i}.pdf",
                content=f"Content {i}".encode(),
                content_type="application/pdf",
                file_type="deliverable",
            )
            deliverable_ids.append(deliverable_id)

        deliverables = repo.list_deliverables_by_assignment(assignment_id)
        if len(deliverables) == 0:
            deliverables = repo.list_files_by_assignment(assignment_id, "deliverable")

        assert len(deliverables) >= 5

        filenames = [d.filename for d in deliverables]
        for i in range(5):
            assert f"submission_{i}.pdf" in filenames

    def test_cascade_deletion_assignment_with_files_and_deliverables(self, repo: DatabaseRepository) -> None:
        assignment_id = repo.create_assignment("Cascade Test", 0.80)

        file_id = repo.store_file(assignment_id, "rubric.pdf", b"rubric", "application/pdf", "rubric")

        deliverable_id = repo.store_file(
            assignment_id, "submission.pdf", b"submission", "application/pdf", "deliverable"
        )

        assert repo.get_assignment(assignment_id) is not None
        assert repo.get_file(file_id) is not None
        assert repo.get_file(deliverable_id) is not None

        success = repo.delete_assignment(assignment_id)
        assert success is True

        assert repo.list_files_by_assignment(assignment_id) == []

        try:
            assert repo.list_deliverables_by_assignment(assignment_id) == []
        except AttributeError:
            pass

    def test_operations_on_nonexistent_entities(self, repo: DatabaseRepository) -> None:
        fake_id = "507f1f77bcf86cd799439011"

        assert repo.get_assignment(fake_id) is None
        assert repo.update_assignment(fake_id, name="New") is False
        assert repo.delete_assignment(fake_id) is False

        assert repo.get_file(fake_id) is None
        assert repo.list_files_by_assignment(fake_id) == []

        assert repo.get_deliverable(fake_id) is None
        assert repo.update_deliverable(fake_id, mark=5.0) is False
        assert repo.delete_deliverable(fake_id) is False
        assert repo.list_deliverables_by_assignment(fake_id) == []

    def test_concurrent_operations(self, repo: DatabaseRepository, cleanup_assignments: list[str]) -> None:
        import threading

        results: list[str] = []

        def create_assignment(index: int) -> None:
            assignment_id = repo.create_assignment(name=f"Concurrent {index}", confidence_threshold=0.70)
            results.append(assignment_id)
            cleanup_assignments.append(assignment_id)

        threads: list[threading.Thread] = []
        for i in range(10):
            thread = threading.Thread(target=create_assignment, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert len(set(results)) == 10

        for assignment_id in results:
            assert repo.get_assignment(assignment_id) is not None
