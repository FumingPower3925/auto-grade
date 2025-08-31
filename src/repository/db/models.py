from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from pydantic_core import core_schema
from bson import ObjectId
from typing import Any, List
from datetime import datetime, timezone

class PyObjectId(ObjectId):
    """Custom Pydantic type for MongoDB's ObjectId."""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
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
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
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

    @field_serializer('id')
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
    deliverables: List[str] = Field(default_factory=list)
    evaluation_rubrics: List[PyObjectId | ObjectId] = Field(default_factory=list) # type: ignore
    relevant_documents: List[PyObjectId | ObjectId] = Field(default_factory=list) # type: ignore
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        return round(v, 2)

    @field_serializer('id', 'evaluation_rubrics', 'relevant_documents')
    def serialize_objectid(self, value: PyObjectId | ObjectId | List[PyObjectId | ObjectId]) -> str | List[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        return str(value)
    
    @field_serializer('created_at', 'updated_at')
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
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


    @field_serializer('id', 'assignment_id')
    def serialize_objectid(self, value: PyObjectId | ObjectId) -> str:
        return str(value)
    
    @field_serializer('uploaded_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )