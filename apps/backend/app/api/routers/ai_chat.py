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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, AliasChoices
from pydantic.config import ConfigDict
from pydantic.functional_validators import field_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_active_user
from app.db.session import SessionLocal
from app.db.models import ChatHistoryDB, ChatSessionDB, ChatSessionPinDB
from app.schemas.schemas import User
from app.services.gemini_ai_chat_service import GeminiResourceExhaustedError
from app.services.mock_ai_chat_service import MockAIChatService
from app.services.analytics_data_service import get_analysis_context, get_analysis_context_powerbi
from app.services.powerbi_service import powerbi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])

_ROLE_ORDER = {"viewer": 0, "analyst": 1, "manager": 2, "admin": 3}


class StartChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_name: str = Field(validation_alias=AliasChoices("session_name", "sessionName"))
    initial_context: Optional[str] = Field(default=None, validation_alias=AliasChoices("initial_context", "initialContext"))
    model: Optional[str] = Field(default=None, validation_alias=AliasChoices("model", "chat_model", "chatModel"))

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

    default_model = _normalize_model_id(os.getenv("GEMINI_MODEL") or settings.gemini_model or "gemini-2.0-flash") or None
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
    chat_service: AIChatService = Depends(get_chat_service),
):
    provider = _provider_name()
    selected_model: Optional[str] = None
    if request.model:
        selected_model = _assert_model_allowed(provider, request.model, current_user)
        try:
            from app.services.gemini_ai_chat_service import GeminiAIChatService

            if isinstance(chat_service, GeminiAIChatService):
                chat_service.model = selected_model
        except Exception:
            pass
    else:
        selected_model = getattr(chat_service, "model", None)

    session_id, greeting = chat_service.start_chat_session(
        session=db,
        user_id=current_user.id,
        session_name=request.session_name,
        initial_context=request.initial_context,
    )
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
    chat_service: AIChatService = Depends(get_chat_service),
):
    provider = _provider_name()
    selected_model: Optional[str] = None
    if request.model:
        selected_model = _assert_model_allowed(provider, request.model, current_user)
        try:
            from app.services.gemini_ai_chat_service import GeminiAIChatService

            if isinstance(chat_service, GeminiAIChatService):
                chat_service.model = selected_model
        except Exception:
            pass
    else:
        selected_model = getattr(chat_service, "model", None)
    session_id = (request.session_id or "").strip() or None
    created_session = False
    greeting_message: Optional[str] = None

    if not session_id:
        created_session = True
        auto_name = f"Auto session {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        session_id, greeting_message = chat_service.start_chat_session(
            session=db,
            user_id=current_user.id,
            session_name=auto_name,
            initial_context=None,
        )
    else:
        session_id = _ensure_uuid(session_id)

    try:
        resp = chat_service.send_message(
            session=db,
            session_id=session_id,
            user_id=current_user.id,
            message=request.message,
            customer_context=request.customer_context,
        )
        err = None
    except Exception as e:
        if isinstance(e, GeminiResourceExhaustedError):
            headers = {}
            retry_after = getattr(e, "retry_after_seconds", None)
            if isinstance(retry_after, int) and retry_after > 0:
                headers["Retry-After"] = str(retry_after)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e), headers=headers)

        fallback = _fallback_to_mock_enabled() and (not _looks_like_auth_or_config_error(e))
        if fallback and not isinstance(chat_service, MockAIChatService):
            mock = MockAIChatService()
            resp = mock.send_message(
                session=db,
                session_id=session_id,
                user_id=current_user.id,
                message=request.message,
                customer_context=request.customer_context,
            )
            provider = "mock"
            sources = list(getattr(resp, "sources", None) or [])
            sources.append(f"fallback:{_provider_name()}_error:{str(e)[:120]}")
            setattr(resp, "sources", sources)
            err = str(e)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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


@router.get("/history/{session_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service),
):
    session_id = _ensure_uuid(session_id)
    history = chat_service.get_chat_history(session=db, session_id=session_id, limit=limit)
    return [ChatMessageResponse(**m) for m in history]


@router.post("/close/{session_id}", response_model=SessionSummaryResponse)
async def close_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service),
):
    session_id = _ensure_uuid(session_id)
    summary = chat_service.close_chat_session(session=db, session_id=session_id)
    return SessionSummaryResponse(**summary)


@router.post("/sessions/{session_id}/close", response_model=SessionSummaryResponse)
async def close_chat_session_alias(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service),
):
    # REST-style alias for UI: /sessions/{id}/close
    session_id = _ensure_uuid(session_id)
    summary = chat_service.close_chat_session(session=db, session_id=session_id)
    return SessionSummaryResponse(**summary)


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
        exists = (
            db.query(ChatSessionPinDB)
            .filter(ChatSessionPinDB.session_id == sid, ChatSessionPinDB.user_id == row.user_id)
            .first()
        )
        if not exists:
            db.add(ChatSessionPinDB(session_id=sid, user_id=row.user_id))
        db.commit()
    except Exception as e:
        # If the optional table doesn't exist yet, return a clear message.
        if "chat_session_pin" in (str(e) or "").lower():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Pinned sessions not available: missing DB table Chat_Session_Pin. Run scripts/sqlserver_create_chat_session_pin.sql.",
            )
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
        db.query(ChatSessionPinDB).filter(ChatSessionPinDB.session_id == sid, ChatSessionPinDB.user_id == row.user_id).delete(
            synchronize_session=False
        )
        db.commit()
    except Exception as e:
        if "chat_session_pin" in (str(e) or "").lower():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Pinned sessions not available: missing DB table Chat_Session_Pin. Run scripts/sqlserver_create_chat_session_pin.sql.",
            )
        raise
    return {"success": True, "session_id": sid, "pinned": False}


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service),
):
    sessions = chat_service.get_user_sessions(session=db, user_id=current_user.id)
    out: List[ChatSessionResponse] = []
    for s in sessions:
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
