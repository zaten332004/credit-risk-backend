"""
Admin service: business logic for admin & system management.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.models import AuditLogDB, UserDB
from app.schemas.schemas import ExportRequestBody, ExportResponse, UserCreate


def list_users(
    db: Session,
    *,
    user_id: int | None = None,
    name: str | None = None,
    name_contains: str | None = None,
    keyword: str | None = None,
) -> List[UserDB]:
    """
    List users with optional filters:
    - user_id: exact match
    - name: exact match on full_name or username
    - name_contains/keyword: substring match on full_name (and username/email for convenience)
    """
    query = db.query(UserDB)

    if user_id is not None:
        query = query.filter(UserDB.user_id == user_id)

    if name:
        query = query.filter(or_(UserDB.full_name == name, UserDB.username == name))

    search_term = name_contains or keyword
    if search_term:
        search = f"%{search_term}%"
        query = query.filter(
            or_(
                UserDB.full_name.ilike(search),
                UserDB.username.ilike(search),
                UserDB.email.ilike(search),
            )
        )

    return query.order_by(UserDB.user_id.asc()).all()


def create_user(db: Session, user: UserCreate) -> UserDB:
    existing_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = UserDB(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
        role_id=user.role_id,
        is_email_verified=True,
        status="approved",
        created_at=datetime.utcnow(),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def toggle_user_status(db: Session, user_id: int, is_active: bool) -> UserDB:
    """Enable/disable a user account for application access."""
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = is_active

    # Keep registration workflow statuses intact; only mark banned for already-approved users.
    if not is_active and user.status == "approved":
        user.status = "banned"
    elif is_active and user.status == "banned":
        user.status = "approved"

    db.commit()
    db.refresh(user)
    return user


def list_audit_logs(
    db: Session,
    from_date: Optional[str],
    to_date: Optional[str],
    user_id: Optional[int],
) -> List[AuditLogDB]:
    query = db.query(AuditLogDB)

    if user_id:
        query = query.filter(AuditLogDB.user_id == user_id)

    if from_date:
        query = query.filter(AuditLogDB.performed_at >= from_date)
    if to_date:
        query = query.filter(AuditLogDB.performed_at <= to_date)

    return query.order_by(AuditLogDB.performed_at.desc()).limit(100).all()


def export_data(body: ExportRequestBody) -> ExportResponse:
    return ExportResponse(file_url="https://example-bucket.s3.amazonaws.com/export/demo.csv")

