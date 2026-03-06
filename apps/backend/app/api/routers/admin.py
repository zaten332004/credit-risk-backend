"""
Admin & system management endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_admin_user
from app.schemas.schemas import User, UserRead
from app.services import admin_service

router = APIRouter()


@router.get("/admin/users", response_model=List[UserRead], tags=["admin"])
async def admin_list_users(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
) -> List[UserRead]:
    """
    Get all users with optional filters:
    - user_id: Filter by user ID
    - username: Filter by username (exact match)
    - search: Search by username or email (contains)
    """
    return admin_service.list_users_with_filters(user_id=user_id, username=username, search=search)


@router.put("/admin/users/{user_id}/approve", response_model=dict, tags=["admin"])
async def admin_approve_manager(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    """
    Approve a manager registration request
    """
    result = admin_service.approve_user(user_id, approved_by=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User approved successfully", "user_id": user_id}


@router.put("/admin/users/{user_id}/reject", response_model=dict, tags=["admin"])
async def admin_reject_manager(
    user_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    """
    Reject a manager registration request
    """
    result = admin_service.reject_user(user_id, reason=reason or "Rejected by admin")
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User rejected successfully", "user_id": user_id}


@router.put("/admin/users/{user_id}/status", response_model=dict, tags=["admin"])
async def admin_toggle_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    """
    Enable or disable user account
    - is_active=true: Allow user to continue using the app
    - is_active=false: Disable user account
    """
    result = admin_service.toggle_user_status(user_id, is_active=is_active)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    status_text = "enabled" if is_active else "disabled"
    return {"message": f"User {status_text} successfully", "user_id": user_id, "is_active": is_active}

