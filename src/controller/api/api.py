from fastapi import FastAPI

from src.controller.api.models import HealthResponse


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
    return HealthResponse(
        status="healthy",
        message="Auto Grade API is running"
    )
