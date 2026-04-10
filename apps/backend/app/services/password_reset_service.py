from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import pwd_context
from app.db.models import UserDB
from app.services.audit_service import log_action
from app.services.email_service import EmailService


PASSWORD_RESET_TOKEN_PREFIX = "password-reset"
PASSWORD_RESET_EXPIRES_MINUTES = 10


def _build_password_reset_token(code: str) -> str:
    return f"{PASSWORD_RESET_TOKEN_PREFIX}::{code}"


def _parse_password_reset_token(raw_token: str | None) -> str | None:
    token = (raw_token or "").strip()
    parts = token.split("::")
    if len(parts) != 2 or parts[0] != PASSWORD_RESET_TOKEN_PREFIX:
        return None
    return parts[1]


def request_password_reset(db: Session, email: str) -> tuple[bool, str]:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return False, "Email is required"

    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    if not user:
        return True, "If the email exists, a password reset code has been sent."

    code = f"{secrets.randbelow(1_000_000):06d}"
    user.verification_token = _build_password_reset_token(code)
    user.verification_sent_at = datetime.utcnow()

    email_sent = EmailService.send_password_reset_code(
        recipient_email=user.email,
        verification_code=code,
        full_name=user.full_name or user.username,
    )
    if not email_sent:
        db.rollback()
        return False, "Could not send password reset code"

    log_action(
        db,
        user_id=user.user_id,
        action="REQUEST_PASSWORD_RESET",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={
            "email": user.email,
            "verification_sent_at": user.verification_sent_at.isoformat() if user.verification_sent_at else None,
        },
    )
    db.commit()
    return True, "If the email exists, a password reset code has been sent."


def confirm_password_reset(db: Session, email: str, code: str, new_password: str) -> tuple[bool, str]:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return False, "Email is required"

    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    if not user:
        return False, "Invalid email or verification code"

    stored_code = _parse_password_reset_token(user.verification_token)
    if not stored_code or not user.verification_sent_at:
        return False, "No password reset request found"

    expires_at = user.verification_sent_at + timedelta(minutes=PASSWORD_RESET_EXPIRES_MINUTES)
    if expires_at < datetime.utcnow():
        return False, "Verification code expired"

    if (code or "").strip() != stored_code:
        return False, "Invalid email or verification code"

    user.password_hash = pwd_context.hash(new_password)
    user.verification_token = None
    user.verification_sent_at = None
    user.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=user.user_id,
        action="RESET_PASSWORD",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={"updated_at": user.updated_at.isoformat() if user.updated_at else None},
    )
    db.commit()
    return True, "Password reset successfully"
