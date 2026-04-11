from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import UploadFile

from app.core.config import settings
from app.core.security import normalize_role_name, pwd_context, verify_password
from app.db.models import RoleDB, UserDB
from app.schemas.schemas import ProfileRead, ProfileUpdateBody
from app.services.audit_service import log_action
from app.services.email_service import EmailService


EMAIL_CHANGE_TOKEN_PREFIX = "email-change"
EMAIL_CHANGE_CODE_EXPIRES_MINUTES = 10
LEGACY_AVATAR_STORAGE_DIR = Path(__file__).resolve().parents[2] / ".uploads" / "avatars"
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024


def _avatar_storage_dir() -> Path:
    configured = (settings.AVATAR_STORAGE_DIR or "").strip()
    if not configured:
        return LEGACY_AVATAR_STORAGE_DIR
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[2] / path).resolve()


def _resolve_role_name(user: UserDB, role_name: Optional[str]) -> str:
    if role_name:
        return normalize_role_name(role_name)
    if user.user_type:
        return normalize_role_name(user.user_type)
    return "viewer"


def _safe_avatar_version(user: UserDB) -> str:
    marker = user.updated_at or user.created_at
    if not marker:
        return "0"
    return str(int(marker.timestamp()))


def _build_avatar_url(user: UserDB) -> Optional[str]:
    if not getattr(user, "avatar_path", None):
        return None
    return f"/api/v1/profile/avatar/me?v={_safe_avatar_version(user)}"


def _to_profile_read(user: UserDB, role_name: Optional[str]) -> ProfileRead:
    return ProfileRead(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=_build_avatar_url(user),
        role=_resolve_role_name(user, role_name),
        status=user.status,
        is_email_verified=bool(user.is_email_verified),
        created_at=user.created_at,
    )


def _get_user_and_role(db: Session, user_id: int) -> tuple[UserDB, Optional[str]] | tuple[None, None]:
    row = (
        db.query(UserDB, RoleDB.role_name)
        .outerjoin(RoleDB, RoleDB.role_id == UserDB.role_id)
        .filter(UserDB.user_id == user_id)
        .first()
    )
    if not row:
        return None, None
    user, role_name = row
    return user, role_name


def get_profile(db: Session, user_id: int) -> Optional[ProfileRead]:
    user, role_name = _get_user_and_role(db, user_id)
    if not user:
        return None
    return _to_profile_read(user, role_name)


def update_profile(db: Session, user_id: int, body: ProfileUpdateBody) -> Optional[ProfileRead]:
    user, role_name = _get_user_and_role(db, user_id)
    if not user:
        return None

    old_value = {
        "full_name": user.full_name,
        "phone": user.phone,
    }

    user.full_name = (body.full_name or "").strip() or None
    user.phone = (body.phone or "").strip() or None
    user.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=user.user_id,
        action="UPDATE_PROFILE",
        entity_type="UserProfile",
        entity_id=user.user_id,
        old_value=old_value,
        new_value={
            "full_name": user.full_name,
            "phone": user.phone,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
    )
    db.commit()
    db.refresh(user)
    return _to_profile_read(user, role_name)


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found"

    if not verify_password(current_password, user.password_hash):
        return False, "Current password is incorrect"

    if current_password.strip() == new_password.strip():
        return False, "New password must be different from the current password"

    user.password_hash = pwd_context.hash(new_password)
    user.updated_at = datetime.utcnow()
    log_action(
        db,
        user_id=user.user_id,
        action="CHANGE_PASSWORD",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={"updated_at": user.updated_at.isoformat() if user.updated_at else None},
    )
    db.commit()
    return True, "Password updated successfully"


def _build_email_change_token(new_email: str, code: str) -> str:
    return f"{EMAIL_CHANGE_TOKEN_PREFIX}::{new_email}::{code}"


def _parse_email_change_token(raw_token: Optional[str]) -> tuple[str, str] | tuple[None, None]:
    token = (raw_token or "").strip()
    parts = token.split("::")
    if len(parts) != 3 or parts[0] != EMAIL_CHANGE_TOKEN_PREFIX:
        return None, None
    return parts[1], parts[2]


