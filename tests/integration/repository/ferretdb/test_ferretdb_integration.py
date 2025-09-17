import pytest

from src.repository.db.factory import get_database_repository
from src.repository.db.base import DatabaseRepository
from src.repository.db.models import DocumentModel


class TestFerretDBIntegration:

    @pytest.fixture(scope="class")
    def repo(self) -> DatabaseRepository:
        return get_database_repository()

    def test_database_connectivity(self, repo: DatabaseRepository) -> None:
        assert repo.health() is True

    def test_document_storage_and_retrieval(self, repo: DatabaseRepository) -> None:
        doc_id = repo.store_document(
            assignment="test_assignment",
            deliverable="test_deliverable",
            student_name="Test Student",
            document=b"Test document content",
            extension="pdf"
        )
        
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        
        document = repo.get_document(doc_id)
        assert document is not None
        assert isinstance(document, DocumentModel)
        assert document.assignment == "test_assignment"
        assert document.deliverable == "test_deliverable"
        assert document.student_name == "Test Student"
        assert document.document == b"Test document content"
        assert document.extension == "pdf"

    def test_document_not_found(self, repo: DatabaseRepository) -> None:
        non_existent_id = "507f1f77bcf86cd799439011"
        document = repo.get_document(non_existent_id)
        assert document is None

    def test_multiple_document_operations(self, repo: DatabaseRepository) -> None:
        doc_ids: list[str] = []
        
        for i in range(5):
            doc_id = repo.store_document(
                assignment=f"assignment_{i}",
                deliverable=f"deliverable_{i}",
                student_name=f"Student {i}",
                document=f"Content {i}".encode(),
                extension="txt"
            )
            doc_ids.append(doc_id)
        
        for i, doc_id in enumerate(doc_ids):
            document = repo.get_document(doc_id)
            assert document is not None
            assert document.assignment == f"assignment_{i}"
            assert document.student_name == f"Student {i}"

    def test_document_with_binary_content(self, repo: DatabaseRepository) -> None:
        binary_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        
        doc_id = repo.store_document(
            assignment="binary_test",
            deliverable="binary_deliverable",
            student_name="Binary Test",
            document=binary_content,
            extension="pdf"
        )
        
        document = repo.get_document(doc_id)
        assert document is not None
        assert document.document == binary_content
        assert document.extension == "pdf"

    def test_document_with_special_characters(self, repo: DatabaseRepository) -> None:
        doc_id = repo.store_document(
            assignment="Test & Assignment",
            deliverable="Test's Deliverable",
            student_name="João São Paulo",
            document=b"Content with special chars: \xe2\x98\x85",
            extension="txt"
        )
        
        document = repo.get_document(doc_id)
        assert document is not None
        assert document.assignment == "Test & Assignment"
        assert document.deliverable == "Test's Deliverable"
        assert document.student_name == "João São Paulo"

    def test_large_document_handling(self, repo: DatabaseRepository) -> None:
        large_content = b"x" * (1024 * 1024)
        
        doc_id = repo.store_document(
            assignment="large_test",
            deliverable="large_deliverable",
            student_name="Large Test",
            document=large_content,
            extension="bin"
        )
        
        document = repo.get_document(doc_id)
        assert document is not None
        assert len(document.document) == 1024 * 1024
        assert document.document == large_content