"""
Langflow AI chat service (provider: langflow).

Env vars:
- LANGFLOW_RUN_URL (recommended): full run endpoint, e.g. http://localhost:7860/api/v1/run/<FLOW_ID>
- OR: LANGFLOW_BASE_URL + LANGFLOW_FLOW_ID
- LANGFLOW_API_KEY (optional): Bearer token
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.db.models import ChatHistoryDB, ChatSessionDB, ChatSessionPinDB


@dataclass
class LangflowChatResponse:
    session_id: str
    message: str
    role: str
    timestamp: datetime
    sources: Optional[List[str]] = None


class LangflowAIChatService:
    def __init__(self) -> None:
        run_url = (os.getenv("LANGFLOW_RUN_URL") or "").strip()
        base_url = (os.getenv("LANGFLOW_BASE_URL") or "").strip().rstrip("/")
        flow_id = (os.getenv("LANGFLOW_FLOW_ID") or "").strip()

        if run_url:
            self.run_url = run_url
        elif base_url and flow_id:
            self.run_url = f"{base_url}/api/v1/run/{flow_id}"
        else:
            raise ValueError("Langflow not configured. Set LANGFLOW_RUN_URL or LANGFLOW_BASE_URL + LANGFLOW_FLOW_ID.")

        self.api_key = (os.getenv("LANGFLOW_API_KEY") or "").strip() or None

    def start_chat_session(
        self, session: Session, user_id: int, session_name: str, initial_context: Optional[str] = None
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
                "[LANGFLOW MODE]\n"
                "Xin chào! Mình có thể hỗ trợ phân tích rủi ro tín dụng, portfolio và dữ liệu Power BI."
            )

            meta = f"[SESSION_NAME]{session_name}[/SESSION_NAME]"
            if initial_context:
                meta += f"\n[INITIAL_CONTEXT]{initial_context}[/INITIAL_CONTEXT]"

            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=user_id,
                    message=meta,
                    bot_response=greeting,
                    created_at=now,
                )
            )
            session.commit()
            return session_id, greeting
        except Exception as e:
            session.rollback()
            raise Exception(f"Error starting chat session (langflow): {str(e)}")

    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[Dict] = None,
    ) -> LangflowChatResponse:
        try:
            sid = (session_id or "").strip()
            if not sid:
                raise ValueError("session_id is required")
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            enhanced_message, sources = self._build_context_prompt(
                message=message, customer_context=customer_context or {}, user_id=user_id
            )

            text = self._run_flow(session_id=session_id, input_value=enhanced_message)

            now = datetime.utcnow()
            session.add(
                ChatHistoryDB(
                    session_id=sid,
                    user_id=user_id,
                    message=enhanced_message,
                    bot_response=text,
                    created_at=now,
                )
            )
            chat_session.last_interaction = now
            session.commit()

            return LangflowChatResponse(
                session_id=sid,
                message=text,
                role="assistant",
                timestamp=now,
                sources=sources or None,
            )
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise Exception(f"Error sending message (langflow): {str(e)}")

    def _run_flow(self, *, session_id: str, input_value: str) -> str:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "input_value": input_value,
            "input_type": "chat",
            "output_type": "chat",
            "session_id": session_id,
        }

        with httpx.Client(timeout=30.0) as client:
            r = client.post(self.run_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        extracted = _extract_text(data)
        return extracted or json.dumps(data, ensure_ascii=False)[:4000]

    def _build_context_prompt(self, *, message: str, customer_context: Dict, user_id: int) -> tuple[str, List[str]]:
        context_parts: List[str] = []
        sources: List[str] = []

        if customer_context.get("customer_id"):
            context_parts.append(f"[Khách hàng ID: {customer_context.get('customer_id')}]")

        if context_parts:
            return "\n".join(context_parts) + "\n\n" + message, sources
        return message, sources

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50) -> List[Dict]:
        sid = (session_id or "").strip()
        messages = (
            session.query(ChatHistoryDB)
            .filter(ChatHistoryDB.session_id == sid)
            .order_by(ChatHistoryDB.created_at)
            .limit(limit)
            .all()
        )
        out: List[Dict] = []
        for m in messages:
            if m.message:
                out.append({"role": "user", "content": m.message, "timestamp": m.created_at.isoformat()})
            if m.bot_response:
                out.append({"role": "assistant", "content": m.bot_response, "timestamp": m.created_at.isoformat()})
        return out

    def close_chat_session(self, session: Session, session_id: str) -> Dict:
        sid = (session_id or "").strip()
        chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
        if not chat_session:
            raise ValueError(f"Chat session {session_id} not found")
        messages = session.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == sid).all()
        user_messages = len([m for m in messages if m.message])
        assistant_messages = len([m for m in messages if m.bot_response])
        chat_session.last_interaction = datetime.utcnow()
        session.commit()
        return {
            "session_id": sid,
            "session_name": f"Session {sid[:8]}",
            "duration": None,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_messages": len(messages),
            "closed_at": None,
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

        sessions = sorted(sessions, key=lambda s: (0 if str(s.session_id) in pinned_ids else 1,))
        return [
            {
                "session_id": str(s.session_id),
                "session_name": f"Session {str(s.session_id)[:8]}",
                "is_active": True,
                "is_pinned": str(s.session_id) in pinned_ids,
                "created_at": s.created_at.isoformat(),
                "closed_at": None,
            }
            for s in sessions
        ]

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        return "[LANGFLOW MODE] Report chưa được cấu hình riêng. Hãy tạo một flow report nếu cần."


def _extract_text(obj: Any) -> Optional[str]:
    preferred = {"text", "message", "content", "output", "result", "answer"}

    def walk(x: Any) -> Optional[str]:
        if isinstance(x, str):
            s = x.strip()
            return s or None
        if isinstance(x, dict):
            for k in preferred:
                if k in x:
                    out = walk(x.get(k))
                    if out:
                        return out
            for v in x.values():
                out = walk(v)
                if out:
                    return out
        if isinstance(x, list):
            for v in x:
                out = walk(v)
                if out:
                    return out
        return None

    return walk(obj)
