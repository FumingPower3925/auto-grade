from abc import ABC, abstractmethod
from typing import Optional
from src.repository.db.models import DocumentModel


class DatabaseRepository(ABC):
    """Abstract base class for database repositories."""

    @abstractmethod
    def health(self) -> bool:
        """Check the health of the database connection."""
        raise NotImplementedError

    @abstractmethod
    def store_document(self, assignment: str, deliverable: str, student_name: str, document: bytes, extension: str) -> str:
        """Store a document in the database.

        Args:
            assignment: The assignment name.
            deliverable: The deliverable content.
            student_name: The name of the student.
            document: The document content as bytes.
            extension: The file extension of the document.

        Returns:
            The ID of the stored document.
        """
        raise NotImplementedError

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Retrieve a document from the database by its ID.

        Args:
            document_id: The ID of the document to retrieve.

        Returns:
            The document model if found, otherwise None.
        """
        raise NotImplementedError