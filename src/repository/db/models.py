from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    """Custom Pydantic type for MongoDB's ObjectId."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def validate(cls, v: str) -> ObjectId:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class DocumentModel(BaseModel):
    id: PyObjectId | ObjectId = Field(default_factory=PyObjectId, alias="_id")
    assignment: str
    deliverable: str
    student_name: str
    document: bytes
    extension: str

    @field_serializer("id")
    def serialize_id(self, id: PyObjectId | ObjectId) -> str:
        return str(id)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class AssignmentModel(BaseModel):
    id: PyObjectId | ObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., max_length=255)
    confidence_threshold: float = Field(..., ge=0.0, le=1.0)
    deliverables: list[PyObjectId | ObjectId] = Field(default_factory=list)  # type: ignore
    evaluation_rubrics: list[PyObjectId | ObjectId] = Field(default_factory=list)  # type: ignore
    relevant_documents: list[PyObjectId | ObjectId] = Field(default_factory=list)  # type: ignore
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        return round(v, 2)

    @field_serializer("id", "evaluation_rubrics", "relevant_documents", "deliverables")
    def serialize_objectid(self, value: PyObjectId | ObjectId | list[PyObjectId | ObjectId]) -> str | list[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        return str(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class FileModel(BaseModel):
    id: PyObjectId | ObjectId = Field(default_factory=PyObjectId, alias="_id")
    assignment_id: PyObjectId | ObjectId
    filename: str
    content: bytes
    content_type: str
    file_type: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("id", "assignment_id")
    def serialize_objectid(self, value: PyObjectId | ObjectId) -> str:
        return str(value)

    @field_serializer("uploaded_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class DeliverableModel(BaseModel):
    id: PyObjectId | ObjectId = Field(default_factory=PyObjectId, alias="_id")
    assignment_id: PyObjectId | ObjectId
    student_name: str = Field(default="Unknown")
    mark: float | None = Field(default=None, ge=0.0, le=10.0)
    certainty_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    filename: str
    content: bytes
    extension: str
    content_type: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extracted_text: str | None = Field(default=None)

    @field_validator("mark")
    @classmethod
    def validate_mark(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 10.0:
            raise ValueError("Mark must be between 0.0 and 10.0")
        return round(v, 2) if v is not None else None

    @field_validator("certainty_threshold")
    @classmethod
    def validate_certainty(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Certainty threshold must be between 0.0 and 1.0")
        return round(v, 2) if v is not None else None

    @field_serializer("id", "assignment_id")
    def serialize_objectid(self, value: PyObjectId | ObjectId) -> str:
        return str(value)

    @field_serializer("uploaded_at", "updated_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