def request_email_change(db: Session, user_id: int, new_email: str) -> tuple[bool, str, Optional[str], Optional[int]]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found", None, None

    normalized_email = (new_email or "").strip().lower()
    if not normalized_email:
        return False, "New email is required", None, None

    if normalized_email == (user.email or "").strip().lower():
        return False, "New email must be different from the current email", None, None

    existing = (
        db.query(UserDB)
        .filter(func.lower(UserDB.email) == normalized_email, UserDB.user_id != user.user_id)
        .first()
    )
    if existing:
        return False, "Email already exists", None, None

    verification_code = f"{secrets.randbelow(1_000_000):06d}"
    user.verification_token = _build_email_change_token(normalized_email, verification_code)
    user.verification_sent_at = datetime.utcnow()

    email_sent = EmailService.send_email_change_code(
        recipient_email=(user.email or "").strip().lower(),
        verification_code=verification_code,
        full_name=user.full_name or user.username,
    )
    if not email_sent:
        db.rollback()
        return False, "Could not send verification code", None, None

    expires_in_seconds = EMAIL_CHANGE_CODE_EXPIRES_MINUTES * 60
    log_action(
        db,
        user_id=user.user_id,
        action="REQUEST_EMAIL_CHANGE",
        entity_type="UserProfile",
        entity_id=user.user_id,
        old_value={"email": user.email},
        new_value={
            "pending_email": normalized_email,
            "verification_sent_at": user.verification_sent_at.isoformat() if user.verification_sent_at else None,
        },
    )
    db.commit()
    return True, "Verification code sent successfully", normalized_email, expires_in_seconds


def confirm_email_change(db: Session, user_id: int, code: str) -> tuple[bool, str, Optional[ProfileRead]]:
    user, role_name = _get_user_and_role(db, user_id)
    if not user:
        return False, "User not found", None

    pending_email, stored_code = _parse_email_change_token(user.verification_token)
    if not pending_email or not stored_code:
        return False, "No email change request found", None

    if not user.verification_sent_at:
        return False, "Verification code expired", None

    expires_at = user.verification_sent_at + timedelta(minutes=EMAIL_CHANGE_CODE_EXPIRES_MINUTES)
    if expires_at < datetime.utcnow():
        return False, "Verification code expired", None

    normalized_code = (code or "").strip()
    if normalized_code != stored_code:
        return False, "Verification code is incorrect", None

    existing = (
        db.query(UserDB)
        .filter(func.lower(UserDB.email) == pending_email.lower(), UserDB.user_id != user.user_id)
        .first()
    )
    if existing:
        return False, "Email already exists", None

    old_email = user.email
    user.email = pending_email
    user.is_email_verified = True
    user.verification_token = None
    user.verification_sent_at = None
    user.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=user.user_id,
        action="CHANGE_EMAIL",
        entity_type="UserProfile",
        entity_id=user.user_id,
        old_value={"email": old_email},
        new_value={
            "email": user.email,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
    )
    db.commit()
    db.refresh(user)
    return True, "Email updated successfully", _to_profile_read(user, role_name)


def update_avatar(db: Session, user_id: int, file: UploadFile) -> tuple[bool, str, Optional[ProfileRead]]:
    user, role_name = _get_user_and_role(db, user_id)
    if not user:
        return False, "User not found", None

    filename = (file.filename or "").strip()
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        return False, "Only JPG, PNG, and WEBP images are supported", None

    content = file.file.read()
    if not content:
        return False, "Avatar file is empty", None
    if len(content) > MAX_AVATAR_SIZE_BYTES:
        return False, "Avatar must be smaller than 5MB", None

    storage_dir = _avatar_storage_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"user-{user.user_id}-{uuid4().hex[:12]}{extension}"
    target_path = storage_dir / stored_name
    target_path.write_bytes(content)

    old_avatar_path = user.avatar_path
    user.avatar_path = stored_name
    user.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=user.user_id,
        action="UPDATE_AVATAR",
        entity_type="UserProfile",
        entity_id=user.user_id,
        old_value={"avatar_path": old_avatar_path},
        new_value={
            "avatar_path": stored_name,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
    )

    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        return False, "Could not save avatar in the database", None

    if old_avatar_path:
        old_safe_name = Path(old_avatar_path).name
        old_path = storage_dir / old_safe_name
        if (not old_path.exists()) and storage_dir != LEGACY_AVATAR_STORAGE_DIR:
            old_path = LEGACY_AVATAR_STORAGE_DIR / old_safe_name
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    return True, "Avatar updated successfully", _to_profile_read(user, role_name)


def get_avatar_file_path(db: Session, user_id: int) -> Optional[Path]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user or not getattr(user, "avatar_path", None):
        return None

    safe_name = Path(user.avatar_path).name
    primary = _avatar_storage_dir() / safe_name
    fallback = LEGACY_AVATAR_STORAGE_DIR / safe_name
    for file_path in (primary, fallback):
        if file_path.exists() and file_path.is_file():
            return file_path
    return None
