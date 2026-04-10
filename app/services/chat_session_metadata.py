from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.orm import Session
from app.db.models import ChatHistoryDB, ChatSessionDB, ChatSessionPinDB

_SESSION_NAME_COLUMN_CACHE: dict[str, bool] = {}
_SESSION_PIN_TABLE_CACHE: dict[str, bool] = {}
_SESSION_NAME_PATTERN = re.compile(r"\[SESSION_NAME\](.*?)\[/SESSION_NAME\]", re.IGNORECASE | re.DOTALL)
_INITIAL_CONTEXT_PATTERN = re.compile(r"\[INITIAL_CONTEXT\](.*?)\[/INITIAL_CONTEXT\]", re.IGNORECASE | re.DOTALL)
_PINNED_PATTERN = re.compile(r"\[PINNED\](.*?)\[/PINNED\]", re.IGNORECASE | re.DOTALL)
_ATTACHMENTS_PATTERN = re.compile(r"\[ATTACHMENTS\](.*?)\[/ATTACHMENTS\]", re.IGNORECASE | re.DOTALL)


def _safe_int_optional_attachment(value: Any) -> Optional[int]:
    """Coerce attachment numeric metadata from API/JSON without raising."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _json_safe_for_attachments(obj: Any) -> Any:
    """Ensure structures from clients are JSON-serializable (no NaN, odd types)."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe_for_attachments(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe_for_attachments(x) for x in obj]
    return str(obj)


def _cache_key(session: Session) -> str:
    bind = session.get_bind()
    url = getattr(bind, "url", None)
    return str(url) if url is not None else "default"


def has_chat_session_name_column(session: Session) -> bool:
    key = _cache_key(session)
    cached = _SESSION_NAME_COLUMN_CACHE.get(key)
    if cached is not None:
        return cached

    bind = session.get_bind()
    inspector = inspect(bind)
    try:
        columns = inspector.get_columns("Chat_Session")
    except Exception:
        _SESSION_NAME_COLUMN_CACHE[key] = False
        return False

    exists = any(str(column.get("name") or "").lower() == "session_name" for column in columns)
    _SESSION_NAME_COLUMN_CACHE[key] = exists
    return exists


def has_chat_session_pin_table(session: Session) -> bool:
    key = _cache_key(session)
    cached = _SESSION_PIN_TABLE_CACHE.get(key)
    if cached is not None:
        return cached

    bind = session.get_bind()
    inspector = inspect(bind)
    try:
        tables = {str(table_name).lower() for table_name in inspector.get_table_names()}
    except Exception:
        _SESSION_PIN_TABLE_CACHE[key] = False
        return False

    exists = "chat_session_pin" in tables
    _SESSION_PIN_TABLE_CACHE[key] = exists
    return exists


def fetch_chat_session_names(session: Session, session_ids: Iterable[str]) -> Dict[str, str]:
    ids = [str(session_id).strip() for session_id in session_ids if str(session_id).strip()]
    if not ids:
        return {}

    out: Dict[str, str] = {}

    if has_chat_session_name_column(session):
        stmt = text(
            "SELECT session_id, session_name FROM Chat_Session WHERE session_id IN :session_ids"
        ).bindparams(bindparam("session_ids", expanding=True))
        rows = session.execute(stmt, {"session_ids": ids}).mappings().all()
        out.update(
            {
                str(row["session_id"]): str(row["session_name"]).strip()
                for row in rows
                if row.get("session_id") is not None and str(row.get("session_name") or "").strip()
            }
        )

    missing_ids = [session_id for session_id in ids if session_id not in out]
    if not missing_ids:
        return out

    rows = (
        session.query(ChatHistoryDB)
        .filter(ChatHistoryDB.session_id.in_(missing_ids))
        .order_by(ChatHistoryDB.session_id.asc(), ChatHistoryDB.created_at.asc(), ChatHistoryDB.chat_id.asc())
        .all()
    )
    for row in rows:
        sid = str(row.session_id or "").strip()
        if not sid or sid in out:
            continue
        name = extract_session_name(row.message)
        if name:
            out[sid] = name
    return out


def update_chat_session_name(session: Session, session_id: str, session_name: str) -> bool:
    updated = False
    if has_chat_session_name_column(session):
        session.execute(
            text("UPDATE Chat_Session SET session_name = :session_name WHERE session_id = :session_id"),
            {"session_id": session_id, "session_name": session_name},
        )
        updated = True

    row = (
        session.query(ChatHistoryDB)
        .filter(ChatHistoryDB.session_id == session_id)
        .order_by(ChatHistoryDB.created_at.asc(), ChatHistoryDB.chat_id.asc())
        .first()
    )
    if row is not None:
        initial_context = extract_initial_context(row.message)
        is_pinned = extract_pinned_state(row.message)
        row.message = build_session_metadata(
            session_name=session_name,
            initial_context=initial_context,
            pinned=is_pinned,
        )
        updated = True
    else:
        chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == session_id).first()
        if chat_session is not None:
            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=chat_session.user_id,
                    message=build_session_metadata(session_name=session_name, pinned=False),
                    bot_response=None,
                    created_at=datetime.utcnow(),
                )
            )
            updated = True

    return updated


