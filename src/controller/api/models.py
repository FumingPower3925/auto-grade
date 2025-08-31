from pydantic import BaseModel, Field
from typing import List


class HealthResponse(BaseModel):
    status: str
    message: str


class CreateAssignmentRequest(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the assignment")
    confidence_threshold: float = Field(..., ge=0.0, le=1.0, description="Confidence threshold between 0.0 and 1.0")


class AssignmentResponse(BaseModel):
    id: str
    name: str
    confidence_threshold: float
    deliverables: List[str]
    evaluation_rubrics_count: int
    relevant_documents_count: int
    created_at: str
    updated_at: str


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponse]
    total: int


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    message: str


class FileInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    file_type: str
    uploaded_at: str


class AssignmentDetailResponse(BaseModel):
    id: str
    name: str
    confidence_threshold: float
    deliverables: List[str]
    evaluation_rubrics: List[FileInfo]
    relevant_documents: List[FileInfo]
    created_at: str
    updated_at: str


class ErrorResponse(BaseModel):
    detail: str