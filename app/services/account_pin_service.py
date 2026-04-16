from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import normalize_role_name, pwd_context
from app.db.models import AuditLogDB, RoleDB, UserDB
from app.services.audit_service import log_action

PIN_RESET_ENTITY = "PinResetRequest"
PIN_RESET_REQUEST_ACTION = "REQUEST_PIN_RESET"
PIN_RESET_APPROVE_ACTION = "APPROVE_PIN_RESET_REQUEST"
PIN_RESET_REJECT_ACTION = "REJECT_PIN_RESET_REQUEST"


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


def _is_user_active(user: UserDB) -> bool:
    if getattr(user, "is_active", True) is False:
        return False
    return str((user.status or "")).strip().lower() != "disabled"


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
        "is_active": _is_user_active(user),
        "rejection_reason": reason or None,
    }


def _pin_reset_subject_user_id(log: AuditLogDB) -> Optional[int]:
    raw_id = log.entity_id if log.entity_id is not None else log.user_id
    try:
        return int(raw_id) if raw_id is not None else None
    except Exception:
        return None


def has_pending_pin_reset_request(db: Session, user_id: int) -> bool:
    latest = (
        db.query(AuditLogDB)
        .filter(
            AuditLogDB.entity_type == PIN_RESET_ENTITY,
            AuditLogDB.action.in_(
                [
                    PIN_RESET_REQUEST_ACTION,
                    PIN_RESET_APPROVE_ACTION,
                    PIN_RESET_REJECT_ACTION,
                ]
            ),
            AuditLogDB.entity_id == user_id,
        )
        .order_by(AuditLogDB.performed_at.desc(), AuditLogDB.audit_id.desc())
        .first()
    )
    return bool(latest and latest.action == PIN_RESET_REQUEST_ACTION)


def request_pin_reset_by_email(db: Session, email: str) -> tuple[bool, str]:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return False, "Email is required"

    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    # Privacy-safe response for unknown emails.
    if not user:
        return True, "If the account exists, a PIN reset request has been sent to admin for review."

    if has_pending_pin_reset_request(db, int(user.user_id)):
        return True, "A PIN reset request is already pending admin review."

    now = datetime.utcnow()
    log_action(
        db,
        user_id=int(user.user_id),
        action=PIN_RESET_REQUEST_ACTION,
        entity_type=PIN_RESET_ENTITY,
        entity_id=int(user.user_id),
        old_value=None,
        new_value={
            "status": "pending",
            "email": normalized_email,
            "requested_at": now.isoformat(),
        },
    )
    db.commit()
    return True, "PIN reset request submitted. Please wait for admin to issue a new PIN."


def pin_reset_status_by_email(db: Session, email: str) -> dict:
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return {"has_pending_request": False}
    user = db.query(UserDB).filter(func.lower(UserDB.email) == normalized_email).first()
    if not user:
        return {"has_pending_request": False}
    return {"has_pending_request": has_pending_pin_reset_request(db, int(user.user_id))}


