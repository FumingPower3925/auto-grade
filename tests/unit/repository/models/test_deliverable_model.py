from typing import Any, Dict
import pytest
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

from src.repository.db.models import DeliverableModel


class TestDeliverableModel:
    """Tests for DeliverableModel validation and serialization."""

    def test_create_deliverable_with_all_fields(self) -> None:
        """Test creating deliverable with all fields."""
        deliverable_id = ObjectId()
        assignment_id = ObjectId()
        now = datetime.now(timezone.utc)
        
        deliverable = DeliverableModel(
            _id=deliverable_id,
            assignment_id=assignment_id,
            student_name="John Doe",
            mark=8.55,
            certainty_threshold=0.95,
            filename="submission.pdf",
            content=b"PDF content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=now,
            updated_at=now,
            extracted_text="Extracted text"
        )
        
        assert deliverable.id == deliverable_id
        assert deliverable.assignment_id == assignment_id
        assert deliverable.student_name == "John Doe"
        assert deliverable.mark == 8.55
        assert deliverable.certainty_threshold == 0.95
        assert deliverable.filename == "submission.pdf"
        assert deliverable.content == b"PDF content"
        assert deliverable.extracted_text == "Extracted text"

    def test_create_deliverable_with_defaults(self) -> None:
        """Test creating deliverable with default values."""
        assignment_id = ObjectId()
        
        deliverable = DeliverableModel(
            assignment_id=assignment_id,
            filename="submission.pdf",
            content=b"PDF content",
            extension="pdf",
            content_type="application/pdf"
        )
        
        assert deliverable.student_name == "Unknown"
        assert deliverable.mark is None
        assert deliverable.certainty_threshold is None
        assert deliverable.extracted_text is None
        assert isinstance(deliverable.uploaded_at, datetime)
        assert isinstance(deliverable.updated_at, datetime)

    @pytest.mark.parametrize("mark,expected", [
        (0.0, 0.0),
        (5.0, 5.0),
        (10.0, 10.0),
        (8.556, 8.56),
        (9.111, 9.11),
        (None, None),
    ])
    def test_mark_validation_valid(self, mark: float, expected: float) -> None:
        """Test valid mark values."""
        assert DeliverableModel.validate_mark(mark) == expected

    @pytest.mark.parametrize("mark", [-0.1, 10.1, 15.0, -10.0])
    def test_mark_validation_invalid(self, mark: float) -> None:
        """Test invalid mark values."""
        with pytest.raises(ValueError, match="Mark must be between 0.0 and 10.0"):
            DeliverableModel.validate_mark(mark)

    @pytest.mark.parametrize("certainty,expected", [
        (0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
        (0.856, 0.86),
        (0.921, 0.92),
        (None, None),
    ])
    def test_certainty_threshold_validation_valid(self, certainty: float, expected: float) -> None:
        """Test valid certainty threshold values."""
        assert DeliverableModel.validate_certainty(certainty) == expected

    @pytest.mark.parametrize("certainty", [-0.01, 1.01, 2.0, -1.0])
    def test_certainty_threshold_validation_invalid(self, certainty: float) -> None:
        """Test invalid certainty threshold values."""
        with pytest.raises(ValueError, match="Certainty threshold must be between 0.0 and 1.0"):
            DeliverableModel.validate_certainty(certainty)

    def test_objectid_serialization(self) -> None:
        """Test that ObjectId fields are serialized to strings."""
        deliverable_id = ObjectId()
        assignment_id = ObjectId()
        
        deliverable = DeliverableModel(
            _id=deliverable_id,
            assignment_id=assignment_id,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf"
        )
        
        dump = deliverable.model_dump()
        assert dump["id"] == str(deliverable_id)
        assert dump["assignment_id"] == str(assignment_id)

    def test_datetime_serialization(self) -> None:
        """Test that datetime fields are serialized to ISO format."""
        now = datetime.now(timezone.utc)
        
        deliverable = DeliverableModel(
            assignment_id=ObjectId(),
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf",
            uploaded_at=now,
            updated_at=now
        )
        
        dump = deliverable.model_dump()
        assert dump["uploaded_at"] == now.isoformat()
        assert dump["updated_at"] == now.isoformat()

    def test_model_validation_from_dict(self) -> None:
        """Test creating DeliverableModel from dictionary."""
        deliverable_id = ObjectId()
        assignment_id = ObjectId()
        now = datetime.now(timezone.utc)
        
        data: Dict[str, Any] = {
            "_id": deliverable_id,
            "assignment_id": assignment_id,
            "student_name": "Jane Smith",
            "mark": 9.0,
            "certainty_threshold": 0.85,
            "filename": "homework.pdf",
            "content": b"PDF content",
            "extension": "pdf",
            "content_type": "application/pdf",
            "uploaded_at": now,
            "updated_at": now,
            "extracted_text": "Some text"
        }
        
        deliverable = DeliverableModel.model_validate(data)
        
        assert deliverable.id == deliverable_id
        assert deliverable.assignment_id == assignment_id
        assert deliverable.student_name == "Jane Smith"
        assert deliverable.mark == 9.0
        assert deliverable.certainty_threshold == 0.85

    def test_model_validation_with_string_ids(self) -> None:
        """Test creating DeliverableModel with string ObjectIds."""
        deliverable_id = str(ObjectId())
        assignment_id = str(ObjectId())
        
        data: Dict[str, Any] = {
            "_id": deliverable_id,
            "assignment_id": assignment_id,
            "filename": "test.pdf",
            "content": b"content",
            "extension": "pdf",
            "content_type": "application/pdf"
        }
        
        deliverable = DeliverableModel.model_validate(data)
        
        assert str(deliverable.id) == deliverable_id
        assert str(deliverable.assignment_id) == assignment_id

    def test_model_validation_with_invalid_mark(self) -> None:
        """Test model validation with invalid mark value."""
        data: Dict[str, Any] = {
            "assignment_id": ObjectId(),
            "filename": "test.pdf",
            "content": b"content",
            "extension": "pdf",
            "content_type": "application/pdf",
            "mark": 15.0
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DeliverableModel.model_validate(data)
        
        errors = exc_info.value.errors()
        assert any("mark" in str(error) for error in errors)

    def test_model_validation_with_invalid_certainty(self) -> None:
        """Test model validation with invalid certainty threshold."""
        data: Dict[str, Any] = {
            "assignment_id": ObjectId(),
            "filename": "test.pdf",
            "content": b"content",
            "extension": "pdf",
            "content_type": "application/pdf",
            "certainty_threshold": 1.5
        }
        
        with pytest.raises(ValidationError) as exc_info:
            DeliverableModel.model_validate(data)
        
        errors = exc_info.value.errors()
        assert any("certainty" in str(error) for error in errors)

    def test_model_copy_with_update(self) -> None:
        """Test copying a model with updates."""
        original = DeliverableModel(
            assignment_id=ObjectId(),
            student_name="Original Name",
            mark=7.50,
            filename="test.pdf",
            content=b"content",
            extension="pdf",
            content_type="application/pdf"
        )
        
        updated = original.model_copy(update={
            "student_name": "Updated Name",
            "mark": 8.5,
            "certainty_threshold": 0.90
        })
        
        assert updated.student_name == "Updated Name"
        assert updated.mark == 8.5
        assert updated.certainty_threshold == 0.90
        assert updated.filename == original.filename
        assert updated.assignment_id == original.assignment_id

    def test_model_with_null_optional_fields(self) -> None:
        """Test model with null/None optional fields."""
        data: Dict[str, Any] = {
            "assignment_id": ObjectId(),
            "student_name": "Student Name",
            "mark": None,
            "certainty_threshold": None,
            "filename": "test.pdf",
            "content": b"content",
            "extension": "pdf",
            "content_type": "application/pdf",
            "extracted_text": None
        }
        
        deliverable = DeliverableModel.model_validate(data)
        
        assert deliverable.mark is None
        assert deliverable.certainty_threshold is None
        assert deliverable.extracted_text is None

    def test_model_json_serialization(self) -> None:
        """Test JSON serialization of the model."""
        deliverable = DeliverableModel(
            assignment_id=ObjectId(),
            student_name="Test Student",
            mark=8.85,
            certainty_threshold=0.92,
            filename="submission.pdf",
            content=b"PDF content",
            extension="pdf",
            content_type="application/pdf"
        )
        
        json_str = deliverable.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test Student" in json_str
        assert "8.85" in json_str
        assert "0.92" in json_str