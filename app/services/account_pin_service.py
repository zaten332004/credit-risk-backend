from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import normalize_role_name, pwd_context
from app.db.models import RoleDB, UserDB
from app.services.audit_service import log_action


def _normalize_pin(pin: str) -> str:
    value = (pin or "").strip()
    if len(value) != 6 or not value.isdigit():
        raise ValueError("PIN must be exactly 6 digits")
    return value


def _resolve_role_name(db: Session, role_id: Optional[int]) -> str:
    if role_id is None:
        return "viewer"
    role = db.query(RoleDB).filter(RoleDB.role_id == role_id).first()
    return normalize_role_name(role.role_name if role else "viewer")


def _resolve_pending_role(db: Session, user: UserDB) -> str:
    if user.role_id is not None:
        return _resolve_role_name(db, user.role_id)

    requested_type = (user.user_type or "").strip().lower()
    if requested_type in {"analyst", "manager", "admin", "viewer"}:
        return requested_type
    return "viewer"


def get_pending_account_status(db: Session, user_id: int) -> dict:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        raise ValueError("User not found")

    reason = (user.rejection_reason or "").strip()
    return {
        "user_id": int(user.user_id),
        "email": str(user.email or ""),
        "role": _resolve_pending_role(db, user),
        "status": str((user.status or "pending")).strip().lower() or "pending",
        "has_pin": bool((user.pin_hash or "").strip()),
        "rejection_reason": reason or None,
    }


def set_account_pin(db: Session, user_id: int, pin: str) -> tuple[bool, str]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found"
    if (user.pin_hash or "").strip():
        return False, "PIN already exists. Use change PIN endpoint."

    normalized = _normalize_pin(pin)
    user.pin_hash = pwd_context.hash(normalized)
    user.pin_updated_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=user.user_id,
        action="SET_PIN",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={"pin_updated_at": user.pin_updated_at.isoformat()},
    )
    db.commit()
    return True, "PIN set successfully"


def change_account_pin(db: Session, user_id: int, old_pin: str, new_pin: str) -> tuple[bool, str]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found"
    if not (user.pin_hash or "").strip():
        return False, "PIN is not set"

    old_value = _normalize_pin(old_pin)
    new_value = _normalize_pin(new_pin)
    if old_value == new_value:
        return False, "New PIN must be different from old PIN"
    if not pwd_context.verify(old_value, user.pin_hash):
        return False, "Current PIN is incorrect"

    user.pin_hash = pwd_context.hash(new_value)
    user.pin_updated_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    log_action(
        db,
        user_id=user.user_id,
        action="CHANGE_PIN",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={"pin_updated_at": user.pin_updated_at.isoformat()},
    )
    db.commit()
    return True, "PIN changed successfully"


def reset_password_with_pin(db: Session, email: str, pin: str, new_password: str) -> tuple[bool, str]:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return False, "Email is required"

    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    if not user:
        return False, "Invalid email or PIN"
    if not (user.pin_hash or "").strip():
        return False, "PIN is not set for this account"

    normalized_pin = _normalize_pin(pin)
    if not pwd_context.verify(normalized_pin, user.pin_hash):
        return False, "Invalid email or PIN"

    user.password_hash = pwd_context.hash((new_password or "").strip())
    user.updated_at = datetime.utcnow()
    log_action(
        db,
        user_id=user.user_id,
        action="RESET_PASSWORD_WITH_PIN",
        entity_type="UserProfile",
        entity_id=user.user_id,
        new_value={"updated_at": user.updated_at.isoformat()},
    )
    db.commit()
    return True, "Password reset successfully"


def change_email_with_pin(db: Session, user_id: int, new_email: str, pin: str) -> tuple[bool, str]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found"
    if not (user.pin_hash or "").strip():
        return False, "PIN is not set"

    normalized_pin = _normalize_pin(pin)
    if not pwd_context.verify(normalized_pin, user.pin_hash):
        return False, "PIN is incorrect"

    normalized_email = (new_email or "").strip().lower()
    if not normalized_email:
        return False, "New email is required"
    if normalized_email == (user.email or "").strip().lower():
        return False, "New email must be different from current email"

    duplicate = (
        db.query(UserDB)
        .filter(func.lower(UserDB.email) == normalized_email, UserDB.user_id != user.user_id)
        .first()
    )
    if duplicate:
        return False, "Email already exists"

    old_email = user.email
    user.email = normalized_email
    user.updated_at = datetime.utcnow()
    log_action(
        db,
        user_id=user.user_id,
        action="CHANGE_EMAIL_WITH_PIN",
        entity_type="UserProfile",
        entity_id=user.user_id,
        old_value={"email": old_email},
        new_value={"email": user.email, "updated_at": user.updated_at.isoformat()},
    )
    db.commit()
    return True, "Email changed successfully"
