import asyncio
import logging
from typing import Any

from src.repository.db.factory import get_database_repository
from src.repository.db.models import AssignmentModel, ChunkModel, FileModel, ProcessingStatus
from src.service.rubric_service import RubricService

logger = logging.getLogger(__name__)


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

        return self.db_repository.store_file(assignment_id, filename, content, content_type, "rubric", extracted_rubric)

    def upload_relevant_document(self, assignment_id: str, filename: str, content: bytes, content_type: str) -> str:
        """Upload a relevant document and start background processing.

        Args:
            assignment_id: The ID of the assignment.
            filename: The name of the file.
            content: The file content as bytes.
            content_type: The MIME type of the file.

        Returns:
            The ID of the uploaded file (processing continues in background).
        """
        assignment = self.db_repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment with ID {assignment_id} not found")

        # Initial storage with QUEUED status
        file_id = self.db_repository.store_file(
            assignment_id, filename, content, content_type, "relevant_document", extracted_text=None, embedding=None
        )

        # Start background processing - store task to prevent GC
        _ = asyncio.create_task(self._process_document_background(file_id, content, content_type))

        return file_id

    async def _process_document_background(self, file_id: str, content: bytes, content_type: str) -> None:
        """Background task to process document: extract text, chunk, and embed."""
        try:
            # Update status to PROCESSING
            self.db_repository.update_file(file_id, status=ProcessingStatus.PROCESSING, progress=10.0)

            from src.service.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()

            # 1. Extract Text
            extracted_text = await embedding_service.extract_text_from_content(content, content_type)
            if not extracted_text:
                raise ValueError("Failed to extract text from document")

            self.db_repository.update_file(file_id, extracted_text=extracted_text, progress=30.0)

            # 2. Chunk Text
            chunks_text = await asyncio.to_thread(embedding_service.chunk_text, extracted_text)
            self.db_repository.update_file(file_id, chunk_count=len(chunks_text), progress=40.0)

            # 3. Generate Embeddings (Parallel)
            # a. Document level summary embedding (using truncated text)
            doc_embedding_task = asyncio.to_thread(embedding_service.generate_embedding, extracted_text)

            # b. Chunk embeddings
            chunk_tasks = []
            for chunk_text in chunks_text:
                chunk_tasks.append(asyncio.to_thread(embedding_service.generate_embedding, chunk_text))

            # Use gather for concurrency
            # chunks might be many, so semaphore might be needed
            # but for now assuming API limits handled by retry or high limit
            logger.info(f"Generating embeddings for {len(chunk_tasks)} chunks...")
            results = await asyncio.gather(doc_embedding_task, *chunk_tasks)

            doc_embedding = results[0]
            chunk_embeddings = results[1:]

            # Construct ChunkModels
            chunks = []
            for i, (text, emb) in enumerate(zip(chunks_text, chunk_embeddings, strict=False)):
                chunks.append(ChunkModel(text=text, embedding=emb, metadata={"index": i}))

            # 4. Final Update
            self.db_repository.update_file(
                file_id,
                embedding=doc_embedding,
                chunks=chunks,
                status=ProcessingStatus.COMPLETED,
                progress=100.0,
                error_message=None,
            )
            logger.info(f"Document {file_id} processed successfully with {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Failed to process document {file_id}: {e}")
            self.db_repository.update_file(file_id, status=ProcessingStatus.FAILED, error_message=str(e), progress=0.0)

    def get_documents_status(self, assignment_id: str) -> list[FileModel]:
        """Get the status of all relevant documents for an assignment."""
        return self.db_repository.list_files_by_assignment(assignment_id, "relevant_document")

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

    def search_similar_documents(self, query: str, assignment_id: str | None = None, k: int = 5) -> list[FileModel]:
        """Search for similar documents using semantic search.

        Args:
            query: The text query to search for.
            assignment_id: Optional filter by assignment ID.
            k: Number of results to return.

        Returns:
            A list of similar documents sorted by relevance.
        """
        try:
            from src.service.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            query_embedding = embedding_service.generate_embedding(query)
            return self.db_repository.vector_search(query_embedding, assignment_id, k)
        except Exception:
            return []

    def ensure_vector_index(self) -> bool:
        """Ensure vector index exists for semantic search.

        Returns:
            True if index exists or was created successfully.
        """
        from config.config import get_config

        dimensions = get_config().embedding.dimensions
        return self.db_repository.create_vector_index(dimensions)

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
