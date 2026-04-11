from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import UserDB
from app.services.audit_service import log_action
from app.services import account_pin_service


def request_password_reset(db: Session, email: str) -> tuple[bool, str]:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return False, "Email is required"

    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    if not user:
        return True, "If the email exists, use your account PIN to reset password."

    if not (user.pin_hash or "").strip():
        return False, "Account PIN is not set. Contact admin to set PIN first."

    log_action(
        db,
        user_id=user.user_id,
        action="REQUEST_PASSWORD_RESET",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={
            "email": user.email,
            "method": "pin",
        },
    )
    db.commit()
    return True, "Use your 6-digit PIN to reset password."


def confirm_password_reset(db: Session, email: str, code: str, new_password: str) -> tuple[bool, str]:
    try:
        return account_pin_service.reset_password_with_pin(db, email=email, pin=code, new_password=new_password)
    except ValueError as exc:
        db.rollback()
        return False, str(exc)