def update_chat_session_initial_context(session: Session, session_id: str, user_id: int, initial_context: str) -> bool:
    clean_context = (initial_context or "").strip()
    if not clean_context:
        return False

    row = (
        session.query(ChatHistoryDB)
        .filter(ChatHistoryDB.session_id == session_id, ChatHistoryDB.user_id == user_id)
        .order_by(ChatHistoryDB.created_at.asc(), ChatHistoryDB.chat_id.asc())
        .first()
    )
    if row is not None:
        session_name = extract_session_name(row.message) or f"Session {session_id[:8]}"
        pinned = extract_pinned_state(row.message)
        row.message = build_session_metadata(
            session_name=session_name,
            initial_context=clean_context,
            pinned=pinned,
        )
        return True

    chat_session = (
        session.query(ChatSessionDB)
        .filter(ChatSessionDB.session_id == session_id, ChatSessionDB.user_id == user_id)
        .first()
    )
    if chat_session is None:
        return False

    session_name = fetch_chat_session_names(session, [session_id]).get(session_id) or f"Session {session_id[:8]}"
    session.add(
        ChatHistoryDB(
            session_id=session_id,
            user_id=user_id,
            message=build_session_metadata(session_name=session_name, initial_context=clean_context, pinned=False),
            bot_response=None,
            created_at=datetime.utcnow(),
        )
    )
    return True


def fetch_pinned_session_ids(session: Session, user_id: int, session_ids: Iterable[str] | None = None) -> Set[str]:
    ids = [str(session_id).strip() for session_id in (session_ids or []) if str(session_id).strip()]
    out: Set[str] = set()

    if has_chat_session_pin_table(session):
        query = session.query(ChatSessionPinDB.session_id).filter(ChatSessionPinDB.user_id == user_id)
        if ids:
            query = query.filter(ChatSessionPinDB.session_id.in_(ids))
        pinned_rows = query.all()
        out.update(str(row[0]) for row in pinned_rows if row and row[0])

    candidate_ids = ids
    if not candidate_ids:
        candidate_ids = [
            str(session_id)
            for session_id, in session.query(ChatSessionDB.session_id).filter(ChatSessionDB.user_id == user_id).all()
            if session_id
        ]
    missing_ids = [session_id for session_id in candidate_ids if session_id not in out]
    if not missing_ids:
        return out

    rows = (
        session.query(ChatHistoryDB)
        .filter(ChatHistoryDB.user_id == user_id, ChatHistoryDB.session_id.in_(missing_ids))
        .order_by(ChatHistoryDB.session_id.asc(), ChatHistoryDB.created_at.asc(), ChatHistoryDB.chat_id.asc())
        .all()
    )
    for row in rows:
        sid = str(row.session_id or "").strip()
        if not sid or sid in out:
            continue
        if extract_pinned_state(row.message):
            out.add(sid)
    return out


def set_chat_session_pinned(session: Session, session_id: str, user_id: int, pinned: bool) -> bool:
    updated = False

    if has_chat_session_pin_table(session):
        existing = (
            session.query(ChatSessionPinDB)
            .filter(ChatSessionPinDB.session_id == session_id, ChatSessionPinDB.user_id == user_id)
            .first()
        )
        if pinned:
            if not existing:
                session.add(ChatSessionPinDB(session_id=session_id, user_id=user_id))
        elif existing:
            session.delete(existing)
        updated = True

    row = (
        session.query(ChatHistoryDB)
        .filter(ChatHistoryDB.session_id == session_id, ChatHistoryDB.user_id == user_id)
        .order_by(ChatHistoryDB.created_at.asc(), ChatHistoryDB.chat_id.asc())
        .first()
    )
    if row is not None:
        initial_context = extract_initial_context(row.message)
        session_name = extract_session_name(row.message) or f"Session {session_id[:8]}"
        row.message = build_session_metadata(
            session_name=session_name,
            initial_context=initial_context,
            pinned=pinned,
        )
        updated = True
    else:
        chat_session = (
            session.query(ChatSessionDB)
            .filter(ChatSessionDB.session_id == session_id, ChatSessionDB.user_id == user_id)
            .first()
        )
        if chat_session is not None:
            fallback_name = fetch_chat_session_names(session, [session_id]).get(session_id) or f"Session {session_id[:8]}"
            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=user_id,
                    message=build_session_metadata(session_name=fallback_name, pinned=pinned),
                    bot_response=None,
                    created_at=datetime.utcnow(),
                )
            )
            updated = True

    return updated


def build_session_metadata(*, session_name: str, initial_context: str | None = None, pinned: bool | None = None) -> str:
    meta = f"[SESSION_NAME]{(session_name or '').strip()}[/SESSION_NAME]"
    clean_initial_context = (initial_context or "").strip()
    if clean_initial_context:
        meta += f"\n[INITIAL_CONTEXT]{clean_initial_context}[/INITIAL_CONTEXT]"
    if pinned is not None:
        meta += f"\n[PINNED]{'1' if pinned else '0'}[/PINNED]"
    return meta


def build_message_with_attachments(message: str, attachments: List[Dict[str, Any]] | None = None) -> str:
    clean_message = (message or "").strip()
    clean_attachments = normalize_message_attachments(attachments)
    if not clean_attachments:
        return clean_message
    safe = _json_safe_for_attachments(clean_attachments)
    try:
        encoded = json.dumps(safe, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Không thể chuẩn hóa metadata đính kèm để lưu: {exc}") from exc
    return f"{clean_message}\n[ATTACHMENTS]{encoded}[/ATTACHMENTS]".strip()


def normalize_message_attachments(attachments: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    if not isinstance(attachments, list):
        return []

    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(attachments, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("file_name") or item.get("fileName") or f"File {idx}").strip()
        if not name:
            continue
        extension = str(item.get("extension") or "").strip().lower()
        if not extension and "." in name:
            extension = name.rsplit(".", 1)[-1].lower()
        status = str(item.get("status") or "ready").strip().lower() or "ready"
        row_count = item.get("row_count")
        if row_count is None:
            row_count = item.get("rowCount")
        col_count = item.get("column_count")
        if col_count is None:
            col_count = item.get("columnCount")
        normalized = {
            "id": str(item.get("id") or f"file-{idx}").strip() or f"file-{idx}",
            "name": name,
            "size": _safe_int_optional_attachment(item.get("size")) or 0,
            "extension": extension,
            "status": "error" if status == "error" else "ready",
            "job_id": str(item.get("job_id") or item.get("jobId") or "").strip() or None,
            "row_count": _safe_int_optional_attachment(row_count),
            "column_count": _safe_int_optional_attachment(col_count),
            "columns": [str(col) for col in (item.get("columns") or []) if str(col).strip()] or None,
            "preview_rows": item.get("preview_rows") or item.get("previewRows") or None,
            "context_text": str(item.get("context_text") or item.get("contextText") or "").strip() or None,
            "error": str(item.get("error") or "").strip() or None,
        }
        out.append(normalized)
    return out


def extract_message_attachments(message: str | None) -> List[Dict[str, Any]]:
    text_value = message or ""
    match = _ATTACHMENTS_PATTERN.search(text_value)
    if not match:
        return []
    try:
        raw = json.loads(match.group(1).strip())
    except Exception:
        return []
    return normalize_message_attachments(raw if isinstance(raw, list) else [])


def extract_session_name(message: str | None) -> str | None:
    text_value = message or ""
    match = _SESSION_NAME_PATTERN.search(text_value)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_initial_context(message: str | None) -> str | None:
    text_value = message or ""
    match = _INITIAL_CONTEXT_PATTERN.search(text_value)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_pinned_state(message: str | None) -> bool | None:
    text_value = message or ""
    match = _PINNED_PATTERN.search(text_value)
    if not match:
        return None
    value = match.group(1).strip().lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    return None


def strip_session_metadata(message: str | None) -> str | None:
    text_value = message or ""
    text_value = _SESSION_NAME_PATTERN.sub("", text_value)
    text_value = _INITIAL_CONTEXT_PATTERN.sub("", text_value)
    text_value = _PINNED_PATTERN.sub("", text_value)
    text_value = _ATTACHMENTS_PATTERN.sub("", text_value)
    cleaned = text_value.strip()
    return cleaned or None


def format_history_user_message_for_llm(raw_message: str | None) -> str | None:
    """
    Build the user turn text for LLM chat history from persisted Chat_History.message.

    Messages store file metadata inside [ATTACHMENTS]... JSON (including context_text).
    strip_session_metadata removes that block, so replaying history without this step drops
    file grounding — follow-up questions (or switching models) look like the model
    "forgot" the file even though the UI still shows the attachment.
    """
    if not (raw_message or "").strip():
        return None
    attachments = extract_message_attachments(raw_message)
    plain = (strip_session_metadata(raw_message) or "").strip()

    file_chunks: List[str] = []
    for idx, att in enumerate(attachments, start=1):
        if not isinstance(att, dict):
            continue
        ctx = att.get("context_text")
        if not isinstance(ctx, str) or not ctx.strip():
            continue
        name = str(att.get("name") or f"File {idx}").strip()
        file_chunks.append(f"[FILE {idx}: {name}]\n{ctx.strip()}")

    if file_chunks:
        merged = "\n\n".join(file_chunks)
        if plain:
            return (
                "[FILE DINH KEM TRONG TIN NHAN (du lieu rut gon luu trong phien — tiep tuc tham chieu khi hoi tiep)]\n"
                + merged
                + "\n\n[NOI DUNG / CAU HOI CUA NGUOI DUNG]\n"
                + plain
            )
        return merged

    return plain or None


def summary_title_from_message(message: str | None, max_len: int = 52) -> str:
    """Short label for session list from first user message (strip metadata/attachments)."""
    plain = strip_session_metadata(message) or (message or "").strip()
    if not plain:
        return ""
    one_line = " ".join(plain.split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1].rstrip() + "…"