def list_pending_pin_reset_requests(db: Session) -> list[dict]:
    logs = (
        db.query(AuditLogDB)
        .filter(
            AuditLogDB.entity_type == PIN_RESET_ENTITY,
            AuditLogDB.action.in_(
                [
                    PIN_RESET_REQUEST_ACTION,
                    PIN_RESET_APPROVE_ACTION,
                    PIN_RESET_REJECT_ACTION,
                ]
            ),
        )
        .order_by(AuditLogDB.performed_at.desc(), AuditLogDB.audit_id.desc())
        .limit(2000)
        .all()
    )

    latest_by_user: dict[int, AuditLogDB] = {}
    for row in logs:
        uid = _pin_reset_subject_user_id(row)
        if uid is None or uid in latest_by_user:
            continue
        latest_by_user[uid] = row

    pending_logs: list[AuditLogDB] = [
        row for row in latest_by_user.values() if row.action == PIN_RESET_REQUEST_ACTION
    ]
    if not pending_logs:
        return []

    pending_ids = [_pin_reset_subject_user_id(r) for r in pending_logs]
    user_ids = [uid for uid in pending_ids if uid is not None]
    users = db.query(UserDB).filter(UserDB.user_id.in_(user_ids)).all() if user_ids else []
    users_by_id = {int(u.user_id): u for u in users}

    out: list[dict] = []
    for row in sorted(pending_logs, key=lambda x: (x.performed_at, x.audit_id), reverse=True):
        uid = _pin_reset_subject_user_id(row)
        if uid is None:
            continue
        user = users_by_id.get(uid)
        if not user:
            continue

        requested_at = row.performed_at
        try:
            payload = json.loads(row.new_value) if row.new_value else {}
            if isinstance(payload, dict) and payload.get("requested_at"):
                requested_at = datetime.fromisoformat(str(payload["requested_at"]))
        except Exception:
            pass

        out.append(
            {
                "user_id": uid,
                "email": str(user.email or ""),
                "full_name": str(user.full_name or user.username or f"User #{uid}"),
                "requested_at": requested_at.isoformat() if requested_at else None,
                "status": "pending",
            }
        )
    return out


def reject_pin_reset_request(db: Session, user_id: int, actor_admin_id: int, reason: Optional[str] = None) -> tuple[bool, str]:
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        return False, "User not found"
    if not has_pending_pin_reset_request(db, user_id):
        return False, "No pending PIN reset request for this user"
    now = datetime.utcnow()
    log_action(
        db,
        user_id=actor_admin_id,
        action=PIN_RESET_REJECT_ACTION,
        entity_type=PIN_RESET_ENTITY,
        entity_id=user_id,
        old_value={"status": "pending"},
        new_value={
            "status": "rejected",
            "reason": (reason or "").strip() or None,
            "processed_at": now.isoformat(),
        },
    )
    db.commit()
    return True, "PIN reset request rejected"


def admin_set_user_pin(
    db: Session,
    *,
    target_user_id: int,
    pin: str,
    actor_admin_id: int,
) -> tuple[bool, str]:
    """Admin sets or replaces the target user's 6-digit account PIN (audited)."""
    target = db.query(UserDB).filter(UserDB.user_id == target_user_id).first()
    if not target:
        return False, "User not found"
    if int(target_user_id) == int(actor_admin_id):
        return False, "Use profile PIN endpoints to set your own PIN"

    try:
        normalized = _normalize_pin(pin)
    except ValueError as exc:
        return False, str(exc)

    had_pin = bool((target.pin_hash or "").strip())
    target.pin_hash = pwd_context.hash(normalized)
    target.pin_updated_at = datetime.utcnow()
    target.updated_at = datetime.utcnow()

    log_action(
        db,
        user_id=actor_admin_id,
        action="ADMIN_SET_USER_PIN",
        entity_type="UserProfile",
        entity_id=target_user_id,
        old_value={"had_pin": had_pin},
        new_value={
            "target_user_id": target_user_id,
            "pin_updated_at": target.pin_updated_at.isoformat(),
        },
    )
    if has_pending_pin_reset_request(db, int(target_user_id)):
        log_action(
            db,
            user_id=actor_admin_id,
            action=PIN_RESET_APPROVE_ACTION,
            entity_type=PIN_RESET_ENTITY,
            entity_id=int(target_user_id),
            old_value={"status": "pending"},
            new_value={
                "status": "approved",
                "processed_at": datetime.utcnow().isoformat(),
                "source_action": "ADMIN_SET_USER_PIN",
            },
        )
    db.commit()
    return True, "PIN set successfully"


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

    plain_pw = (new_password or "").strip()
    if (user.password_hash or "").strip() and pwd_context.verify(plain_pw, user.password_hash):
        return False, "New password must be different from your current password."

    user.password_hash = pwd_context.hash(plain_pw)
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
