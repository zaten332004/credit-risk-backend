"""
AI Chat API Router (supports multiple providers).

Providers:
- gemini
- mock (optional fallback)
"""

from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Protocol

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, AliasChoices
from pydantic.config import ConfigDict
from pydantic.functional_validators import field_validator
from sqlalchemy.orm import Session

from app.core.client_safe_errors import chat_service_unavailable_message, public_message_for_exception
from app.core.config import settings
from app.core.security import get_current_active_user
from app.db.session import SessionLocal
from app.db.models import ChatHistoryDB, ChatSessionDB
from app.schemas.schemas import User
from app.services.gemini_ai_chat_service import GeminiResourceExhaustedError
from app.services.mock_ai_chat_service import MockAIChatService
from app.services.analytics_data_service import get_analysis_context, get_analysis_context_powerbi
from app.services.ai_chat_file_context_service import AIChatFileContextService
from app.services.chat_session_metadata import set_chat_session_pinned, update_chat_session_initial_context, update_chat_session_name
from app.services.services import get_upload_job_content, persist_upload_job_file
from app.services.powerbi_service import powerbi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])

_ROLE_ORDER = {"viewer": 0, "analyst": 1, "manager": 2, "admin": 3}


def _enforce_ai_data_source_rbac(customer_context: Optional[dict], user: User) -> None:
    """Reject privileged AI data sources for lower roles (e.g. alerts → manager+)."""
    if not isinstance(customer_context, dict):
        return
    raw = str(customer_context.get("ai_data_source") or customer_context.get("aiDataSource") or "").strip().lower()
    if raw in ("alerts", "alert", "canh_bao", "danh_muc_alerts", "alert_list"):
        if _ROLE_ORDER.get(_user_role(user), 0) < _ROLE_ORDER.get("manager", 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nguồn dữ liệu Alerts chỉ dành cho Manager hoặc Admin.",
            )


class StartChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_name: str = Field(default="", validation_alias=AliasChoices("session_name", "sessionName"))
    initial_context: Optional[str] = Field(default=None, validation_alias=AliasChoices("initial_context", "initialContext"))
    model: Optional[str] = Field(default=None, validation_alias=AliasChoices("model", "chat_model", "chatModel"))

    @field_validator("model", mode="before")
    @classmethod
    def _strip_empty_model(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("initial_context", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("session_id", "sessionId"))
    message: str = Field(validation_alias=AliasChoices("message", "text", "content", "prompt"))
    customer_context: Optional[dict] = Field(default=None, validation_alias=AliasChoices("customer_context", "customerContext"))
    model: Optional[str] = Field(default=None, validation_alias=AliasChoices("model", "chat_model", "chatModel"))

    @field_validator("model", mode="before")
    @classmethod
    def _strip_empty_model_send(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v


class RenameSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_name: str = Field(validation_alias=AliasChoices("session_name", "sessionName", "name", "title"))

    @field_validator("session_name")
    @classmethod
    def _validate_session_name(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("session_name is required")
        return value[:255]


class PowerBIDaxQueryRequest(BaseModel):
    query: str


class StartChatResponse(BaseModel):
    session_id: str
    sessionId: str
    greeting_message: str
    greetingMessage: str
    greeting: str
    created_at: str
    createdAt: str
    provider: str
    model: Optional[str] = None


class SendMessageResponse(BaseModel):
    success: bool = True
    session_id: str
    sessionId: str
    message: str
    content: str
    answer: str
    text: str
    reply: str
    role: str
    timestamp: str
    sources: Optional[List[str]] = None
    created_session: bool = False
    createdSession: bool = False
    greeting_message: Optional[str] = None
    greetingMessage: Optional[str] = None
    provider: str
    model: Optional[str] = None
    error: Optional[str] = None


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str
    attachments: Optional[List[dict]] = None


class ChatSessionResponse(BaseModel):
    session_id: str
    sessionId: str
    session_name: str
    sessionName: str
    is_active: bool
    isActive: bool
    is_pinned: bool = False
    isPinned: bool = False
    created_at: str
    createdAt: str
    closed_at: Optional[str] = None
    closedAt: Optional[str] = None


class SessionSummaryResponse(BaseModel):
    session_id: str
    session_name: str
    duration: Optional[float]
    user_messages: int
    assistant_messages: int
    total_messages: int
    closed_at: Optional[str]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AIChatService(Protocol):
    def start_chat_session(self, session: Session, user_id: int, session_name: str, initial_context: Optional[str] = None): ...

    def send_message(self, session: Session, session_id: str, user_id: int, message: str, customer_context: Optional[dict] = None): ...

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50): ...

    def close_chat_session(self, session: Session, session_id: str): ...

    def get_user_sessions(self, session: Session, user_id: int): ...

    def generate_analysis_report(self, session: Session, session_id: str): ...


def _provider_name() -> str:
    configured = (os.getenv("AI_CHAT_PROVIDER") or settings.ai_chat_provider or "gemini").strip().lower()
    # Keep runtime provider focused on Gemini; ignore openai/langflow to simplify stack.
    if configured in {"", "gemini"}:
        return "gemini"
    if configured == "mock":
        return "mock"
    return "gemini"


def _resolved_provider_name(chat_service: object) -> str:
    # Avoid importing provider-specific classes here; keep it lightweight and robust.
    name = (getattr(chat_service, "__class__", type(chat_service)).__name__ or "").strip().lower()
    module = (getattr(getattr(chat_service, "__class__", None), "__module__", "") or "").strip().lower()
    marker = f"{module}.{name}"

    if "mock" in marker:
        return "mock"
    if "openai" in marker:
        return "openai"
    if "langflow" in marker:
        return "langflow"
    if "gemini" in marker:
        return "gemini"
    return "unknown"


def _looks_like_missing_db_column(err: Exception, column_name: str) -> bool:
    s = (str(err) or "").lower()
    col = (column_name or "").lower()
    return ("invalid column name" in s and col in s) or ("unknown column" in s and col in s)


def _user_role(user: User) -> str:
    role = (getattr(user, "role", None) or "").strip().lower()
    if role in _ROLE_ORDER:
        return role
    return "admin" if bool(getattr(user, "is_admin", False)) else "viewer"


def _normalize_model_id(model: str) -> str:
    m = (model or "").strip()
    if not m:
        return ""
    if m.startswith("models/"):
        m = m[len("models/") :]
    return m


def _gemini_model_catalog() -> List[dict]:
    # Defaults chosen to match typical "fast / thinking / pro" UX.
    # Order is lowest tier first (used as safe default when client omits model).
    fast = _normalize_model_id(os.getenv("AI_CHAT_GEMINI_MODEL_FAST") or "gemini-2.5-flash-lite")
    thinking = _normalize_model_id(os.getenv("AI_CHAT_GEMINI_MODEL_THINKING") or "gemini-2.5-flash")
    pro = _normalize_model_id(os.getenv("AI_CHAT_GEMINI_MODEL_PRO") or "gemini-2.5-pro")

    out = [
        {
            "id": fast,
            "label": "Nhanh",
            "tier": "fast",
            "description": "Trả lời nhanh, chi phí thấp.",
            "min_role": "viewer",
        },
        {
            "id": thinking,
            "label": "Tư duy",
            "tier": "thinking",
            "description": "Cân bằng tốc độ và chất lượng.",
            "min_role": "analyst",
        },
        {
            "id": pro,
            "label": "Pro",
            "tier": "pro",
            "description": "Chất lượng cao hơn (giới hạn theo quyền/quota).",
            "min_role": "manager",
        },
    ]
    return [m for m in out if m.get("id")]


def _lowest_allowed_gemini_model(user: User) -> str:
    """Smallest tier the user may use (catalog order: fast → thinking → pro)."""
    role = _user_role(user)
    for m in _gemini_model_catalog():
        min_role = m.get("min_role", "viewer")
        if _ROLE_ORDER.get(role, 0) >= _ROLE_ORDER.get(min_role, 0):
            mid = str(m.get("id") or "").strip()
            if mid:
                return mid
    return _normalize_model_id(os.getenv("AI_CHAT_GEMINI_MODEL_FAST") or "gemini-2.5-flash-lite")


def _apply_gemini_model_on_service(chat_service: AIChatService, model_id: str) -> None:
    if not (model_id or "").strip():
        return
    try:
        from app.services.gemini_ai_chat_service import GeminiAIChatService

        if isinstance(chat_service, GeminiAIChatService):
            chat_service.model = _normalize_model_id(model_id)
            chat_service.mode_tier = _gemini_tier_for_model(model_id)
    except Exception:
        pass


def _assert_model_allowed(provider: str, model: str, user: User) -> str:
    selected = _normalize_model_id(model)
    if not selected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is required")

    if provider != "gemini":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model override is only supported for provider=gemini")

    role = _user_role(user)
    allowed = []
    for m in _gemini_model_catalog():
        if m["id"] != selected:
            continue
        min_role = m.get("min_role", "viewer")
        if _ROLE_ORDER.get(role, 0) < _ROLE_ORDER.get(min_role, 0):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"model '{selected}' requires role '{min_role}'")
        allowed.append(m)

    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"model '{selected}' is not allowed")
    return selected


