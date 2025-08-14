from fastapi import FastAPI, Response, status
from typing import List

from src.controller.api.models import HealthResponse, ServiceHealth
from src.repository.db.factory import get_db_client
from src.repository.vdb.factory import get_vdb_client
from src.repository.cache.factory import get_cache_client


app = FastAPI(
    title="Auto Grade API",
    description="A PoC of an automatic bulk assignment grader LLM engine",
    version="0.1.0",
    root_path="/api"
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check(response: Response) -> HealthResponse:
    """Health check endpoint to verify API and its dependent services are running."""
    services_health: List[ServiceHealth] = []
    overall_healthy = True

    # Check DB health
    try:
        db_client = get_db_client()
        db_health = db_client.health()
        db_status = db_health.get("status", "unhealthy")
        services_health.append(ServiceHealth(service="database", status=db_status, details=db_health.get("error")))
        if db_status != "healthy":
            overall_healthy = False
    except Exception as e:
        overall_healthy = False
        services_health.append(ServiceHealth(service="database", status="unhealthy", details=str(e)))

    # Check VDB health
    try:
        vdb_client = get_vdb_client()
        vdb_health = vdb_client.health()
        vdb_status = vdb_health.get("status", "unhealthy")
        services_health.append(ServiceHealth(service="vector_db", status=vdb_status, details=vdb_health.get("error")))
        if vdb_status != "healthy":
            overall_healthy = False
    except Exception as e:
        overall_healthy = False
        services_health.append(ServiceHealth(service="vector_db", status="unhealthy", details=str(e)))

    # Check Cache health
    try:
        cache_client = get_cache_client()
        cache_health = cache_client.health()
        cache_status = cache_health.get("status", "unhealthy")
        services_health.append(ServiceHealth(service="cache", status=cache_status, details=cache_health.get("error")))
        if cache_status != "healthy":
            overall_healthy = False
    except Exception as e:
        overall_healthy = False
        services_health.append(ServiceHealth(service="cache", status="unhealthy", details=str(e)))

    # Determine overall status
    overall_status = "healthy" if overall_healthy else "unhealthy"
    if not overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        services=services_health
    )
