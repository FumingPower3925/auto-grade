import pytest
from src.repository.db.factory import get_database_repository
from src.repository.db.base import DatabaseRepository
from src.repository.db.models import DocumentModel


class TestFerretDBIntegration:
    """Integration tests for the FerretDB repository."""

    @pytest.fixture(scope="class")
    def repo(self) -> DatabaseRepository:
        """Fixture to provide a FerretDBRepository instance."""
        return get_database_repository()

    def test_database_health(self, repo: DatabaseRepository) -> None:
        """Test that the database is healthy."""
        assert repo.health() is True

    def test_store_and_retrieve_document(self, repo: DatabaseRepository) -> None:
        """Test storing and retrieving a document."""
        assignment = "test_assignment_integration"
        deliverable = "test_deliverable_integration"
        student_name = "test_student_integration"
        document = b"This is a test document."
        extension = "txt"

        doc_id = repo.store_document(assignment, deliverable, student_name, document, extension)
        assert isinstance(doc_id, str)

        retrieved_doc: DocumentModel | None = repo.get_document(doc_id)

        assert retrieved_doc is not None
        assert isinstance(retrieved_doc, DocumentModel)
        assert retrieved_doc.assignment == assignment
        assert retrieved_doc.deliverable == deliverable
        assert retrieved_doc.student_name == student_name
        assert retrieved_doc.document == document
        assert retrieved_doc.extension == extension

    def test_get_document_not_found(self, repo: DatabaseRepository) -> None:
        """Test retrieving a non-existent document."""
        # A 24-character hex string that is unlikely to exist
        non_existent_id = "0123456789abcdef01234567"
        retrieved_doc = repo.get_document(non_existent_id)
        assert retrieved_doc is None