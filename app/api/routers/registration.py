"""
Registration API Endpoints
User registration, email verification, and manager approval
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_active_user, get_current_admin_user
from app.db.models import UserDB
from app.db.session import SessionLocal
from app.schemas.schemas import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserRegistrationApprovalRequest,
    UserRegistrationResendRequest,
    UserRegistrationRead,
    User,
)
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/auth/register", tags=["registration"])


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/signup", response_model=UserRegistrationResponse, status_code=201)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register new user (analyst or manager)
    
    **registration_type**: 'analyst' or 'manager'
    - analyst: Auto-approved after email verification
    - manager: Requires admin approval after email verification
    
    **Response includes:**
    - verification_token: Token for email verification (for testing)
    - verification_link: Full URL to verify email (click in email)
    - message: Instructions for user
    """
    success, message, response = RegistrationService.register_user(db, request)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Treat signup success as authenticated pending session.
    access_token = create_access_token(
        data={
            "sub": response.email,
            "role": response.role or response.registration_type,
            "status": response.status,
        }
    )
    response.access_token = access_token
    response.role = response.role or response.registration_type
    response.has_pin = False

    return response


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user email with token
    Token should be sent via email link
    """
    success, message = RegistrationService.verify_email(db, token)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message, "status": "verified"}


@router.get("/me/status")
async def get_my_registration_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Current user's registration row (status + rejection_reason). For pending/rejected users on the verify flow;
    does not require admin (unlike GET /registration/{user_id}).
    """
    row = db.query(UserDB).filter(UserDB.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    reason = (row.rejection_reason or "").strip()
    return {
        "user_id": int(row.user_id),
        "status": str(row.status or "pending").strip().lower() or "pending",
        "rejection_reason": reason or None,
    }


@router.post("/resend-verification")
async def resend_verification_email(
    request: UserRegistrationResendRequest,
    db: Session = Depends(get_db)
):
    """
    Resend verification email for a pending registration
    """
    success, message = RegistrationService.resend_verification_email(db, request.email)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message, "status": "resent"}


@router.get("/list", response_model=list[UserRegistrationRead])
async def list_registrations(
    reg_type: str | None = None,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get registrations for admin review.
    """
    registrations = RegistrationService.list_registrations(db, reg_type, status_filter)
    return registrations


@router.post("/approve")
async def approve_registration(
    request: UserRegistrationApprovalRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject manager registration (admin only)
    """
    # Approve/reject registration
    success, message = RegistrationService.approve_registration(
        db,
        request.registration_id,  # This is now the user_id
        current_user.id,
        request.action,
        request.rejection_reason
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message, "status": request.action}


@router.get("/registration/{user_id}", response_model=UserRegistrationRead)
async def get_registration(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user registration details (admin only)"""
    user = RegistrationService.get_registration_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