def _gemini_tier_for_model(model: str) -> str:
    selected = _normalize_model_id(model)
    for item in _gemini_model_catalog():
        if item.get("id") == selected:
            return str(item.get("tier") or "thinking")
    normalized = selected.lower()
    if "lite" in normalized:
        return "fast"
    if "pro" in normalized:
        return "pro"
    return "thinking"


@router.get("/models")
async def ai_chat_models(current_user: User = Depends(get_current_active_user)):
    provider = _provider_name()
    role = _user_role(current_user)

    if provider != "gemini":
        return {"provider": provider, "role": role, "models": []}

    models = []
    for m in _gemini_model_catalog():
        min_role = m.get("min_role", "viewer")
        if _ROLE_ORDER.get(role, 0) >= _ROLE_ORDER.get(min_role, 0):
            models.append({k: v for k, v in m.items() if k != "min_role"} | {"min_role": min_role})

    default_model = _lowest_allowed_gemini_model(current_user)
    return {"provider": provider, "role": role, "default_model": default_model, "models": models}


def _ensure_uuid(session_id: str) -> str:
    s = (session_id or "").strip()
    if not s:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id is required")
    try:
        uuid.UUID(s)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id must be a valid UUID")
    return s


def _ensure_uuid_file_id(file_id: str) -> str:
    s = (file_id or "").strip()
    if not s:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_id is required")
    try:
        uuid.UUID(s)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_id must be a valid UUID")
    return s


def _extract_uploaded_file_context(customer_context: Optional[dict]) -> str:
    if not isinstance(customer_context, dict):
        return ""
    raw_files = customer_context.get("uploaded_files") or customer_context.get("uploadedFiles") or []
    if not isinstance(raw_files, list):
        return ""

    chunks: List[str] = []
    for idx, item in enumerate(raw_files, start=1):
        if not isinstance(item, dict):
            continue
        status_value = str(item.get("status") or "").strip().lower()
        if status_value == "error":
            continue
        name = str(item.get("name") or item.get("file_name") or item.get("fileName") or f"File {idx}").strip()
        context_text = str(item.get("context_text") or item.get("contextText") or "").strip()
        if not context_text:
            continue
        chunks.append(f"[FILE {idx}: {name}]\n{context_text}")
    return "\n\n".join(chunks).strip()


def _merge_customer_context_with_powerbi(customer_context: Optional[dict], current_user: User) -> Optional[dict]:
    merged = dict(customer_context) if isinstance(customer_context, dict) else {}
    runtime_user = powerbi_service.get_runtime_user(current_user)
    if runtime_user.power_bi_enabled and runtime_user.power_bi_workspace_id and runtime_user.power_bi_dataset_id:
        merged["powerbi_runtime_config"] = {
            "tenant_id": runtime_user.power_bi_tenant_id,
            "workspace_id": runtime_user.power_bi_workspace_id,
            "dataset_id": runtime_user.power_bi_dataset_id,
            "workspace_name": getattr(runtime_user, "power_bi_workspace_name", None) or "",
            "dataset_name": getattr(runtime_user, "power_bi_dataset_name", None) or "",
            "enabled": True,
            "table_names": list(getattr(runtime_user, "power_bi_table_names", None) or []),
        }
    return merged or None


