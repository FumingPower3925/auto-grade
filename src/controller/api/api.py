import datetime as datetime
import io
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from src.controller.api.models import (
    AssignmentDetailResponse,
    AssignmentListResponse,
    AssignmentResponse,
    BulkDeliverableUploadResponse,
    BulkFileUploadResponse,
    CreateAssignmentRequest,
    DeleteResponse,
    DeliverableListResponse,
    DeliverableResponse,
    DeliverableUploadResponse,
    ExtractedRubricResponse,
    FileInfo,
    FileUploadResponse,
    GradeLevelResponse,
    HealthResponse,
    RubricCriterionResponse,
    UpdateDeliverableRequest,
    UpdateRubricRequest,
)
from src.repository.db.models import ExtractedRubricModel
from src.service.assignment_service import AssignmentService
from src.service.deliverable_service import DeliverableService
from src.service.health_service import HealthService

DEFAULT_CONTENT_TYPE = "application/octet-stream"

DELIVERABLE_NOT_FOUND = "Deliverable not found"

app = FastAPI(
    title="Auto Grade API",
    description="A PoC of an automatic bulk assignment grader LLM engine",
    version="0.1.0",
    root_path="/api",
)


def convert_extracted_rubric(extracted_rubric: ExtractedRubricModel | None) -> ExtractedRubricResponse | None:
    """Convert ExtractedRubricModel to API response format."""
    if extracted_rubric is None:
        return None

    criteria = [
        RubricCriterionResponse(
            name=c.name,
            max_points=c.max_points,
            weight=c.weight,
            grades=[GradeLevelResponse(label=g.label, points=g.points, description=g.description) for g in c.grades],
        )
        for c in extracted_rubric.criteria
    ]

    return ExtractedRubricResponse(
        title=extracted_rubric.title,
        total_points=extracted_rubric.total_points,
        criteria=criteria,
        raw_text=extracted_rubric.raw_text,
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint to verify API is running."""
    health_service = HealthService()
    if health_service.check_health():
        return HealthResponse(status="healthy", message="Auto Grade API is running and connected to the database")
    else:
        return HealthResponse(
            status="unhealthy", message="Auto Grade API is running but could not connect to the database"
        )


@app.post("/assignments", response_model=AssignmentResponse, tags=["Assignments"])
async def create_assignment(request: CreateAssignmentRequest) -> AssignmentResponse:
    """Create a new assignment."""
    assignment_service = AssignmentService()

    try:
        assignment_id = assignment_service.create_assignment(
            name=request.name, confidence_threshold=request.confidence_threshold
        )

        assignment = assignment_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=500, detail="Failed to retrieve created assignment")

        return AssignmentResponse(
            id=str(assignment.id),
            name=assignment.name,
            confidence_threshold=assignment.confidence_threshold,
            deliverables=[str(d) for d in assignment.deliverables],  # type: ignore
            evaluation_rubrics_count=len(assignment.evaluation_rubrics),
            relevant_documents_count=len(assignment.relevant_documents),
            created_at=assignment.created_at.isoformat(),
            updated_at=assignment.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create assignment") from e


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
                deliverables=[str(d) for d in assignment.deliverables],  # type: ignore
                evaluation_rubrics_count=len(assignment.evaluation_rubrics),
                relevant_documents_count=len(assignment.relevant_documents),
                created_at=assignment.created_at.isoformat(),
                updated_at=assignment.updated_at.isoformat(),
            )
            for assignment in assignments
        ]

        return AssignmentListResponse(assignments=assignment_responses, total=len(assignment_responses))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list assignments") from e


@app.get("/assignments/{assignment_id}", response_model=AssignmentDetailResponse, tags=["Assignments"])  # type: ignore[misc]
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
                uploaded_at=rubric.uploaded_at.isoformat(),
                extracted_rubric=convert_extracted_rubric(rubric.extracted_rubric),
            )
            for rubric in rubrics
        ]

        document_infos = [
            FileInfo(
                id=str(doc.id),
                filename=doc.filename,
                content_type=doc.content_type,
                file_type=doc.file_type,
                uploaded_at=doc.uploaded_at.isoformat(),
                status=str(doc.status.value) if hasattr(doc, "status") and doc.status else None,
                progress=doc.progress,
                error_message=doc.error_message,
                chunk_count=doc.chunk_count,
            )
            for doc in documents
        ]

        return AssignmentDetailResponse(
            id=str(assignment.id),
            name=assignment.name,
            confidence_threshold=assignment.confidence_threshold,
            deliverables=[str(d) for d in assignment.deliverables],  # type: ignore
            deliverables_count=len(assignment.deliverables),
            evaluation_rubrics=rubric_infos,
            relevant_documents=document_infos,
            created_at=assignment.created_at.isoformat(),
            updated_at=assignment.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get assignment") from e


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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete assignment") from e


@app.post("/assignments/{assignment_id}/rubrics", response_model=FileUploadResponse, tags=["Assignments"])
async def upload_rubric(assignment_id: str, file: Annotated[UploadFile, File(...)]) -> FileUploadResponse:
    """Upload an evaluation rubric for an assignment."""
    assignment_service = AssignmentService()

    try:
        content = await file.read()
        file_id = await assignment_service.upload_rubric(
            assignment_id=assignment_id,
            filename=file.filename or "rubric",
            content=content,
            content_type=file.content_type or DEFAULT_CONTENT_TYPE,
        )

        return FileUploadResponse(
            id=file_id,
            filename=file.filename or "rubric",
            uploaded_at=datetime.datetime.now(datetime.UTC).isoformat(),
            message="Rubric uploaded successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload rubric") from e


@app.post("/assignments/{assignment_id}/documents", response_model=BulkFileUploadResponse, tags=["Assignments"])
async def upload_relevant_documents(
    assignment_id: str, files: Annotated[list[UploadFile], File(...)]
) -> BulkFileUploadResponse:
    """Upload multiple relevant documents for an assignment (async processing)."""
    assignment_service = AssignmentService()

    try:
        uploaded_files = []
        for file in files:
            content = await file.read()
            # This returns immediately after queuing background task
            file_id = assignment_service.upload_relevant_document(
                assignment_id=assignment_id,
                filename=file.filename or "document",
                content=content,
                content_type=file.content_type or DEFAULT_CONTENT_TYPE,
            )
            uploaded_files.append(
                FileUploadResponse(
                    id=file_id,
                    filename=file.filename or "document",
                    uploaded_at=datetime.datetime.now(datetime.UTC).isoformat(),
                    message="Document queued for processing",
                )
            )

        return BulkFileUploadResponse(
            files=uploaded_files,
            total_uploaded=len(uploaded_files),
            message=f"Successfully queued {len(uploaded_files)} document(s) for processing",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload documents") from e


@app.get("/assignments/{assignment_id}/documents/status", response_model=list[FileInfo], tags=["Assignments"])
async def get_documents_status(assignment_id: str) -> list[FileInfo]:
    """Get processing status of relevant documents."""
    assignment_service = AssignmentService()
    try:
        documents = assignment_service.get_documents_status(assignment_id)
        return [
            FileInfo(
                id=str(doc.id),
                filename=doc.filename,
                content_type=doc.content_type,
                file_type=doc.file_type,
                uploaded_at=doc.uploaded_at.isoformat(),
                status=str(doc.status.value) if hasattr(doc, "status") and doc.status else None,
                progress=doc.progress,
                error_message=doc.error_message,
                chunk_count=doc.chunk_count,
            )
            for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get documents status") from e


@app.get("/files/{file_id}", tags=["Files"])
async def download_file(file_id: str) -> StreamingResponse:
    """Download a file by ID."""
    assignment_service = AssignmentService()

    try:
        file_model = assignment_service.get_file(file_id)
        if not file_model:
            raise HTTPException(status_code=404, detail="File not found")

        return StreamingResponse(
            io.BytesIO(file_model.content),
            media_type=file_model.content_type,
            headers={"Content-Disposition": f"inline; filename={file_model.filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to download file") from e


@app.patch("/rubrics/{rubric_id}", response_model=ExtractedRubricResponse, tags=["Files"])
async def update_rubric(rubric_id: str, request: UpdateRubricRequest) -> ExtractedRubricResponse:
    """Update a rubric's extracted data."""
    assignment_service = AssignmentService()

    try:
        criteria_dicts = None
        if request.criteria is not None:
            criteria_dicts = [c.model_dump() for c in request.criteria]

        success = assignment_service.update_rubric(
            rubric_id=rubric_id,
            title=request.title,
            total_points=request.total_points,
            criteria=criteria_dicts,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update rubric")

        # Fetch updated file to return response
        file_model = assignment_service.get_file(rubric_id)
        if not file_model or not file_model.extracted_rubric:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated rubric")

        return convert_extracted_rubric(file_model.extracted_rubric)  # type: ignore
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update rubric") from e


@app.delete("/rubrics/{rubric_id}", tags=["Files"])
async def delete_rubric(rubric_id: str) -> dict[str, str]:
    """Delete a rubric and its extracted data."""
    assignment_service = AssignmentService()

    try:
        success = assignment_service.delete_rubric(rubric_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rubric not found")
        return {"message": "Rubric deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete rubric") from e


@app.delete("/files/{file_id}", tags=["Files"])
async def delete_file(file_id: str) -> dict[str, str]:
    """Delete a document file and its embeddings."""
    assignment_service = AssignmentService()

    try:
        success = assignment_service.delete_document(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete document") from e


@app.post("/assignments/{assignment_id}/deliverables", response_model=DeliverableUploadResponse, tags=["Deliverables"])
async def upload_deliverable(
    assignment_id: str,
    file: Annotated[UploadFile, File(...)],
    extract_name: Annotated[bool, Form()] = True,
) -> DeliverableUploadResponse:
    """Upload a single deliverable for an assignment."""
    deliverable_service = DeliverableService()

    try:
        str_filename = str(file.filename)
        is_valid, error_msg = deliverable_service.validate_file_format(
            str_filename, file.content_type or DEFAULT_CONTENT_TYPE
        )
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_msg)

        content = await file.read()
        extension = str_filename.split(".")[-1] if "." in str_filename else ""

        deliverable_id = deliverable_service.upload_deliverable(
            assignment_id=assignment_id,
            filename=str_filename,
            content=content,
            extension=extension,
            content_type=file.content_type or DEFAULT_CONTENT_TYPE,
            extract_name=extract_name,
        )

        deliverable = deliverable_service.get_deliverable(deliverable_id)
        if not deliverable:
            raise HTTPException(status_code=500, detail="Failed to retrieve uploaded deliverable")

        return DeliverableUploadResponse(
            id=deliverable_id,
            filename=deliverable.filename,
            student_name=deliverable.student_name,
            uploaded_at=deliverable.uploaded_at.isoformat(),
            message="Deliverable uploaded successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload deliverable") from e


async def prepare_file_data(
    file: UploadFile, deliverable_service: DeliverableService
) -> tuple[str, bytes, str, str] | None:
    """Prepare file data for upload if valid.

    Returns tuple of (filename, content, extension, content_type) or None if invalid.
    """
    if not file.filename:
        return None

    content_type = file.content_type or DEFAULT_CONTENT_TYPE
    is_valid, _ = deliverable_service.validate_file_format(file.filename, content_type)

    if not is_valid:
        return None

    content = await file.read()
    extension = file.filename.split(".")[-1] if "." in file.filename else ""
    return (file.filename, content, extension, content_type)


def create_deliverable_response(
    deliverable_id: str, deliverable_service: DeliverableService
) -> DeliverableUploadResponse | None:
    """Create a DeliverableUploadResponse from a deliverable ID.

    Returns the response or None if deliverable not found.
    """
    deliverable = deliverable_service.get_deliverable(deliverable_id)
    if not deliverable:
        return None

    return DeliverableUploadResponse(
        id=deliverable_id,
        filename=deliverable.filename,
        student_name=deliverable.student_name,
        uploaded_at=deliverable.uploaded_at.isoformat(),
        message="Uploaded successfully",
    )


@app.post(
    "/assignments/{assignment_id}/deliverables/bulk",
    response_model=BulkDeliverableUploadResponse,
    tags=["Deliverables"],
)
async def upload_multiple_deliverables(
    assignment_id: str,
    files: Annotated[list[UploadFile], File(...)],
    extract_names: Annotated[bool, Form()] = True,
) -> BulkDeliverableUploadResponse:
    """Upload multiple deliverables for an assignment."""
    deliverable_service = DeliverableService()

    try:
        files_data: list[Any] = []
        for file in files:
            file_data = await prepare_file_data(file, deliverable_service)
            if file_data:
                files_data.append(file_data)

        if not files_data:
            raise HTTPException(status_code=422, detail="No valid files provided")

        deliverable_ids = deliverable_service.upload_multiple_deliverables(
            assignment_id=assignment_id, files=files_data, extract_names=extract_names
        )

        uploaded_deliverables: list[DeliverableUploadResponse] = []
        for deliverable_id in deliverable_ids:
            response = create_deliverable_response(deliverable_id, deliverable_service)
            if response:
                uploaded_deliverables.append(response)

        return BulkDeliverableUploadResponse(
            deliverables=uploaded_deliverables,
            total_uploaded=len(uploaded_deliverables),
            message=f"Successfully uploaded {len(uploaded_deliverables)} deliverable(s)",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload deliverables") from e


@app.get("/assignments/{assignment_id}/deliverables", response_model=DeliverableListResponse, tags=["Deliverables"])
async def list_deliverables(assignment_id: str) -> DeliverableListResponse:
    """List all deliverables for an assignment."""
    deliverable_service = DeliverableService()

    try:
        deliverables = deliverable_service.list_deliverables(assignment_id)

        deliverable_responses = [
            DeliverableResponse(
                id=str(deliverable.id),
                assignment_id=str(deliverable.assignment_id),
                student_name=deliverable.student_name,
                mark=deliverable.mark,
                mark_status="Marked" if deliverable.mark is not None else "Unmarked",
                certainty_threshold=deliverable.certainty_threshold,
                filename=deliverable.filename,
                extension=deliverable.extension,
                content_type=deliverable.content_type,
                file_url=f"/api/deliverables/{deliverable.id}/download",
                uploaded_at=deliverable.uploaded_at.isoformat(),
                updated_at=deliverable.updated_at.isoformat(),
            )
            for deliverable in deliverables
        ]

        return DeliverableListResponse(deliverables=deliverable_responses, total=len(deliverable_responses))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list deliverables") from e


@app.patch("/deliverables/{deliverable_id}", response_model=DeliverableResponse, tags=["Deliverables"])
async def update_deliverable(deliverable_id: str, request: UpdateDeliverableRequest) -> DeliverableResponse:
    """Update a deliverable's information."""
    deliverable_service = DeliverableService()

    try:
        success = deliverable_service.update_deliverable(
            deliverable_id=deliverable_id,
            student_name=request.student_name,
            mark=request.mark,
            certainty_threshold=request.certainty_threshold,
        )

        if not success:
            raise HTTPException(status_code=404, detail=DELIVERABLE_NOT_FOUND)

        deliverable = deliverable_service.get_deliverable(deliverable_id)
        if not deliverable:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated deliverable")

        return DeliverableResponse(
            id=str(deliverable.id),
            assignment_id=str(deliverable.assignment_id),
            student_name=deliverable.student_name,
            mark=deliverable.mark,
            mark_status="Marked" if deliverable.mark is not None else "Unmarked",
            certainty_threshold=deliverable.certainty_threshold,
            filename=deliverable.filename,
            extension=deliverable.extension,
            content_type=deliverable.content_type,
            file_url=f"/api/deliverables/{deliverable.id}/download",
            uploaded_at=deliverable.uploaded_at.isoformat(),
            updated_at=deliverable.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update deliverable") from e


@app.delete("/deliverables/{deliverable_id}", response_model=DeleteResponse, tags=["Deliverables"])
async def delete_deliverable(deliverable_id: str) -> DeleteResponse:
    """Delete a deliverable."""
    deliverable_service = DeliverableService()

    try:
        success = deliverable_service.delete_deliverable(deliverable_id)

        if not success:
            raise HTTPException(status_code=404, detail=DELIVERABLE_NOT_FOUND)

        return DeleteResponse(message="Deliverable deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete deliverable") from e


@app.get("/deliverables/{deliverable_id}/download", tags=["Deliverables"])
async def download_deliverable(deliverable_id: str) -> StreamingResponse:
    """Download a deliverable file."""
    deliverable_service = DeliverableService()

    try:
        deliverable = deliverable_service.get_deliverable(deliverable_id)
        if not deliverable:
            raise HTTPException(status_code=404, detail=DELIVERABLE_NOT_FOUND)

        return StreamingResponse(
            io.BytesIO(deliverable.content),
            media_type=deliverable.content_type,
            headers={"Content-Disposition": f"inline; filename={deliverable.filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to download deliverable") from e
