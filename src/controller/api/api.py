from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
import io
import datetime as datetime
from src.controller.api.models import (
    HealthResponse, 
    CreateAssignmentRequest,
    AssignmentResponse,
    AssignmentListResponse,
    AssignmentDetailResponse,
    FileUploadResponse,
    FileInfo
)
from src.service.health_service import HealthService
from src.service.assignment_service import AssignmentService


app = FastAPI(
    title="Auto Grade API",
    description="A PoC of an automatic bulk assignment grader LLM engine",
    version="0.1.0",
    root_path="/api"
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint to verify API is running."""
    health_service = HealthService()
    if health_service.check_health():
        return HealthResponse(
            status="healthy",
            message="Auto Grade API is running and connected to the database"
        )
    else:
        return HealthResponse(
            status="unhealthy",
            message="Auto Grade API is running but could not connect to the database"
        )


@app.post("/assignments", response_model=AssignmentResponse, tags=["Assignments"])
async def create_assignment(request: CreateAssignmentRequest) -> AssignmentResponse:
    """Create a new assignment."""
    assignment_service = AssignmentService()
    
    try:
        assignment_id = assignment_service.create_assignment(
            name=request.name,
            confidence_threshold=request.confidence_threshold
        )
        
        assignment = assignment_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=500, detail="Failed to retrieve created assignment")
        
        return AssignmentResponse(
            id=str(assignment.id),
            name=assignment.name,
            confidence_threshold=assignment.confidence_threshold,
            deliverables=assignment.deliverables,
            evaluation_rubrics_count=len(assignment.evaluation_rubrics),
            relevant_documents_count=len(assignment.relevant_documents),
            created_at=assignment.created_at.isoformat(),
            updated_at=assignment.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create assignment")


@app.get("/assignments", response_model=AssignmentListResponse, tags=["Assignments"])
async def list_assignments() -> AssignmentListResponse:
    """List all assignments."""
    assignment_service = AssignmentService()
    
    try:
        assignments = assignment_service.list_assignments()
        
        assignment_responses = [
            AssignmentResponse(
                id=str(assignment.id),
                name=assignment.name,
                confidence_threshold=assignment.confidence_threshold,
                deliverables=assignment.deliverables,
                evaluation_rubrics_count=len(assignment.evaluation_rubrics),
                relevant_documents_count=len(assignment.relevant_documents),
                created_at=assignment.created_at.isoformat(),
                updated_at=assignment.updated_at.isoformat()
            )
            for assignment in assignments
        ]
        
        return AssignmentListResponse(
            assignments=assignment_responses,
            total=len(assignment_responses)
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list assignments")


@app.get("/assignments/{assignment_id}", response_model=AssignmentDetailResponse, tags=["Assignments"])
async def get_assignment(assignment_id: str) -> AssignmentDetailResponse:
    """Get a specific assignment by ID."""
    assignment_service = AssignmentService()
    
    try:
        assignment = assignment_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        rubrics = assignment_service.list_rubrics(assignment_id)
        documents = assignment_service.list_relevant_documents(assignment_id)
        
        rubric_infos = [
            FileInfo(
                id=str(rubric.id),
                filename=rubric.filename,
                content_type=rubric.content_type,
                file_type=rubric.file_type,
                uploaded_at=rubric.uploaded_at.isoformat()
            )
            for rubric in rubrics
        ]
        
        document_infos = [
            FileInfo(
                id=str(doc.id),
                filename=doc.filename,
                content_type=doc.content_type,
                file_type=doc.file_type,
                uploaded_at=doc.uploaded_at.isoformat()
            )
            for doc in documents
        ]
        
        return AssignmentDetailResponse(
            id=str(assignment.id),
            name=assignment.name,
            confidence_threshold=assignment.confidence_threshold,
            deliverables=assignment.deliverables,
            evaluation_rubrics=rubric_infos,
            relevant_documents=document_infos,
            created_at=assignment.created_at.isoformat(),
            updated_at=assignment.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get assignment")


@app.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Assignments"])
async def delete_assignment(assignment_id: str) -> None:
    """Delete an assignment."""
    assignment_service = AssignmentService()
    
    try:
        success = assignment_service.delete_assignment(assignment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Assignment not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete assignment")


@app.post("/assignments/{assignment_id}/rubrics", response_model=FileUploadResponse, tags=["Assignments"])
async def upload_rubric(
    assignment_id: str,
    file: UploadFile = File(...)
) -> FileUploadResponse:
    """Upload an evaluation rubric for an assignment."""
    assignment_service = AssignmentService()
    
    try:
        content = await file.read()
        file_id = assignment_service.upload_rubric(
            assignment_id=assignment_id,
            filename=file.filename or "rubric",
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )
        
        return FileUploadResponse(
            id=file_id,
            filename=file.filename or "rubric",
            uploaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            message="Rubric uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload rubric")


@app.post("/assignments/{assignment_id}/documents", response_model=FileUploadResponse, tags=["Assignments"])
async def upload_relevant_document(
    assignment_id: str,
    file: UploadFile = File(...)
) -> FileUploadResponse:
    """Upload a relevant document or example for an assignment."""
    assignment_service = AssignmentService()
    
    try:
        content = await file.read()
        file_id = assignment_service.upload_relevant_document(
            assignment_id=assignment_id,
            filename=file.filename or "document",
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )
        
        return FileUploadResponse(
            id=file_id,
            filename=file.filename or "document",
            uploaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            message="Document uploaded successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload document")


@app.get("/files/{file_id}", tags=["Files"])
async def download_file(file_id: str):
    """Download a file by ID."""
    assignment_service = AssignmentService()
    
    try:
        file_model = assignment_service.get_file(file_id)
        if not file_model:
            raise HTTPException(status_code=404, detail="File not found")
        
        return StreamingResponse(
            io.BytesIO(file_model.content),
            media_type=file_model.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_model.filename}"
            }
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to download file")