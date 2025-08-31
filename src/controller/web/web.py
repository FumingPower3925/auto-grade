import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from src.service.assignment_service import AssignmentService

app = APIRouter()
templates = Jinja2Templates(directory="src/view")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = "static/img/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Home page with assignment list."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/assignments", response_class=HTMLResponse)
async def assignments_list(request: Request):
    """Get assignments list as HTML fragment for HTMX."""
    assignment_service = AssignmentService()
    
    try:
        assignments = assignment_service.list_assignments()
        return templates.TemplateResponse(
            "templates/assignment_cards.html",
            {
                "request": request,
                "assignments": assignments
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "templates/assignment_cards.html",
            {
                "request": request,
                "assignments": [],
                "error": str(e)
            }
        )

@app.get("/assignments/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(request: Request, assignment_id: str):
    """Assignment detail page."""
    assignment_service = AssignmentService()
    
    try:
        assignment = assignment_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        rubrics = assignment_service.list_rubrics(assignment_id)
        documents = assignment_service.list_relevant_documents(assignment_id)
        
        return templates.TemplateResponse(
            "assignment_detail.html",
            {
                "request": request,
                "assignment": assignment,
                "rubrics": rubrics,
                "documents": documents,
                "assignment_id": assignment_id
            }
        )
    except HTTPException:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "Assignment not found"}
        )