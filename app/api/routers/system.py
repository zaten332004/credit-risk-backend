"""
System endpoints: health check, metrics
"""
from fastapi import APIRouter

from app.schemas.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Health check endpoint - public, no auth required"""
    # db_ok ở đây demo = True; thực tế nên ping DB
    return HealthResponse(status="ok", version="v1", db_ok=True)
