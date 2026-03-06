"""
File upload & data ingestion endpoints
"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import get_current_active_user
from app.schemas.schemas import JobStatusResponse, UploadJobResponse, User
from app.services import ingestion_service

router = APIRouter()


@router.post("/upload/data", response_model=UploadJobResponse, tags=["ingestion"])
async def upload_data_endpoint(
    file: UploadFile = File(...),
    type: str = "customers",  # type: ignore[assignment]
    current_user: User = Depends(get_current_active_user),
) -> UploadJobResponse:
    # Demo: chưa parse file; chỉ tạo job
    return ingestion_service.create_upload_job(type)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["ingestion"])
async def job_status_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
) -> JobStatusResponse:
    return ingestion_service.get_job_status(job_id)