def _fallback_to_mock_enabled() -> bool:
    # Default is OFF to avoid silently returning mock responses in production/dev.
    return (os.getenv("AI_CHAT_FALLBACK_TO_MOCK") or "0").strip().lower() in ("1", "true", "yes", "y")


def _looks_like_auth_or_config_error(err: Exception) -> bool:
    # Heuristic: don't hide "bad key / missing config" problems behind mock mode.
    s = (str(err) or "").lower()
    needles = (
        "unauthorized",
        "forbidden",
        "permission",
        "api key",
        "apikey",
        "invalid key",
        "invalid api",
        "401",
        "403",
        "gemini_api_key",
        "gemini_api_key not found",
        "openai_api_key",
        "openai_api_key not found",
        "langflow not configured",
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "429",
    )
    return any(n in s for n in needles)


def get_chat_service() -> AIChatService:
    provider = _provider_name()

    if provider == "mock":
        return MockAIChatService()

    # Default: Gemini
    try:
        from app.services.gemini_ai_chat_service import GeminiAIChatService

        return GeminiAIChatService()
    except Exception as e:
        if _fallback_to_mock_enabled() and not _looks_like_auth_or_config_error(e):
            logger.warning("Gemini init failed (%s) -> fallback to mock", str(e))
            return MockAIChatService()
        raise


@router.post("/start", response_model=StartChatResponse)
async def start_chat_session(
    request: StartChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for start_chat_session: %s", str(e))
        raise HTTPException(status_code=500, detail=chat_service_unavailable_message())
    
    provider = _provider_name()
    selected_model: Optional[str] = None
    if provider == "gemini":
        if request.model:
            selected_model = _assert_model_allowed(provider, request.model, current_user)
        else:
            selected_model = _lowest_allowed_gemini_model(current_user)
        _apply_gemini_model_on_service(chat_service, selected_model)
    else:
        selected_model = getattr(chat_service, "model", None)

    try:
        session_id, greeting = chat_service.start_chat_session(
            session=db,
            user_id=current_user.id,
            session_name=request.session_name,
            initial_context=request.initial_context,
        )
    except Exception as e:
        logger.exception("Error starting chat session")
        raise HTTPException(status_code=500, detail=public_message_for_exception(e))
    
    created_at = datetime.utcnow().isoformat()
    resolved_provider = _resolved_provider_name(chat_service)
    return StartChatResponse(
        session_id=session_id,
        sessionId=session_id,
        greeting_message=greeting,
        greetingMessage=greeting,
        greeting=greeting,
        created_at=created_at,
        createdAt=created_at,
        provider=resolved_provider if resolved_provider != "unknown" else provider,
        model=selected_model if resolved_provider == "gemini" else None,
    )


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for send_message: %s", str(e))
        # Fallback to mock if available
        if _fallback_to_mock_enabled():
            chat_service = MockAIChatService()
        else:
            raise HTTPException(status_code=500, detail=chat_service_unavailable_message())
    
    provider = _provider_name()
    selected_model: Optional[str] = None
    if provider == "gemini":
        if request.model:
            selected_model = _assert_model_allowed(provider, request.model, current_user)
        else:
            selected_model = _lowest_allowed_gemini_model(current_user)
        _apply_gemini_model_on_service(chat_service, selected_model)
    else:
        selected_model = getattr(chat_service, "model", None)
    effective_customer_context = _merge_customer_context_with_powerbi(request.customer_context, current_user)
    _enforce_ai_data_source_rbac(effective_customer_context, current_user)
    session_id = (request.session_id or "").strip() or None
    created_session = False
    greeting_message: Optional[str] = None

    if not session_id:
        created_session = True
        # Tên hiển thị được gán sau từ tin nhắn user đầu tiên (Gemini/Mock).
        try:
            session_id, greeting_message = chat_service.start_chat_session(
                session=db,
                user_id=current_user.id,
                session_name="",
                initial_context=None,
            )
        except Exception as e:
            logger.exception("Error creating auto session in send_message")
            raise HTTPException(status_code=500, detail=public_message_for_exception(e))
    else:
        session_id = _ensure_uuid(session_id)

    uploaded_file_context = _extract_uploaded_file_context(effective_customer_context)
    if uploaded_file_context:
        try:
            update_chat_session_initial_context(db, session_id, current_user.id, uploaded_file_context)
            db.flush()
        except Exception as e:
            logger.warning("Could not persist uploaded file context for session %s: %s", session_id, str(e))

    try:
        resp = chat_service.send_message(
            session=db,
            session_id=session_id,
            user_id=current_user.id,
            message=request.message,
            customer_context=effective_customer_context,
        )
        err = None
    except Exception as e:
        if isinstance(e, GeminiResourceExhaustedError):
            headers = {}
            retry_after = getattr(e, "retry_after_seconds", None)
            if isinstance(retry_after, int) and retry_after > 0:
                headers["Retry-After"] = str(retry_after)
            detail_429 = str(e).strip()
            if len(detail_429) > 180 or "pymysql" in detail_429.lower():
                detail_429 = "Đã vượt giới hạn sử dụng mô hình AI. Vui lòng thử lại sau."
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail_429,
                headers=headers,
            )

        fallback = _fallback_to_mock_enabled() and (not _looks_like_auth_or_config_error(e))
        if fallback and not isinstance(chat_service, MockAIChatService):
            mock = MockAIChatService()
            resp = mock.send_message(
                session=db,
                session_id=session_id,
                user_id=current_user.id,
                message=request.message,
                customer_context=effective_customer_context,
            )
            provider = "mock"
            sources = list(getattr(resp, "sources", None) or [])
            sources.append(f"fallback:{_provider_name()}_error:{str(e)[:120]}")
            setattr(resp, "sources", sources)
            err = str(e)
        else:
            logger.exception(
                "ai-chat send_message failed (user_id=%s session_id=%s provider=%s)",
                getattr(current_user, "id", None),
                session_id,
                provider,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=public_message_for_exception(e),
            )

    resolved_provider = "mock" if provider == "mock" else _resolved_provider_name(chat_service)
    resolved_model = selected_model if resolved_provider == "gemini" else None

    return SendMessageResponse(
        success=True,
        session_id=resp.session_id,
        sessionId=resp.session_id,
        message=resp.message,
        content=resp.message,
        answer=resp.message,
        text=resp.message,
        reply=resp.message,
        role=resp.role,
        timestamp=resp.timestamp.isoformat(),
        sources=getattr(resp, "sources", None),
        created_session=created_session,
        createdSession=created_session,
        greeting_message=greeting_message,
        greetingMessage=greeting_message,
        provider=resolved_provider if resolved_provider != "unknown" else provider,
        model=resolved_model,
        error=err,
    )


