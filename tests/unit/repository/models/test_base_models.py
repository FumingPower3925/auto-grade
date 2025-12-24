from datetime import datetime

import pytest
from bson import ObjectId
from pydantic import ValidationError

from src.repository.db.models import DocumentModel, FileModel, PyObjectId


class TestPyObjectId:
    """Tests for PyObjectId custom type."""

    def test_validate_valid_object_id(self) -> None:
        """Test validating a valid ObjectId string."""
        valid_id_str = "60c72b2f9b1d8e2a1c9d4b7f"
        validated_id = PyObjectId.validate(valid_id_str)
        assert isinstance(validated_id, ObjectId)
        assert validated_id == ObjectId(valid_id_str)

    def test_validate_invalid_object_id(self) -> None:
        """Test that invalid ObjectId string raises error."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate("this-is-not-a-valid-id")

    def test_validate_object_id_instance(self) -> None:
        """Test validating an existing ObjectId instance."""
        obj_id = ObjectId()
        validated_id = PyObjectId.validate(obj_id)  # type: ignore
        assert validated_id == obj_id


class TestDocumentModel:
    """Tests for DocumentModel."""

    def test_create_document_model(self) -> None:
        """Test creating a DocumentModel."""
        doc_id = ObjectId()

        document = DocumentModel(
            _id=doc_id,
            assignment="test_assignment",
            deliverable="test_deliverable",
            student_name="John Doe",
            document=b"test content",
            extension="txt",
        )

        assert document.id == doc_id
        assert document.assignment == "test_assignment"
        assert document.deliverable == "test_deliverable"
        assert document.student_name == "John Doe"
        assert document.document == b"test content"
        assert document.extension == "txt"

    def test_document_model_validation_with_invalid_id(self) -> None:
        """Test creating DocumentModel with invalid ID."""
        invalid_data: dict[str, str | bytes] = {
            "_id": "invalid-id-string",
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "document": b"test",
            "extension": "txt",
        }

        with pytest.raises(ValidationError):
            DocumentModel.model_validate(invalid_data)

    def test_document_model_validation_with_string_id(self) -> None:
        """Test creating DocumentModel with string ObjectId."""
        valid_id = str(ObjectId())

        data: dict[str, str | bytes] = {
            "_id": valid_id,
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "document": b"test",
            "extension": "txt",
        }

        document = DocumentModel.model_validate(data)
        assert str(document.id) == valid_id

    def test_document_id_serialization(self) -> None:
        """Test that document ID is serialized to string."""
        doc_id = ObjectId()

        document = DocumentModel(
            _id=doc_id, assignment="test", deliverable="test", student_name="test", document=b"test", extension="txt"
        )

        dump = document.model_dump()
        assert dump["id"] == str(doc_id)


class TestFileModel:
    """Tests for FileModel."""

    def test_create_file_model(self) -> None:
        """Test creating a FileModel."""
        file_id = ObjectId()
        assignment_id = ObjectId()
        now = datetime.now()

        file_model = FileModel(
            _id=file_id,
            assignment_id=assignment_id,
            filename="test.pdf",
            content=b"test content",
            content_type="application/pdf",
            file_type="rubric",
            uploaded_at=now,
        )

        assert file_model.id == file_id
        assert file_model.assignment_id == assignment_id
        assert file_model.filename == "test.pdf"
        assert file_model.content == b"test content"
        assert file_model.content_type == "application/pdf"
        assert file_model.file_type == "rubric"
        assert file_model.uploaded_at == now

    def test_file_model_with_defaults(self) -> None:
        """Test creating FileModel with default values."""
        assignment_id = ObjectId()

        file_model = FileModel(
            assignment_id=assignment_id,
            filename="test.txt",
            content=b"content",
            content_type="text/plain",
            file_type="document",
        )

        assert isinstance(file_model.id, ObjectId)
        assert isinstance(file_model.uploaded_at, datetime)

    def test_file_objectid_serialization(self) -> None:
        """Test that FileModel ObjectIds are serialized to strings."""
        file_id = ObjectId()
        assignment_id = ObjectId()

        file_model = FileModel(
            _id=file_id,
            assignment_id=assignment_id,
            filename="test.txt",
            content=b"test",
            content_type="text/plain",
            file_type="rubric",
        )

        dump = file_model.model_dump()
        assert dump["id"] == str(file_id)
        assert dump["assignment_id"] == str(assignment_id)

    def test_file_datetime_serialization(self) -> None:
        """Test that FileModel datetime is serialized to ISO format."""
        now = datetime.now()

        file_model = FileModel(
            assignment_id=ObjectId(),
            filename="test.txt",
            content=b"test",
            content_type="text/plain",
            file_type="rubric",
            uploaded_at=now,
        )

        dump = file_model.model_dump()
        assert dump["uploaded_at"] == now.isoformat()

    def test_file_model_with_extracted_rubric(self) -> None:
        """Test FileModel with extracted_rubric field."""
        from src.repository.db.models import ExtractedRubricModel, RubricCriterionModel

        rubric = ExtractedRubricModel(
            title="Test Rubric",
            total_points=100,
            criteria=[RubricCriterionModel(name="Quality", description="Code quality", max_points=50, weight=0.5)],
            raw_text="Raw text",
        )

        file_model = FileModel(
            assignment_id=ObjectId(),
            filename="rubric.pdf",
            content=b"content",
            content_type="application/pdf",
            file_type="rubric",
            extracted_rubric=rubric,
        )

        assert file_model.extracted_rubric is not None
        assert file_model.extracted_rubric.title == "Test Rubric"
        assert len(file_model.extracted_rubric.criteria) == 1

    def test_file_model_without_extracted_rubric(self) -> None:
        """Test FileModel without extracted_rubric field."""
        file_model = FileModel(
            assignment_id=ObjectId(),
            filename="document.pdf",
            content=b"content",
            content_type="application/pdf",
            file_type="relevant_document",
        )

        assert file_model.extracted_rubric is None


class TestRubricCriterionModel:
    """Tests for RubricCriterionModel."""

    def test_create_rubric_criterion(self) -> None:
        """Test creating a RubricCriterionModel."""
        from src.repository.db.models import GradeLevel, RubricCriterionModel

        grades = [
            GradeLevel(label="Excellent", points=25.0, description="Outstanding work"),
            GradeLevel(label="Good", points=20.0, description="Good work"),
        ]
        criterion = RubricCriterionModel(
            name="Code Quality",
            max_points=25.0,
            weight=0.25,
            grades=grades,
        )

        assert criterion.name == "Code Quality"
        assert criterion.max_points == pytest.approx(25.0)
        assert criterion.weight == pytest.approx(0.25)
        assert len(criterion.grades) == 2
        assert criterion.grades[0].label == "Excellent"

    def test_rubric_criterion_with_defaults(self) -> None:
        """Test RubricCriterionModel with default values."""
        from src.repository.db.models import RubricCriterionModel

        criterion = RubricCriterionModel(name="Test", max_points=10)

        assert criterion.grades == []
        assert criterion.weight is None

    def test_rubric_criterion_weight_validation(self) -> None:
        """Test that weight must be between 0.0 and 1.0."""
        from src.repository.db.models import RubricCriterionModel

        with pytest.raises(ValidationError):
            RubricCriterionModel(name="Test", max_points=10, weight=1.5)

    def test_rubric_criterion_weight_rounding(self) -> None:
        """Test that weight is rounded to 2 decimal places."""
        from src.repository.db.models import RubricCriterionModel

        criterion = RubricCriterionModel(name="Test", max_points=10, weight=0.333)

        assert criterion.weight == pytest.approx(0.33)

    def test_rubric_criterion_max_grades_validation(self) -> None:
        """Test that criterion cannot have more than 10 grades."""
        from src.repository.db.models import GradeLevel, RubricCriterionModel

        # 11 grades should fail
        grades = [GradeLevel(label=f"Grade {i}", points=i, description="") for i in range(11)]

        with pytest.raises(ValidationError):
            RubricCriterionModel(name="Test", max_points=10, grades=grades)


class TestExtractedRubricModel:
    """Tests for ExtractedRubricModel."""

    def test_create_extracted_rubric(self) -> None:
        """Test creating an ExtractedRubricModel."""
        from src.repository.db.models import ExtractedRubricModel, RubricCriterionModel

        criteria = [
            RubricCriterionModel(name="Criterion 1", max_points=50),
            RubricCriterionModel(name="Criterion 2", max_points=50),
        ]

        rubric = ExtractedRubricModel(
            title="Grading Rubric",
            total_points=100,
            criteria=criteria,
            raw_text="Original text",
        )

        assert rubric.title == "Grading Rubric"
        assert rubric.total_points == 100
        assert len(rubric.criteria) == 2
        assert rubric.raw_text == "Original text"

    def test_extracted_rubric_with_defaults(self) -> None:
        """Test ExtractedRubricModel with default values."""
        from src.repository.db.models import ExtractedRubricModel

        rubric = ExtractedRubricModel()

        assert rubric.title is None
        assert rubric.total_points is None
        assert rubric.criteria == []
        assert rubric.raw_text is None

    def test_extracted_rubric_serialization(self) -> None:
        """Test ExtractedRubricModel serialization."""
        from src.repository.db.models import ExtractedRubricModel, RubricCriterionModel

        rubric = ExtractedRubricModel(
            title="Test",
            total_points=50,
            criteria=[RubricCriterionModel(name="C1", max_points=25)],
        )

        dump = rubric.model_dump()
        assert dump["title"] == "Test"
        assert dump["total_points"] == 50
        assert len(dump["criteria"]) == 1

