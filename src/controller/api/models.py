from pydantic import BaseModel, Field
from typing import List, Optional


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
    deliverables_count: int
    evaluation_rubrics: List[FileInfo]
    relevant_documents: List[FileInfo]
    created_at: str
    updated_at: str


class ErrorResponse(BaseModel):
    detail: str


class DeliverableUploadResponse(BaseModel):
    id: str
    filename: str
    student_name: str
    uploaded_at: str
    message: str


class BulkDeliverableUploadResponse(BaseModel):
    deliverables: List[DeliverableUploadResponse]
    total_uploaded: int
    message: str


class UpdateDeliverableRequest(BaseModel):
    student_name: Optional[str] = Field(None, max_length=255, description="Student name")
    mark: Optional[float] = Field(None, ge=0.0, le=10.0, description="Mark between 0 and 100")
    certainty_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Certainty threshold between 0.0 and 1.0")


class DeliverableResponse(BaseModel):
    id: str
    assignment_id: str
    student_name: str
    mark: Optional[float]
    mark_status: str
    certainty_threshold: Optional[float]
    filename: str
    extension: str
    content_type: str
    file_url: str
    uploaded_at: str
    updated_at: str


class DeliverableListResponse(BaseModel):
    deliverables: List[DeliverableResponse]
    total: int


class DeleteResponse(BaseModel):
    message: str