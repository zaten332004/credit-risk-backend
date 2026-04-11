"""
Admin service: business logic for admin management
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import UserDB, RoleDB
from app.db.session import SessionLocal
from app.schemas.schemas import UserRead


def list_users_with_filters(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
) -> List[UserRead]:
    """
    Get all users with optional filters
    """
    db = SessionLocal()
    try:
        query = db.query(UserDB)
        
        # Filter by user_id
        if user_id:
            query = query.filter(UserDB.user_id == user_id)
        
        # Filter by exact username
        if username:
            query = query.filter(UserDB.username == username)
        
        # Search in username or email (contains)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (UserDB.username.ilike(search_pattern)) | 
                (UserDB.email.ilike(search_pattern))
            )
        
        users = query.all()
        return [
            UserRead(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                role_id=user.role_id,
                created_at=user.created_at,
                rejection_reason=(user.rejection_reason or "").strip() or None,
            )
            for user in users
        ]
    finally:
        db.close()


def approve_user(user_id: int, approved_by: int) -> bool:
    """
    Approve a user registration (change status to 'approved')
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not user:
            return False
        
        user.status = "approved"
        user.approved_by = approved_by
        user.approved_at = datetime.utcnow()
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error approving user: {str(e)}")
        return False
    finally:
        db.close()


def reject_user(user_id: int, reason: str) -> bool:
    """
    Reject a user registration (change status to 'rejected')
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not user:
            return False
        
        user.status = "rejected"
        user.rejection_reason = reason
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error rejecting user: {str(e)}")
        return False
    finally:
        db.close()


def toggle_user_status(user_id: int, is_active: bool) -> bool:
    """
    Enable or disable a user account
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not user:
            return False
        
        # Update status based on is_active flag
        user.status = "verified" if is_active else "disabled"
        user.updated_at = datetime.utcnow()
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error toggling user status: {str(e)}")
        return False
    finally:
        db.close()

