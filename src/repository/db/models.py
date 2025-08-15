from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from bson import ObjectId
from typing import Any

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
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    assignment: str
    deliverable: str
    student_name: str
    document: bytes
    extension: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )