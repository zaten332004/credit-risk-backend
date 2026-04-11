from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLogDB

logger = logging.getLogger(__name__)
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


def cleanup_expired_audit_logs() -> int:
    """
    Xóa các dòng Audit_Log có performed_at trước ngưỡng AUDIT_LOG_RETENTION_DAYS (UTC).
    Trả về số bản ghi đã xóa. AUDIT_LOG_RETENTION_DAYS <= 0 thì không xóa.
    """
    from app.core.config import settings

    days = float(getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 0) or 0)
    if days <= 0:
        return 0

    from app.db.session import SessionLocal

    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        deleted = (
            db.query(AuditLogDB)
            .filter(AuditLogDB.performed_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        return int(deleted or 0)
    except Exception:
        db.rollback()
        logger.exception("Audit log retention delete failed")
        raise
    finally:
        db.close()
