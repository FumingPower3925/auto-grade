from typing import Any

from src.repository.db.factory import get_database_repository
from src.repository.db.models import AssignmentModel, FileModel
from src.service.rubric_service import RubricService


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

    def get_assignment(self, assignment_id: str) -> AssignmentModel | None:
        """Get an assignment by ID.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            The assignment model if found, otherwise None.
        """
        return self.db_repository.get_assignment(assignment_id)

    def list_assignments(self) -> list[AssignmentModel]:
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

    async def upload_rubric(self, assignment_id: str, filename: str, content: bytes, content_type: str) -> str:
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

        rubric_service = RubricService()
        extracted_rubric = await rubric_service.parse_rubric(content, content_type)

        return self.db_repository.store_file(
            assignment_id, filename, content, content_type, "rubric", extracted_rubric
        )

    def upload_relevant_document(self, assignment_id: str, filename: str, content: bytes, content_type: str) -> str:
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

        return self.db_repository.store_file(assignment_id, filename, content, content_type, "relevant_document")

    def get_file(self, file_id: str) -> FileModel | None:
        """Get a file by ID.

        Args:
            file_id: The ID of the file.

        Returns:
            The file model if found, otherwise None.
        """
        return self.db_repository.get_file(file_id)

    def list_rubrics(self, assignment_id: str) -> list[FileModel]:
        """List evaluation rubrics for an assignment.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            A list of rubric files.
        """
        return self.db_repository.list_files_by_assignment(assignment_id, "rubric")

    def list_relevant_documents(self, assignment_id: str) -> list[FileModel]:
        """List relevant documents for an assignment.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            A list of relevant document files.
        """
        return self.db_repository.list_files_by_assignment(assignment_id, "relevant_document")

    def update_rubric(
        self,
        rubric_id: str,
        title: str | None = None,
        total_points: float | None = None,
        criteria: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Update an evaluation rubric's extracted data.

        Args:
            rubric_id: The ID of the rubric file to update.
            title: Optional new title.
            total_points: Optional new total points.
            criteria: Optional new list of criteria.

        Returns:
            True if the rubric was updated, False otherwise.
        """
        file = self.db_repository.get_file(rubric_id)
        if not file or file.file_type != "rubric":
            raise ValueError(f"Rubric with ID {rubric_id} not found")

        from src.repository.db.models import ExtractedRubricModel

        existing = file.extracted_rubric

        new_title = self._resolve_value(title, existing.title if existing else None)
        new_total = self._resolve_value(total_points, existing.total_points if existing else None)
        raw_text = existing.raw_text if existing else None

        new_criteria = self._build_criteria(criteria, existing)

        extracted_rubric = ExtractedRubricModel(
            title=new_title,
            total_points=new_total,
            criteria=new_criteria,
            raw_text=raw_text,
        )

        return self.db_repository.update_file(rubric_id, extracted_rubric=extracted_rubric)

    def _resolve_value(self, new_value: Any, existing_value: Any) -> Any:
        """Return new_value if not None, otherwise existing_value."""
        if new_value is not None:
            return new_value
        return existing_value

    def _build_criteria(
        self,
        criteria: list[dict[str, Any]] | None,
        existing: Any,
    ) -> list[Any]:
        """Build criteria list from input or existing data."""

        if criteria is None:
            return existing.criteria if existing else []

        new_criteria = []
        for c in criteria:
            grades = self._build_grades(c.get("grades", []))
            criterion = self._build_criterion(c, grades)
            new_criteria.append(criterion)

        return new_criteria

    def _build_grades(self, grades_data: list[dict[str, Any]]) -> list[Any]:
        """Build grade levels from input data."""
        from src.repository.db.models import GradeLevel

        grades = []
        for g in grades_data:
            grades.append(
                GradeLevel(
                    label=str(g.get("label", "Unnamed")),
                    points=float(g.get("points", 0)),
                    description=str(g.get("description", "")),
                )
            )
        return grades

    def _build_criterion(self, c: dict[str, Any], grades: list[Any]) -> Any:
        """Build a single criterion from input data."""
        from src.repository.db.models import RubricCriterionModel

        max_pts = c.get("max_points", 0)
        weight_val = c.get("weight")

        return RubricCriterionModel(
            name=str(c.get("name", "Unnamed")),
            max_points=float(max_pts) if max_pts is not None else 0.0,
            weight=float(weight_val) if weight_val is not None else None,
            grades=grades,
        )

