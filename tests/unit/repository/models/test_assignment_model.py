from typing import Any
import pytest
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

from src.repository.db.models import AssignmentModel


class TestAssignmentModel:
    """Tests for AssignmentModel validation and serialization."""

    def test_create_assignment_with_all_fields(self) -> None:
        """Test creating assignment with all fields."""
        assignment_id = ObjectId()
        rubric_id = ObjectId()
        doc_id = ObjectId()
        deliverable_id = ObjectId()
        now = datetime.now(timezone.utc)
        
        assignment = AssignmentModel(
            _id=assignment_id,
            name="Test Assignment",
            confidence_threshold=0.75,
            deliverables=[deliverable_id],
            evaluation_rubrics=[rubric_id],
            relevant_documents=[doc_id],
            created_at=now,
            updated_at=now
        )
        
        assert assignment.id == assignment_id
        assert assignment.name == "Test Assignment"
        assert assignment.confidence_threshold == 0.75
        assert rubric_id in assignment.evaluation_rubrics
        assert doc_id in assignment.relevant_documents
        assert deliverable_id in assignment.deliverables

    def test_create_assignment_with_defaults(self) -> None:
        """Test creating assignment with default values."""
        assignment = AssignmentModel(
            name="Test Assignment",
            confidence_threshold=0.5
        )
        
        assert isinstance(assignment.id, ObjectId)
        assert assignment.deliverables == []
        assert assignment.evaluation_rubrics == []
        assert assignment.relevant_documents == []
        assert isinstance(assignment.created_at, datetime)
        assert isinstance(assignment.updated_at, datetime)

    @pytest.mark.parametrize("threshold,valid", [
        (0.0, True),
        (0.5, True),
        (1.0, True),
        (0.999, True),
        (-0.01, False),
        (1.01, False),
        (2.0, False),
    ])
    def test_confidence_threshold_validation(self, threshold: float, valid: bool) -> None:
        """Test confidence threshold validation."""
        if valid:
            result = AssignmentModel.validate_confidence_threshold(threshold)
            assert result == round(threshold, 2)
        else:
            with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
                AssignmentModel.validate_confidence_threshold(threshold)

    def test_objectid_serialization(self) -> None:
        """Test that ObjectId fields are serialized to strings."""
        assignment_id = ObjectId()
        rubric_id = ObjectId()
        doc_id = ObjectId()
        
        assignment = AssignmentModel(
            _id=assignment_id,
            name="Test",
            confidence_threshold=0.8,
            evaluation_rubrics=[rubric_id],
            relevant_documents=[doc_id]
        )
        
        dump = assignment.model_dump()
        assert dump["id"] == str(assignment_id)
        assert dump["evaluation_rubrics"] == [str(rubric_id)]
        assert dump["relevant_documents"] == [str(doc_id)]

    def test_datetime_serialization(self) -> None:
        """Test that datetime fields are serialized to ISO format."""
        now = datetime.now(timezone.utc)
        
        assignment = AssignmentModel(
            name="Test",
            confidence_threshold=0.8,
            created_at=now,
            updated_at=now
        )
        
        dump = assignment.model_dump()
        assert dump["created_at"] == now.isoformat()
        assert dump["updated_at"] == now.isoformat()

    def test_model_validation_from_dict(self) -> None:
        """Test creating AssignmentModel from dictionary."""
        assignment_id = ObjectId()
        now = datetime.now(timezone.utc)
        
        data: dict[str, Any] = {
            "_id": assignment_id,
            "name": "Test Assignment",
            "confidence_threshold": 0.75,
            "deliverables": [],
            "evaluation_rubrics": [],
            "relevant_documents": [],
            "created_at": now,
            "updated_at": now
        }
        
        assignment = AssignmentModel.model_validate(data)
        
        assert assignment.id == assignment_id
        assert assignment.name == "Test Assignment"
        assert assignment.confidence_threshold == 0.75

    def test_model_validation_with_string_ids(self) -> None:
        """Test creating AssignmentModel with string ObjectIds."""
        assignment_id = str(ObjectId())
        rubric_id = str(ObjectId())
        
        data: dict[str, Any] = {
            "_id": assignment_id,
            "name": "Test",
            "confidence_threshold": 0.5,
            "evaluation_rubrics": [rubric_id]
        }
        
        assignment = AssignmentModel.model_validate(data)
        
        assert str(assignment.id) == assignment_id
        assert str(assignment.evaluation_rubrics[0]) == rubric_id

    def test_model_validation_with_invalid_threshold(self) -> None:
        """Test model validation with invalid confidence threshold."""
        data: dict[str, str | float] = {
            "name": "Test",
            "confidence_threshold": 1.5
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AssignmentModel.model_validate(data)
        
        errors = exc_info.value.errors()
        assert any("confidence_threshold" in str(error) for error in errors)