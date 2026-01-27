"""
Admin & system management endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_admin_user
from app.schemas.schemas import AuditLogRead, ExportRequestBody, ExportResponse, User, UserCreate, UserRead
from app.services import admin_service

router = APIRouter()


@router.get("/admin/users", response_model=List[UserRead], tags=["admin"])
async def admin_list_users_endpoint(
    current_user: User = Depends(get_current_admin_user),
) -> List[UserRead]:
    return admin_service.list_users()


@router.post("/admin/users", response_model=UserRead, tags=["admin"])
async def admin_create_user_endpoint(
    body: UserCreate,
    current_user: User = Depends(get_current_admin_user),
) -> UserRead:
    return admin_service.create_user(body)


@router.get("/admin/audit-logs", response_model=List[AuditLogRead], tags=["admin"])
async def admin_audit_logs_endpoint(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
) -> List[AuditLogRead]:
    return admin_service.list_audit_logs(from_date, to_date, user_id)


@router.post("/admin/export", response_model=ExportResponse, tags=["admin"])
async def admin_export_endpoint(
    body: ExportRequestBody,
    current_user: User = Depends(get_current_admin_user),
) -> ExportResponse:
    return admin_service.export_data(body)
