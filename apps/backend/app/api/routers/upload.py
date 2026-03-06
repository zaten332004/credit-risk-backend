"""
Upload Router - FastAPI endpoints for file upload and processing
Endpoints: POST /upload, GET /upload/status
"""

import os
import uuid
from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.services.upload_service import UploadService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])

# Response Models
class UploadResponse(BaseModel):
    success: bool
    message: str
    upload_id: str
    file_name: str
    rows_processed: int
    customers_created: int = 0
    applications_created: int = 0
    facilities_created: int = 0
    processing_time_seconds: float
    errors: list = []
    
    class Config:
        from_attributes = True


class UploadStatusResponse(BaseModel):
    upload_id: str
    status: str  # pending, processing, completed, failed
    message: str
    progress_percent: int = 0
    file_name: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# In-memory upload tracking (in production, use database)
upload_status_store = {}


@router.post("/", response_model=UploadResponse, summary="Upload CSV file for processing")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    limit_rows: Optional[int] = None,
    db: Session = Depends(SessionLocal),
    current_user = Depends(get_current_user)
) -> UploadResponse:
    """
    Upload a CSV file for ETL processing and risk analysis
    
    **Parameters:**
    - `file`: CSV file to upload (required)
    - `limit_rows`: Optional row limit for testing (default: all rows)
    
    **Returns:**
    - UploadResponse with processing results
    
    **Example:**
    ```
    POST /api/upload
    Content-Type: multipart/form-data
    
    file: <your_file.csv>
    limit_rows: 1000
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Successfully uploaded and processed 1000 records",
        "upload_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_name": "sales_data.csv",
        "rows_processed": 1000,
        "customers_created": 150,
        "applications_created": 1000,
        "facilities_created": 1000,
        "processing_time_seconds": 12.5,
        "errors": []
    }
    ```
    """
    
    start_time = datetime.now()
    upload_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{file_ext}'. Allowed: .csv, .xlsx, .xls"
            )
        
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{upload_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)
        
        logger.info(f"File uploaded: {file_path} (Size: {len(contents)} bytes)")
        
        # Track upload status
        upload_status_store[upload_id] = {
            'status': 'processing',
            'file_name': file.filename,
            'created_at': start_time,
            'progress_percent': 10
        }
        
        # Process file (in background or foreground for demo)
        process_result = await UploadService.process_upload(
            db=db,
            file_path=file_path,
            limit_rows=limit_rows
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Update upload status
        upload_status_store[upload_id].update({
            'status': 'completed' if process_result['success'] else 'failed',
            'message': process_result['message'],
            'completed_at': datetime.now(),
            'progress_percent': 100
        })
        
        # Return response
        return UploadResponse(
            success=process_result['success'],
            message=process_result['message'],
            upload_id=upload_id,
            file_name=file.filename,
            rows_processed=process_result['rows_processed'],
            customers_created=process_result['counts'].get('customers', 0),
            applications_created=process_result['counts'].get('applications', 0),
            facilities_created=process_result['counts'].get('facilities', 0),
            processing_time_seconds=processing_time,
            errors=process_result['errors']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        
        upload_status_store[upload_id] = {
            'status': 'failed',
            'message': str(e),
            'completed_at': datetime.now(),
            'progress_percent': 0
        }
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing upload: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Temporary file deleted: {file_path}")
        except:
            pass


@router.get("/status/{upload_id}", response_model=UploadStatusResponse, summary="Check upload status")
async def check_upload_status(upload_id: str) -> UploadStatusResponse:
    """
    Check the status of an ongoing upload
    
    **Parameters:**
    - `upload_id`: Upload ID from upload response
    
    **Returns:**
    - UploadStatusResponse with current status
    
    **Example:**
    ```
    GET /api/upload/status/550e8400-e29b-41d4-a716-446655440000
    ```
    
    **Response:**
    ```json
    {
        "upload_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "message": "Successfully uploaded and processed 1000 records",
        "progress_percent": 100,
        "file_name": "sales_data.csv",
        "created_at": "2026-01-28T10:30:00",
        "completed_at": "2026-01-28T10:30:15"
    }
    ```
    """
    
    if upload_id not in upload_status_store:
        raise HTTPException(
            status_code=404,
            detail=f"Upload ID '{upload_id}' not found"
        )
    
    status_info = upload_status_store[upload_id]
    
    return UploadStatusResponse(
        upload_id=upload_id,
        status=status_info.get('status', 'unknown'),
        message=status_info.get('message', ''),
        progress_percent=status_info.get('progress_percent', 0),
        file_name=status_info.get('file_name'),
        created_at=status_info.get('created_at'),
        completed_at=status_info.get('completed_at')
    )


@router.get("/", response_model=dict, summary="Get upload information")
async def get_upload_info(
    current_user = Depends(get_current_user)
) -> dict:
    """
    Get information about the upload service
    
    **Returns:**
    - Dictionary with service information
    
    **Example:**
    ```
    GET /api/upload
    ```
    
    **Response:**
    ```json
    {
        "service": "File Upload & ETL Processing",
        "supported_formats": [".csv", ".xlsx", ".xls"],
        "max_file_size_mb": 50,
        "max_rows_per_file": null,
        "endpoints": [
            "POST /api/upload - Upload and process file",
            "GET /api/upload/status/{upload_id} - Check upload status"
        ],
        "recent_uploads": 5,
        "active_uploads": 0
    }
    ```
    """
    
    return {
        "service": "File Upload & ETL Processing",
        "supported_formats": [".csv", ".xlsx", ".xls"],
        "max_file_size_mb": 50,
        "max_rows_per_file": None,
        "endpoints": [
            "POST /api/upload - Upload and process file",
            "GET /api/upload/status/{upload_id} - Check upload status",
            "GET /api/upload - Get service information"
        ],
        "recent_uploads": len(upload_status_store),
        "active_uploads": sum(1 for s in upload_status_store.values() if s.get('status') == 'processing')
    }
