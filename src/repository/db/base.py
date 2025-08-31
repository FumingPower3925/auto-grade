from abc import ABC, abstractmethod
from typing import Optional, List, Any
from src.repository.db.models import DocumentModel, AssignmentModel, FileModel


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

    @abstractmethod
    def create_assignment(self, name: str, confidence_threshold: float) -> str:
        """Create a new assignment.

        Args:
            name: The name of the assignment.
            confidence_threshold: The confidence threshold for the assignment.

        Returns:
            The ID of the created assignment.
        """
        raise NotImplementedError

    @abstractmethod
    def get_assignment(self, assignment_id: str) -> Optional[AssignmentModel]:
        """Retrieve an assignment by its ID.

        Args:
            assignment_id: The ID of the assignment to retrieve.

        Returns:
            The assignment model if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def list_assignments(self) -> List[AssignmentModel]:
        """List all assignments.

        Returns:
            A list of all assignments.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete an assignment by its ID.

        Args:
            assignment_id: The ID of the assignment to delete.

        Returns:
            True if the assignment was deleted, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def update_assignment(self, assignment_id: str, **kwargs: Any) -> bool:
        """Update an assignment.

        Args:
            assignment_id: The ID of the assignment to update.
            **kwargs: Fields to update.

        Returns:
            True if the assignment was updated, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def store_file(self, assignment_id: str, filename: str, content: bytes, 
                   content_type: str, file_type: str) -> str:
        """Store a file related to an assignment.

        Args:
            assignment_id: The ID of the assignment.
            filename: The name of the file.
            content: The file content as bytes.
            content_type: The MIME type of the file.
            file_type: The type of file ("rubric" or "relevant_document").

        Returns:
            The ID of the stored file.
        """
        raise NotImplementedError

    @abstractmethod
    def get_file(self, file_id: str) -> Optional[FileModel]:
        """Retrieve a file by its ID.

        Args:
            file_id: The ID of the file to retrieve.

        Returns:
            The file model if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def list_files_by_assignment(self, assignment_id: str, file_type: Optional[str] = None) -> List[FileModel]:
        """List files for an assignment.

        Args:
            assignment_id: The ID of the assignment.
            file_type: Optional filter by file type.

        Returns:
            A list of files for the assignment.
        """
        raise NotImplementedError