"""
Gemini AI Chat service (provider: gemini) using `google-genai`.
Đọc dữ liệu từ cùng DB mà Power BI dùng, đưa vào context để AI phân tích theo yêu cầu người dùng.

Env (.env) keys supported:
- gemini_api_key / GEMINI_API_KEY
- GEMINI_MODEL (optional, default: gemini-2.0-flash)
"""

from __future__ import annotations

import logging
import os
import re
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatHistoryDB, ChatSessionDB, ChatSessionPinDB
from app.services.analytics_data_service import get_analysis_context

logger = logging.getLogger(__name__)


@dataclass
class GeminiChatResponse:
    session_id: str
    message: str
    role: str
    timestamp: datetime
    sources: Optional[List[str]] = None


class GeminiResourceExhaustedError(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _parse_retry_after_seconds(msg: str) -> Optional[int]:
    s = msg or ""

    m = re.search(r"retryDelay'\s*:\s*'(?P<sec>[0-9]+)s'", s)
    if m:
        return int(m.group("sec"))

    m = re.search(r"retry in\s+(?P<sec>[0-9]+(?:\.[0-9]+)?)s", s, flags=re.IGNORECASE)
    if m:
        return int(math.ceil(float(m.group("sec"))))

    return None


def _looks_like_resource_exhausted(msg: str) -> bool:
    s = (msg or "").lower()
    return ("resource_exhausted" in s or "quota exceeded" in s) and (
        "429" in s or "code': 429" in s or "code\": 429" in s
    )


class GeminiAIChatService:
    SYSTEM_PROMPT = (
        "Bạn là chuyên gia tài chính và quản lý rủi ro trong ngân hàng Việt Nam. "
        "Bạn sẽ được cung cấp dữ liệu hiện tại từ hệ thống (cùng nguồn với Power BI): "
        "tổng quan danh mục, phân bố rủi ro, top khách hàng. Hãy phân tích theo đúng câu hỏi của người dùng "
        "dựa trên dữ liệu đó; trả lời bằng tiếng Việt, chuyên nghiệp, có công thức/ví dụ/khuyến nghị khi phù hợp. "
        "Nếu thiếu dữ liệu cho câu hỏi thì nói rõ và gợi ý thông tin cần bổ sung."
    )

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.gemini_api_key or None
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set GEMINI_API_KEY (or gemini_api_key) in .env")

        raw_model = (model or os.getenv("GEMINI_MODEL") or settings.gemini_model or "gemini-2.0-flash").strip()
        if raw_model.startswith("models/"):
            raw_model = raw_model[len("models/") :]
        self.model = raw_model

        try:
            # google-genai (new SDK)
            from google import genai  # type: ignore
        except Exception as e:
            raise RuntimeError(f"google-genai is not installed or import failed: {e}")

        self._genai = genai
        self.client = genai.Client(api_key=self.api_key)

    def start_chat_session(
        self,
        session: Session,
        user_id: int,
        session_name: str,
        initial_context: Optional[str] = None,
    ) -> Tuple[str, str]:
        try:
            now = datetime.utcnow()
            session_id = str(uuid.uuid4())
            chat_session = ChatSessionDB(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_interaction=now,
            )
            session.add(chat_session)

            greeting = (
                "Xin chào! Mình là trợ lý AI phân tích rủi ro tín dụng. "
                "Bạn muốn phân tích khách hàng cụ thể hay tổng quan danh mục?"
            )
            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=user_id,
                    message="",
                    bot_response=greeting,
                    created_at=now,
                )
            )
            session.commit()
            return session_id, greeting
        except Exception as e:
            session.rollback()
            raise Exception(f"Error starting chat session (gemini): {str(e)}")

    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[Dict] = None,
    ) -> GeminiChatResponse:
        try:
            sid = _normalize_session_id(session_id)
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            history_rows = (
                session.query(ChatHistoryDB)
                .filter(ChatHistoryDB.session_id == sid)
                .order_by(ChatHistoryDB.created_at)
                .limit(20)
                .all()
            )

            contents: List[dict] = []
            contents.append({"role": "user", "parts": [{"text": f"[SYSTEM]\n{self.SYSTEM_PROMPT}"}]})

            for row in history_rows:
                if row.message:
                    contents.append({"role": "user", "parts": [{"text": row.message}]})
                if row.bot_response:
                    contents.append({"role": "model", "parts": [{"text": row.bot_response}]})

            # Đưa dữ liệu từ DB (cùng nguồn Power BI) vào context để Gemini phân tích theo yêu cầu
            data_context = ""
            try:
                context_source = (os.getenv("AI_CHAT_CONTEXT_SOURCE") or settings.ai_chat_context_source or "db").strip().lower()
                if context_source == "powerbi":
                    from app.services.analytics_data_service import get_analysis_context_powerbi

                    data_context = get_analysis_context_powerbi()
                else:
                    data_context = get_analysis_context(session)
            except Exception as e:
                logger.warning("Could not load analytics context for AI: %s", e)
            user_text = message
            if data_context.strip():
                user_text = (
                    "[DỮ LIỆU HIỆN TẠI TỪ HỆ THỐNG]\n"
                    + data_context.strip()
                    + "\n\n[CÂU HỎI / YÊU CẦU PHÂN TÍCH CỦA NGƯỜI DÙNG]\n"
                    + message
                )
            if customer_context:
                user_text = (
                    "[THÔNG TIN KHÁCH HÀNG (nếu có)]\n"
                    + str(customer_context)
                    + "\n\n"
                    + user_text
                )
            contents.append({"role": "user", "parts": [{"text": user_text}]})

            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
            except Exception as e:
                msg = str(e)
                if _looks_like_resource_exhausted(msg):
                    retry_after = _parse_retry_after_seconds(msg)
                    detail = (msg or "").strip()
                    if len(detail) > 800:
                        detail = detail[:800] + "..."
                    raise GeminiResourceExhaustedError(
                        message=(
                            "Gemini quota/rate limit exceeded (429 RESOURCE_EXHAUSTED)."
                            + (f" Retry after {retry_after}s." if retry_after else "")
                            + (f" Detail: {detail}" if detail else "")
                        ),
                        retry_after_seconds=retry_after,
                    ) from e
                raise

            ai_text = _extract_text(resp)
            if not ai_text:
                ai_text = "Mình chưa nhận được nội dung trả lời từ mô hình. Bạn thử lại giúp mình nhé."

            now = datetime.utcnow()
            session.add(
                ChatHistoryDB(
                    session_id=sid,
                    user_id=user_id,
                    message=message,
                    bot_response=ai_text,
                    created_at=now,
                )
            )
            chat_session.last_interaction = now
            session.commit()

            return GeminiChatResponse(
                session_id=sid,
                message=ai_text,
                role="assistant",
                timestamp=now,
                sources=None,
            )
        except ValueError:
            session.rollback()
            raise
        except GeminiResourceExhaustedError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise Exception(f"Error sending message (gemini): {str(e)}")

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50) -> List[Dict]:
        sid = _normalize_session_id(session_id)
        rows = (
            session.query(ChatHistoryDB)
            .filter(ChatHistoryDB.session_id == sid)
            .order_by(ChatHistoryDB.created_at)
            .limit(limit)
            .all()
        )
        out: List[Dict] = []
        for r in rows:
            ts = r.created_at.isoformat()
            if r.message:
                out.append({"role": "user", "content": r.message, "timestamp": ts})
            if r.bot_response:
                out.append({"role": "assistant", "content": r.bot_response, "timestamp": ts})
        return out

    def close_chat_session(self, session: Session, session_id: str) -> Dict:
        sid = _normalize_session_id(session_id)
        chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
        if not chat_session:
            raise ValueError(f"Chat session {session_id} not found")
        rows = session.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == sid).all()
        user_messages = sum(1 for r in rows if r.message)
        assistant_messages = sum(1 for r in rows if r.bot_response)
        now = datetime.utcnow()
        chat_session.last_interaction = now
        session.commit()
        return {
            "session_id": sid,
            "session_name": f"Session {sid[:8]}",
            "duration": None,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_messages": len(rows),
            "closed_at": now.isoformat(),
        }

    def get_user_sessions(self, session: Session, user_id: int) -> List[Dict]:
        sessions = (
            session.query(ChatSessionDB)
            .filter(ChatSessionDB.user_id == user_id)
            .order_by(ChatSessionDB.created_at.desc())
            .all()
        )
        pinned_ids = set()
        try:
            pinned_rows = session.query(ChatSessionPinDB.session_id).filter(ChatSessionPinDB.user_id == user_id).all()
            pinned_ids = {str(r[0]) for r in pinned_rows}
        except Exception:
            pinned_ids = set()

        # Stable sort: pinned first, then by created_at desc (already ordered)
        sessions = sorted(sessions, key=lambda s: (0 if str(s.session_id) in pinned_ids else 1,))
        return [
            {
                "session_id": str(s.session_id),
                "session_name": f"Session {str(s.session_id)[:8]}",
                "is_active": True,
                "is_pinned": str(s.session_id) in pinned_ids,
                "created_at": s.created_at.isoformat(),
                "closed_at": s.last_interaction.isoformat() if s.last_interaction else None,
            }
            for s in sessions
        ]

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        return "[GEMINI MODE] Report chưa được triển khai riêng."


def _extract_text(resp) -> str:
    # google-genai responses commonly expose `.text`
    txt = getattr(resp, "text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    # Try to walk common fields
    candidates = getattr(resp, "candidates", None)
    if candidates:
        try:
            cand0 = candidates[0]
            content = getattr(cand0, "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t.strip():
                        texts.append(t.strip())
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass
    return ""


def _normalize_session_id(session_id: str) -> str:
    s = (session_id or "").strip()
    if not s:
        raise ValueError("session_id is required")
    return s
