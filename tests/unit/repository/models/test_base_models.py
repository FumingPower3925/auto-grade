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
