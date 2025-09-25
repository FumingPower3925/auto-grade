from pydantic import BaseModel, Field


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
    deliverables: list[str]
    evaluation_rubrics_count: int
    relevant_documents_count: int
    created_at: str
    updated_at: str


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]
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
    deliverables: list[str]
    deliverables_count: int
    evaluation_rubrics: list[FileInfo]
    relevant_documents: list[FileInfo]
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
    deliverables: list[DeliverableUploadResponse]
    total_uploaded: int
    message: str


class UpdateDeliverableRequest(BaseModel):
    student_name: str | None = Field(None, max_length=255, description="Student name")
    mark: float | None = Field(None, ge=0.0, le=10.0, description="Mark between 0 and 100")
    certainty_threshold: float | None = Field(
        None, ge=0.0, le=1.0, description="Certainty threshold between 0.0 and 1.0"
    )


class DeliverableResponse(BaseModel):
    id: str
    assignment_id: str
    student_name: str
    mark: float | None
    mark_status: str
    certainty_threshold: float | None
    filename: str
    extension: str
    content_type: str
    file_url: str
    uploaded_at: str
    updated_at: str


class DeliverableListResponse(BaseModel):
    deliverables: list[DeliverableResponse]
    total: int


class DeleteResponse(BaseModel):
    message: str