@router.post("/upload-file")
async def ai_chat_upload_context_file(
    file: UploadFile = File(...),
    _: User = Depends(get_current_active_user),
):
    """Parse CSV/Excel for in-chat context (passed as customer_context.uploaded_files on /send)."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    try:
        extracted = AIChatFileContextService.extract_context(filename=file.filename or "upload.csv", content=contents)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    raw_name = file.filename or "upload.csv"
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    fid = str(uuid.uuid4())
    try:
        persist_upload_job_file(fid, raw_name, contents)
    except Exception:
        logger.exception("Failed to persist AI chat upload file id=%s", fid)
        raise HTTPException(status_code=500, detail="Could not store uploaded file")
    return {
        "uploaded_files": [
            {
                "id": fid,
                "name": extracted["file_name"],
                "file_name": extracted["file_name"],
                "extension": ext,
                "size": len(contents),
                "status": "ready",
                "row_count": extracted["row_count"],
                "column_count": extracted["column_count"],
                "columns": extracted["columns"],
                "preview_rows": extracted["preview_rows"],
                "context_text": extracted["context_text"],
            }
        ]
    }


@router.get("/uploaded-file/{file_id}")
async def ai_chat_get_uploaded_file_rows(
    file_id: str,
    max_rows: int = Query(default=50_000, ge=1, le=200_000),
    current_user: User = Depends(get_current_active_user),
):
    """Return parsed tabular rows for a file previously uploaded via POST /upload-file (by UUID)."""
    _ = current_user
    fid = _ensure_uuid_file_id(file_id)
    payload = get_upload_job_content(fid)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded file not found")
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        rows = []
    total = len(rows)
    truncated = total > max_rows
    out_rows = rows[:max_rows] if truncated else rows
    return {
        "id": fid,
        "name": payload.get("file_name") or "",
        "columns": payload.get("columns") or [],
        "rows": out_rows,
        "row_count": int(payload.get("row_count") or total),
        "returned_rows": len(out_rows),
        "truncated": truncated,
        "context_text": payload.get("context_text"),
    }


@router.get("/history/{session_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for get_chat_history: %s", str(e))
        raise HTTPException(status_code=500, detail=chat_service_unavailable_message())
    
    try:
        session_id = _ensure_uuid(session_id)
        history = chat_service.get_chat_history(session=db, session_id=session_id, limit=limit)
        return [ChatMessageResponse(**m) for m in history]
    except Exception as e:
        logger.exception("Error fetching chat history")
        raise HTTPException(status_code=500, detail=public_message_for_exception(e))


@router.post("/close/{session_id}", response_model=SessionSummaryResponse)
async def close_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for close_chat_session: %s", str(e))
        raise HTTPException(status_code=500, detail=chat_service_unavailable_message())
    
    try:
        session_id = _ensure_uuid(session_id)
        summary = chat_service.close_chat_session(session=db, session_id=session_id)
        return SessionSummaryResponse(**summary)
    except Exception as e:
        logger.exception("Error closing chat session")
        raise HTTPException(status_code=500, detail=public_message_for_exception(e))


@router.post("/sessions/{session_id}/close", response_model=SessionSummaryResponse)
async def close_chat_session_alias(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for close_chat_session_alias: %s", str(e))
        raise HTTPException(status_code=500, detail=chat_service_unavailable_message())
    
    try:
        # REST-style alias for UI: /sessions/{id}/close
        session_id = _ensure_uuid(session_id)
        summary = chat_service.close_chat_session(session=db, session_id=session_id)
        return SessionSummaryResponse(**summary)
    except Exception as e:
        logger.exception("Error closing chat session (alias)")
        raise HTTPException(status_code=500, detail=public_message_for_exception(e))


@router.post("/sessions/{session_id}/pin")
async def pin_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sid = _ensure_uuid(session_id)
    q = db.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid)
    if _user_role(current_user) != "admin":
        q = q.filter(ChatSessionDB.user_id == current_user.id)
    row = q.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    try:
        updated = set_chat_session_pinned(db, sid, row.user_id, True)
        if not updated:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist pinned state.",
            )
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    return {"success": True, "session_id": sid, "pinned": True}


@router.post("/sessions/{session_id}/unpin")
async def unpin_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sid = _ensure_uuid(session_id)
    q = db.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid)
    if _user_role(current_user) != "admin":
        q = q.filter(ChatSessionDB.user_id == current_user.id)
    row = q.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    try:
        updated = set_chat_session_pinned(db, sid, row.user_id, False)
        if not updated:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist pinned state.",
            )
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    return {"success": True, "session_id": sid, "pinned": False}


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        chat_service = get_chat_service()
    except Exception as e:
        logger.warning("Failed to get chat service for sessions endpoint: %s", str(e))
        # Return empty sessions if chat service unavailable
        return []
    
    try:
        sessions = chat_service.get_user_sessions(session=db, user_id=current_user.id)
    except Exception as e:
        logger.exception("Error fetching user sessions")
        raise HTTPException(status_code=500, detail=public_message_for_exception(e))
    
    out: List[ChatSessionResponse] = []
    for s in sessions:
        try:
            sid = s.get("session_id")
            name = s.get("session_name")
            active = s.get("is_active")
            pinned = bool(s.get("is_pinned") or s.get("pinned") or False)
            created = s.get("created_at")
            closed = s.get("closed_at")
            out.append(
                ChatSessionResponse(
                    session_id=sid,
                    sessionId=sid,
                    session_name=name,
                    sessionName=name,
                    is_active=active,
                    isActive=active,
                    is_pinned=pinned,
                    isPinned=pinned,
                    created_at=created,
                    createdAt=created,
                    closed_at=closed,
                    closedAt=closed,
                )
            )
        except Exception as e:
            logger.error("Error mapping session response: %s", str(e))
            continue
    return out


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sid = _ensure_uuid(session_id)
    q = db.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid)
    if _user_role(current_user) != "admin":
        q = q.filter(ChatSessionDB.user_id == current_user.id)

    row = q.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    # Delete messages first to avoid FK issues on some DB schemas.
    db.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == sid).delete(synchronize_session=False)
    db.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).delete(synchronize_session=False)
    db.commit()
    return {"success": True, "session_id": sid}


@router.patch("/sessions/{session_id}")
async def rename_chat_session(
    session_id: str,
    request: RenameSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sid = _ensure_uuid(session_id)
    q = db.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid)
    if _user_role(current_user) != "admin":
        q = q.filter(ChatSessionDB.user_id == current_user.id)

    row = q.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    row.last_interaction = datetime.utcnow()
    try:
        updated = update_chat_session_name(db, sid, request.session_name)
        if not updated:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist session name.",
            )
        db.commit()
        db.refresh(row)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "session_id": sid,
        "session_name": request.session_name,
        "updated_at": row.last_interaction.isoformat() if row.last_interaction else None,
    }


@router.get("/debug")
async def ai_chat_debug(current_user: User = Depends(get_current_active_user)):
    provider = _provider_name()
    resolved_provider: Optional[str] = None
    resolved_model: Optional[str] = None
    provider_init_error: Optional[str] = None
    try:
        chat_service = get_chat_service()
        resolved_provider = _resolved_provider_name(chat_service)
        resolved_model = getattr(chat_service, "model", None)
    except Exception as e:
        provider_init_error = str(e)
    return {
        "provider": provider,
        "resolved_provider": resolved_provider,
        "resolved_model": resolved_model,
        "provider_init_error": provider_init_error,
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY") or settings.gemini_api_key),
        "gemini_model": (os.getenv("GEMINI_MODEL") or settings.gemini_model or "gemini-2.0-flash").strip() or None,
        "context_source": (os.getenv("AI_CHAT_CONTEXT_SOURCE") or settings.ai_chat_context_source or "db").strip().lower(),
        "powerbi_configured": bool(
            (settings.power_bi_tenant_id or "").strip()
            and (settings.power_bi_client_id or "").strip()
            and (settings.power_bi_client_secret or "").strip()
            and (settings.power_bi_workspace_id or "").strip()
            and (settings.power_bi_dataset_id or "").strip()
        ),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY") or settings.openai_api_key),
        "openai_model": (os.getenv("OPENAI_MODEL") or settings.openai_model or "").strip() or None,
        "fallback_to_mock": _fallback_to_mock_enabled(),
        "langflow_run_url": None,
        "langflow_base_url": None,
        "langflow_flow_id": None,
    }


@router.get("/context-preview")
async def ai_chat_context_preview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    source = (os.getenv("AI_CHAT_CONTEXT_SOURCE") or settings.ai_chat_context_source or "db").strip().lower()
    if source == "powerbi":
        context = get_analysis_context_powerbi()
    else:
        context = get_analysis_context(db)
    return {"source": source, "context": context}


@router.get("/powerbi-diagnostic")
async def ai_chat_powerbi_diagnostic(current_user: User = Depends(get_current_active_user)):
    ping = powerbi_service.execute_dax_query_global_verbose('EVALUATE ROW("Ping", 1)')
    return {"ping": ping}


@router.get("/powerbi-tables")
async def ai_chat_powerbi_tables(current_user: User = Depends(get_current_active_user)):
    return powerbi_service.get_dataset_tables_global_verbose()


@router.get("/powerbi-columns")
async def ai_chat_powerbi_columns(
    table: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_active_user),
):
    return powerbi_service.get_table_columns_global_verbose(table)


@router.post("/powerbi-query")
async def ai_chat_powerbi_query(
    request: PowerBIDaxQueryRequest,
    current_user: User = Depends(get_current_active_user),
):
    allow_any = bool(os.getenv("AI_CHAT_POWERBI_QUERY_ALLOW_ANY") or settings.ai_chat_powerbi_query_allow_any)
    if not getattr(current_user, "is_admin", False) and not allow_any:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    q = (request.query or "").strip()
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")
    if len(q) > 5000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query too long")
    return powerbi_service.execute_dax_query_global_verbose(q)
