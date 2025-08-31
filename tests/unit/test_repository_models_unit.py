import pytest
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime

from src.repository.db.models import PyObjectId, DocumentModel, AssignmentModel, FileModel


class TestPyObjectId:
    """Unit tests for the PyObjectId custom type."""

    def test_validate_valid_object_id(self) -> None:
        """Test that a valid ObjectId string is correctly validated."""
        valid_id_str = "60c72b2f9b1d8e2a1c9d4b7f"
        validated_id = PyObjectId.validate(valid_id_str)
        assert isinstance(validated_id, ObjectId)
        assert validated_id == ObjectId(valid_id_str)

    def test_validate_invalid_object_id_raises_error(self) -> None:
        """Test that an invalid ObjectId string raises a ValueError."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate("this-is-not-a-valid-id")


class TestDocumentModel:
    """Unit tests for the DocumentModel."""

    def test_model_validation_with_invalid_id(self) -> None:
        """Test that creating a model with an invalid ObjectId string fails."""
        invalid_data: dict[str, str | bytes] = {
            "_id": "invalid-id-string",
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "document": b"test",
            "extension": "txt"
        }
        with pytest.raises(ValidationError):
            DocumentModel.model_validate(invalid_data)

    def test_model_validation_with_valid_id(self) -> None:
        """Test that creating a model with a valid ObjectId string succeeds."""
        valid_id = ObjectId()
        valid_data: dict[str, str | bytes] = {
            "_id": str(valid_id),
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "document": b"test",
            "extension": "txt"
        }
        model = DocumentModel.model_validate(valid_data)
        assert model.id == valid_id

    def test_id_serialization(self) -> None:
        """Test that the `id` field is serialized to a string."""
        doc_id = ObjectId()
        model = DocumentModel(
            _id=doc_id,
            assignment="test",
            deliverable="test",
            student_name="test",
            document=b"test",
            extension="txt"
        )
        assert model.model_dump()["id"] == str(doc_id)


class TestAssignmentModel:
    """Unit tests for the AssignmentModel."""

    def test_confidence_threshold_validation(self) -> None:
        """Test the confidence_threshold validator."""
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            AssignmentModel.validate_confidence_threshold(-0.1)
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            AssignmentModel.validate_confidence_threshold(1.1)

    def test_objectid_serialization(self) -> None:
        """Test that ObjectId fields are serialized to strings."""
        assignment_id = ObjectId()
        rubric_id = ObjectId()
        doc_id = ObjectId()
        model = AssignmentModel(
            _id=assignment_id,
            name="test",
            confidence_threshold=0.8,
            evaluation_rubrics=[rubric_id],
            relevant_documents=[doc_id]
        )
        dump = model.model_dump()
        assert dump["id"] == str(assignment_id)
        assert dump["evaluation_rubrics"] == [str(rubric_id)]
        assert dump["relevant_documents"] == [str(doc_id)]

    def test_datetime_serialization(self) -> None:
        """Test that datetime fields are serialized to ISO format."""
        now = datetime.now()
        model = AssignmentModel(
            name="test",
            confidence_threshold=0.8,
            created_at=now,
            updated_at=now
        )
        dump = model.model_dump()
        assert dump["created_at"] == now.isoformat()
        assert dump["updated_at"] == now.isoformat()

    def test_serialize_objectid_list(self) -> None:
        """Test serializing a list of ObjectIds."""
        model = AssignmentModel(
            name="test",
            confidence_threshold=0.8,
            evaluation_rubrics=[ObjectId(), ObjectId()]
        )
        dump = model.model_dump()
        assert isinstance(dump["evaluation_rubrics"], list)
        assert all(isinstance(item, str) for item in dump["evaluation_rubrics"]) # type: ignore

    def test_serialize_objectid_single(self) -> None:
        """Test serializing a single ObjectId."""
        model = AssignmentModel(
            name="test",
            confidence_threshold=0.8
        )
        dump = model.model_dump()
        assert isinstance(dump["id"], str)

    def test_pyobjectid_in_model(self) -> None:
        """Test using PyObjectId in a Pydantic model."""
        class MyModel(AssignmentModel):
            my_id: PyObjectId

        obj_id = ObjectId()
        model = MyModel(name="test", confidence_threshold=0.8, my_id=PyObjectId(obj_id))
        assert model.my_id == obj_id


class TestFileModel:
    """Unit tests for the FileModel."""

    def test_objectid_serialization(self) -> None:
        """Test that ObjectId fields are serialized to strings."""
        file_id = ObjectId()
        assignment_id = ObjectId()
        model = FileModel(
            _id=file_id,
            assignment_id=assignment_id,
            filename="test.txt",
            content=b"test",
            content_type="text/plain",
            file_type="rubric"
        )
        dump = model.model_dump()
        assert dump["id"] == str(file_id)
        assert dump["assignment_id"] == str(assignment_id)

    def test_datetime_serialization(self) -> None:
        """Test that datetime fields are serialized to ISO format."""
        now = datetime.now()
        model = FileModel(
            assignment_id=ObjectId(),
            filename="test.txt",
            content=b"test",
            content_type="text/plain",
            file_type="rubric",
            uploaded_at=now
        )
        dump = model.model_dump()
        assert dump["uploaded_at"] == now.isoformat()