"""
Ingestion service: business logic for file upload & data ingestion
"""
import uuid
from typing import Dict

from app.models.models import UploadJob
from app.schemas.schemas import JobStatusResponse, UploadJobResponse

# In-memory "repository" cho demo
_upload_jobs: Dict[str, UploadJob] = {}


def create_upload_job(job_type: str) -> UploadJobResponse:
    job_id = str(uuid.uuid4())
    job = UploadJob(job_id=job_id, status="pending", progress=0.0, result_url=None)
    _upload_jobs[job_id] = job
    return UploadJobResponse(job_id=job_id, status=job.status)


def get_job_status(job_id: str) -> JobStatusResponse:
    job = _upload_jobs.get(job_id)
    if not job:
        return JobStatusResponse(job_id=job_id, progress=0.0, result_url=None)
    return JobStatusResponse(job_id=job.job_id, progress=job.progress, result_url=job.result_url)
