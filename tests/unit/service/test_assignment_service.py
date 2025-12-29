from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from src.repository.db.models import AssignmentModel, ExtractedRubricModel, FileModel
from src.service.assignment_service import AssignmentService


class TestAssignmentService:
    """Tests for AssignmentService."""

    @patch("src.service.assignment_service.get_database_repository")
    def test_create_assignment_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful assignment creation."""
        mock_repo = MagicMock()
        mock_repo.create_assignment.return_value = "test_id_123"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        assignment_id = service.create_assignment("Test Assignment", 0.75)

        assert assignment_id == "test_id_123"
        mock_repo.create_assignment.assert_called_once_with("Test Assignment", 0.75)

    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.parametrize(
        "name,error_msg",
        [
            ("", "Assignment name must be between 1 and 255 characters"),
            ("a" * 256, "Assignment name must be between 1 and 255 characters"),
        ],
    )
    def test_create_assignment_invalid_name(self, mock_get_repo: MagicMock, name: str, error_msg: str) -> None:
        """Test assignment creation with invalid name."""
        service = AssignmentService()

        with pytest.raises(ValueError, match=error_msg):
            service.create_assignment(name, 0.75)

    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.parametrize(
        "threshold,error_msg",
        [
            (-0.1, "Confidence threshold must be between 0.0 and 1.0"),
            (1.1, "Confidence threshold must be between 0.0 and 1.0"),
        ],
    )
    def test_create_assignment_invalid_threshold(
        self, mock_get_repo: MagicMock, threshold: float, error_msg: str
    ) -> None:
        """Test assignment creation with invalid threshold."""
        service = AssignmentService()

        with pytest.raises(ValueError, match=error_msg):
            service.create_assignment("Test", threshold)

    @patch("src.service.assignment_service.get_database_repository")
    def test_get_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test getting an assignment."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_assignment("test_id")

        assert result == mock_assignment
        mock_repo.get_assignment.assert_called_once_with("test_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_assignments(self, mock_get_repo: MagicMock) -> None:
        """Test listing assignments."""
        mock_repo = MagicMock()
        mock_assignments = [self._create_mock_assignment("Assignment 1"), self._create_mock_assignment("Assignment 2")]
        mock_repo.list_assignments.return_value = mock_assignments
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_assignments()

        assert result == mock_assignments
        assert len(result) == 2
        mock_repo.list_assignments.assert_called_once()

    @patch("src.service.assignment_service.get_database_repository")
    def test_delete_assignment(self, mock_get_repo: MagicMock) -> None:
        """Test deleting an assignment."""
        mock_repo = MagicMock()
        mock_repo.delete_assignment.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.delete_assignment("test_id")

        assert result is True
        mock_repo.delete_assignment.assert_called_once_with("test_id")

    @patch("src.service.assignment_service.RubricService")
    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.asyncio
    async def test_upload_rubric_success(self, mock_get_repo: MagicMock, mock_rubric_service: MagicMock) -> None:
        """Test successful rubric upload."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_123"
        mock_get_repo.return_value = mock_repo

        mock_extracted_rubric = ExtractedRubricModel(title="Test Rubric", total_points=100, criteria=[])
        mock_rubric_service_instance = MagicMock()
        # Make parse_rubric awaitable
        mock_rubric_service_instance.parse_rubric = AsyncMock(return_value=mock_extracted_rubric)
        mock_rubric_service.return_value = mock_rubric_service_instance

        service = AssignmentService()
        file_id = await service.upload_rubric("assignment_id", "rubric.pdf", b"content", "application/pdf")

        assert file_id == "file_id_123"
        mock_rubric_service_instance.parse_rubric.assert_called_once_with(b"content", "application/pdf")
        mock_repo.store_file.assert_called_once_with(
            "assignment_id", "rubric.pdf", b"content", "application/pdf", "rubric", mock_extracted_rubric
        )

    @patch("src.service.assignment_service.get_database_repository")
    @pytest.mark.asyncio
    async def test_upload_rubric_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test rubric upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            await service.upload_rubric("test_id", "rubric.pdf", b"content", "application/pdf")

    @pytest.mark.asyncio
    @patch("src.service.assignment_service.get_database_repository")
    async def test_upload_relevant_document_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful relevant document upload."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_456"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        # Mock EmbeddingService at its source module since it's imported locally
        with patch("src.service.embedding_service.EmbeddingService") as mock_embedding:
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.extract_text_from_content.return_value = "extracted text"
            mock_embedding_instance.generate_embedding.return_value = [0.1] * 1536
            mock_embedding.return_value = mock_embedding_instance

            file_id = await service.upload_relevant_document(
                "assignment_id",
                "example.docx",
                b"content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        assert file_id == "file_id_456"
        mock_repo.store_file.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.service.assignment_service.get_database_repository")
    async def test_upload_relevant_document_assignment_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test document upload when assignment doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_assignment.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Assignment with ID test_id not found"):
            await service.upload_relevant_document("test_id", "doc.pdf", b"content", "application/pdf")

    @patch("src.service.assignment_service.get_database_repository")
    def test_get_file(self, mock_get_repo: MagicMock) -> None:
        """Test getting a file."""
        mock_repo = MagicMock()
        mock_file = self._create_mock_file()
        mock_repo.get_file.return_value = mock_file
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.get_file("file_id")

        assert result == mock_file
        mock_repo.get_file.assert_called_once_with("file_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_rubrics(self, mock_get_repo: MagicMock) -> None:
        """Test listing rubrics."""
        mock_repo = MagicMock()
        mock_files = [self._create_mock_file("rubric1.pdf"), self._create_mock_file("rubric2.pdf")]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_rubrics("assignment_id")

        assert result == mock_files
        assert len(result) == 2
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "rubric")

    @patch("src.service.assignment_service.get_database_repository")
    def test_list_relevant_documents(self, mock_get_repo: MagicMock) -> None:
        """Test listing relevant documents."""
        mock_repo = MagicMock()
        mock_files = [self._create_mock_file("example.docx")]
        mock_repo.list_files_by_assignment.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.list_relevant_documents("assignment_id")

        assert result == mock_files
        assert len(result) == 1
        mock_repo.list_files_by_assignment.assert_called_once_with("assignment_id", "relevant_document")

    @pytest.mark.asyncio
    @patch("src.service.assignment_service.get_database_repository")
    async def test_upload_relevant_document_embedding_fails(self, mock_get_repo: MagicMock) -> None:
        """Test document upload continues when embedding fails."""
        mock_repo = MagicMock()
        mock_assignment = self._create_mock_assignment()
        mock_repo.get_assignment.return_value = mock_assignment
        mock_repo.store_file.return_value = "file_id_456"
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        # Mock EmbeddingService to raise an exception
        with patch("src.service.embedding_service.EmbeddingService") as mock_embedding:
            mock_embedding.side_effect = Exception("API key missing")

            file_id = await service.upload_relevant_document(
                "assignment_id",
                "example.docx",
                b"content",
                "application/pdf",
            )

        assert file_id == "file_id_456"
        mock_repo.store_file.assert_called_once()

    @patch("src.service.assignment_service.get_database_repository")
    def test_search_similar_documents_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful semantic search."""
        mock_repo = MagicMock()
        mock_files = [self._create_mock_file("similar.pdf")]
        mock_repo.vector_search.return_value = mock_files
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        with patch("src.service.embedding_service.EmbeddingService") as mock_embedding:
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.generate_embedding.return_value = [0.1] * 1536
            mock_embedding.return_value = mock_embedding_instance

            result = service.search_similar_documents("test query")

        assert result == mock_files

    @patch("src.service.assignment_service.get_database_repository")
    def test_search_similar_documents_error(self, mock_get_repo: MagicMock) -> None:
        """Test semantic search handles errors gracefully."""
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        with patch("src.service.embedding_service.EmbeddingService") as mock_embedding:
            mock_embedding.side_effect = Exception("API error")

            result = service.search_similar_documents("test query")

        assert result == []

    @patch("src.service.assignment_service.get_database_repository")
    def test_ensure_vector_index(self, mock_get_repo: MagicMock) -> None:
        """Test ensuring vector index exists."""
        mock_repo = MagicMock()
        mock_repo.create_vector_index.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        with patch("config.config.get_config") as mock_config:
            mock_config.return_value.embedding.dimensions = 1536

            result = service.ensure_vector_index()

        assert result is True
        mock_repo.create_vector_index.assert_called_once_with(1536)

    def _create_mock_assignment(self, name: str = "Test Assignment") -> AssignmentModel:
        """Create a mock AssignmentModel."""
        return AssignmentModel(
            _id=ObjectId(),
            name=name,
            confidence_threshold=0.75,
            deliverables=[],
            evaluation_rubrics=[],
            relevant_documents=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def _create_mock_file(self, filename: str = "test.pdf") -> FileModel:
        """Create a mock FileModel."""
        return FileModel(
            _id=ObjectId(),
            assignment_id=ObjectId(),
            filename=filename,
            content=b"content",
            content_type="application/pdf",
            file_type="rubric",
            uploaded_at=datetime.now(UTC),
        )

    @patch("src.service.assignment_service.get_database_repository")
    def test_update_rubric_success(self, mock_get_repo: MagicMock) -> None:
        """Test successful rubric update."""
        mock_repo = MagicMock()
        rubric_file = self._create_mock_file("rubric.pdf")
        rubric_file.extracted_rubric = ExtractedRubricModel(
            title="Old Title", total_points=50, criteria=[], raw_text="raw"
        )
        mock_repo.get_file.return_value = rubric_file
        mock_repo.update_file.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.update_rubric(
            rubric_id=str(rubric_file.id),
            title="New Title",
            total_points=100,
        )

        assert result is True
        mock_repo.update_file.assert_called_once()

    @patch("src.service.assignment_service.get_database_repository")
    def test_update_rubric_not_found(self, mock_get_repo: MagicMock) -> None:
        """Test update_rubric when rubric not found."""
        mock_repo = MagicMock()
        mock_repo.get_file.return_value = None
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Rubric with ID .* not found"):
            service.update_rubric("nonexistent_id")

    @patch("src.service.assignment_service.get_database_repository")
    def test_update_rubric_wrong_file_type(self, mock_get_repo: MagicMock) -> None:
        """Test update_rubric when file is not a rubric."""
        mock_repo = MagicMock()
        doc_file = self._create_mock_file("document.pdf")
        doc_file.file_type = "relevant_document"
        mock_repo.get_file.return_value = doc_file
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()

        with pytest.raises(ValueError, match="Rubric with ID .* not found"):
            service.update_rubric(str(doc_file.id))

    @patch("src.service.assignment_service.get_database_repository")
    def test_update_rubric_with_criteria(self, mock_get_repo: MagicMock) -> None:
        """Test update_rubric with new criteria."""
        mock_repo = MagicMock()
        rubric_file = self._create_mock_file("rubric.pdf")
        rubric_file.extracted_rubric = None
        mock_repo.get_file.return_value = rubric_file
        mock_repo.update_file.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.update_rubric(
            rubric_id=str(rubric_file.id),
            title="Test",
            total_points=100,
            criteria=[
                {
                    "name": "Quality",
                    "max_points": 50,
                    "weight": 0.5,
                    "grades": [
                        {"label": "Excellent", "points": 50, "description": "Outstanding"},
                        {"label": "Good", "points": 40, "description": "Good work"},
                    ],
                },
                {"name": "Style", "max_points": 50, "weight": None, "grades": []},
            ],
        )

        assert result is True
        call_kwargs = mock_repo.update_file.call_args[1]
        assert call_kwargs["extracted_rubric"].title == "Test"
        assert len(call_kwargs["extracted_rubric"].criteria) == 2
        assert len(call_kwargs["extracted_rubric"].criteria[0].grades) == 2

    @patch("src.service.assignment_service.get_database_repository")
    def test_update_rubric_preserve_existing_criteria(self, mock_get_repo: MagicMock) -> None:
        """Test update_rubric preserves existing criteria when not provided."""
        from src.repository.db.models import RubricCriterionModel

        mock_repo = MagicMock()
        rubric_file = self._create_mock_file("rubric.pdf")
        existing_criteria = [RubricCriterionModel(name="Existing", max_points=10)]
        rubric_file.extracted_rubric = ExtractedRubricModel(
            title="Old", total_points=50, criteria=existing_criteria, raw_text="raw"
        )
        mock_repo.get_file.return_value = rubric_file
        mock_repo.update_file.return_value = True
        mock_get_repo.return_value = mock_repo

        service = AssignmentService()
        result = service.update_rubric(
            rubric_id=str(rubric_file.id),
            title="New Title",
        )

        assert result is True
        call_kwargs = mock_repo.update_file.call_args[1]
        assert len(call_kwargs["extracted_rubric"].criteria) == 1
        assert call_kwargs["extracted_rubric"].criteria[0].name == "Existing"

