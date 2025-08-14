from pydantic import BaseModel
from typing import List, Optional

class ServiceHealth(BaseModel):
    service: str
    status: str
    details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    services: List[ServiceHealth]
