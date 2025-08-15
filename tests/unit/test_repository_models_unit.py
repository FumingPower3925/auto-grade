import pytest
from pydantic import ValidationError
from bson import ObjectId

from src.repository.db.models import PyObjectId, DocumentModel


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