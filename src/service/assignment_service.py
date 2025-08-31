from typing import List, Optional
from src.repository.db.factory import get_database_repository
from src.repository.db.models import AssignmentModel, FileModel


class AssignmentService:
    """Service for handling assignment operations."""

    def __init__(self) -> None:
        self.db_repository = get_database_repository()

    def create_assignment(self, name: str, confidence_threshold: float) -> str:
        """Create a new assignment.

        Args:
            name: The name of the assignment.
            confidence_threshold: The confidence threshold for the assignment.

        Returns:
            The ID of the created assignment.
        """
        if not name or len(name) > 255:
            raise ValueError("Assignment name must be between 1 and 255 characters")
        
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        
        return self.db_repository.create_assignment(name, confidence_threshold)

    def get_assignment(self, assignment_id: str) -> Optional[AssignmentModel]:
        """Get an assignment by ID.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            The assignment model if found, otherwise None.
        """
        return self.db_repository.get_assignment(assignment_id)

    def list_assignments(self) -> List[AssignmentModel]:
        """List all assignments.

        Returns:
            A list of all assignments.
        """
        return self.db_repository.list_assignments()

    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete an assignment.

        Args:
            assignment_id: The ID of the assignment to delete.

        Returns:
            True if the assignment was deleted, False otherwise.
        """
        return self.db_repository.delete_assignment(assignment_id)

    def upload_rubric(self, assignment_id: str, filename: str, content: bytes, 
                     content_type: str) -> str:
        """Upload an evaluation rubric for an assignment.

        Args:
            assignment_id: The ID of the assignment.
            filename: The name of the file.
            content: The file content as bytes.
            content_type: The MIME type of the file.

        Returns:
            The ID of the uploaded file.
        """
        assignment = self.db_repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment with ID {assignment_id} not found")
        
        return self.db_repository.store_file(
            assignment_id, filename, content, content_type, "rubric"
        )

    def upload_relevant_document(self, assignment_id: str, filename: str, 
                                content: bytes, content_type: str) -> str:
        """Upload a relevant document or example for an assignment.

        Args:
            assignment_id: The ID of the assignment.
            filename: The name of the file.
            content: The file content as bytes.
            content_type: The MIME type of the file.

        Returns:
            The ID of the uploaded file.
        """
        assignment = self.db_repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment with ID {assignment_id} not found")
        
        return self.db_repository.store_file(
            assignment_id, filename, content, content_type, "relevant_document"
        )

    def get_file(self, file_id: str) -> Optional[FileModel]:
        """Get a file by ID.

        Args:
            file_id: The ID of the file.

        Returns:
            The file model if found, otherwise None.
        """
        return self.db_repository.get_file(file_id)

    def list_rubrics(self, assignment_id: str) -> List[FileModel]:
        """List evaluation rubrics for an assignment.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            A list of rubric files.
        """
        return self.db_repository.list_files_by_assignment(assignment_id, "rubric")

    def list_relevant_documents(self, assignment_id: str) -> List[FileModel]:
        """List relevant documents for an assignment.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            A list of relevant document files.
        """
        return self.db_repository.list_files_by_assignment(assignment_id, "relevant_document")