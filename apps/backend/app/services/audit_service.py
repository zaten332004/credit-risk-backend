from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLogDB
from app.schemas.schemas import AuditLogRead


def _serialize(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def log_action(
    db: Session,
    *,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    old_value: Any = None,
    new_value: Any = None,
) -> AuditLogDB:
    row = AuditLogDB(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_serialize(old_value),
        new_value=_serialize(new_value),
        performed_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def to_audit_log_read(row: AuditLogDB, actor_name: Optional[str] = None) -> AuditLogRead:
    return AuditLogRead(
        audit_id=row.audit_id,
        user_id=row.user_id,
        actor_name=actor_name,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        old_value=row.old_value,
        new_value=row.new_value,
        performed_at=row.performed_at,
    )
