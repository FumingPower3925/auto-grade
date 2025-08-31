import pytest
from typing import List
from src.repository.db.factory import get_database_repository
from src.repository.db.base import DatabaseRepository
from src.repository.db.models import AssignmentModel, FileModel


class TestAssignmentRepositoryIntegration:
    """Integration tests for assignment-related repository operations."""

    @pytest.fixture(scope="class")
    def repo(self) -> DatabaseRepository:
        """Fixture to provide a database repository instance."""
        return get_database_repository()

    @pytest.fixture
    def cleanup_assignments(self, repo: DatabaseRepository):
        """Fixture to clean up test assignments after each test."""
        created_ids: List[str] = []
        
        yield created_ids
        
        for assignment_id in created_ids:
            try:
                repo.delete_assignment(assignment_id)
            except Exception:
                pass

    def test_create_and_retrieve_assignment(self, repo: DatabaseRepository, cleanup_assignments: List[str]) -> None:
        """Test creating and retrieving an assignment."""
        assignment_id = repo.create_assignment(
            name="Integration Test Assignment",
            confidence_threshold=0.85
        )
        cleanup_assignments.append(assignment_id)
        
        assert isinstance(assignment_id, str)
        assert len(assignment_id) > 0
        
        assignment = repo.get_assignment(assignment_id)
        
        assert assignment is not None
        assert isinstance(assignment, AssignmentModel)
        assert assignment.name == "Integration Test Assignment"
        assert assignment.confidence_threshold == 0.85
        assert assignment.deliverables == []
        assert assignment.evaluation_rubrics == []
        assert assignment.relevant_documents == []

    def test_list_assignments_integration(self, repo: DatabaseRepository, cleanup_assignments: List[str]) -> None:
        """Test listing assignments."""
        id1 = repo.create_assignment("List Test 1", 0.70)
        cleanup_assignments.append(id1)
        
        id2 = repo.create_assignment("List Test 2", 0.80)
        cleanup_assignments.append(id2)
        
        id3 = repo.create_assignment("List Test 3", 0.90)
        cleanup_assignments.append(id3)
        
        assignments = repo.list_assignments()
        
        assert isinstance(assignments, list)
        assert len(assignments) >= 3
        
        assignment_names = [a.name for a in assignments]
        assert "List Test 1" in assignment_names
        assert "List Test 2" in assignment_names
        assert "List Test 3" in assignment_names

    def test_update_assignment_integration(self, repo: DatabaseRepository, cleanup_assignments: List[str]) -> None:
        """Test updating an assignment."""
        assignment_id = repo.create_assignment(
            name="Original Name",
            confidence_threshold=0.50
        )
        cleanup_assignments.append(assignment_id)
        
        success = repo.update_assignment(
            assignment_id,
            name="Updated Name",
            confidence_threshold=0.95
        )
        
        assert success is True
        
        updated = repo.get_assignment(assignment_id)
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.confidence_threshold == 0.95

    def test_delete_assignment_integration(self, repo: DatabaseRepository) -> None:
        """Test deleting an assignment."""
        assignment_id = repo.create_assignment(
            name="Delete Test Assignment",
            confidence_threshold=0.75
        )
        
        assignment = repo.get_assignment(assignment_id)
        assert assignment is not None
        
        success = repo.delete_assignment(assignment_id)
        assert success is True
        
        deleted = repo.get_assignment(assignment_id)
        assert deleted is None
        
        success = repo.delete_assignment(assignment_id)
        assert success is False

    def test_store_and_retrieve_file_integration(self, repo: DatabaseRepository, cleanup_assignments: List[str]) -> None:
        """Test storing and retrieving files."""
        assignment_id = repo.create_assignment(
            name="File Test Assignment",
            confidence_threshold=0.80
        )
        cleanup_assignments.append(assignment_id)
        
        rubric_id = repo.store_file(
            assignment_id=assignment_id,
            filename="test_rubric.pdf",
            content=b"This is a test rubric content",
            content_type="application/pdf",
            file_type="rubric"
        )
        
        assert isinstance(rubric_id, str)
        assert len(rubric_id) > 0
        
        doc_id = repo.store_file(
            assignment_id=assignment_id,
            filename="example.docx",
            content=b"This is an example document",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_type="relevant_document"
        )
        
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        
        rubric = repo.get_file(rubric_id)
        assert rubric is not None
        assert isinstance(rubric, FileModel)
        assert rubric.filename == "test_rubric.pdf"
        assert rubric.content == b"This is a test rubric content"
        assert rubric.file_type == "rubric"
        
        document = repo.get_file(doc_id)
        assert document is not None
        assert document.filename == "example.docx"
        assert document.file_type == "relevant_document"

    def test_list_files_by_assignment_integration(self, repo: DatabaseRepository, cleanup_assignments: List[str]) -> None:
        """Test listing files for an assignment."""
        assignment_id = repo.create_assignment(
            name="File List Test",
            confidence_threshold=0.70
        )
        cleanup_assignments.append(assignment_id)
        
        repo.store_file(
            assignment_id, "rubric1.pdf", b"content1", "application/pdf", "rubric"
        )
        repo.store_file(
            assignment_id, "rubric2.pdf", b"content2", "application/pdf", "rubric"
        )
        repo.store_file(
            assignment_id, "doc1.txt", b"doc content", "text/plain", "relevant_document"
        )
        
        all_files = repo.list_files_by_assignment(assignment_id)
        assert len(all_files) == 3
        
        rubrics = repo.list_files_by_assignment(assignment_id, "rubric")
        assert len(rubrics) == 2
        assert all(f.file_type == "rubric" for f in rubrics)
        
        documents = repo.list_files_by_assignment(assignment_id, "relevant_document")
        assert len(documents) == 1
        assert documents[0].file_type == "relevant_document"
        assert documents[0].filename == "doc1.txt"

    def test_assignment_with_files_deletion_integration(self, repo: DatabaseRepository) -> None:
        """Test that deleting an assignment also deletes its files."""
        assignment_id = repo.create_assignment(
            name="Delete with Files Test",
            confidence_threshold=0.85
        )
        
        file_id = repo.store_file(
            assignment_id, "test.pdf", b"content", "application/pdf", "rubric"
        )
        
        file_obj = repo.get_file(file_id)
        assert file_obj is not None
        
        success = repo.delete_assignment(assignment_id)
        assert success is True
        
        files = repo.list_files_by_assignment(assignment_id)
        assert len(files) == 0

    def test_assignment_not_found_operations(self, repo: DatabaseRepository) -> None:
        """Test operations on non-existent assignments."""
        fake_id = "60c72b2f9b1d8e2a1c9d4b7f"
        
        assignment = repo.get_assignment(fake_id)
        assert assignment is None
        
        success = repo.update_assignment(fake_id, name="New Name")
        assert success is False
        
        success = repo.delete_assignment(fake_id)
        assert success is False
        
        files = repo.list_files_by_assignment(fake_id)
        assert files == []

    def test_file_not_found_operations(self, repo: DatabaseRepository) -> None:
        """Test operations on non-existent files."""
        fake_id = "50c72b2f9b1d8e2a1c9d4b7f"
        
        file_obj = repo.get_file(fake_id)
        assert file_obj is None