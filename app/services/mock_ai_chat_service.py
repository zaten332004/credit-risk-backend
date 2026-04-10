"""
Mock AI chat service (provider: mock).

No external API calls; useful for local testing and as a safe fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import ChatHistoryDB, ChatSessionDB
from app.services.chat_session_metadata import (
    build_message_with_attachments,
    build_session_metadata,
    extract_message_attachments,
    fetch_chat_session_names,
    fetch_pinned_session_ids,
    strip_session_metadata,
    summary_title_from_message,
    update_chat_session_name,
)


@dataclass
class MockChatResponse:
    session_id: str
    message: str
    role: str
    timestamp: datetime
    sources: Optional[List[str]] = None


class MockAIChatService:
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
                "[MOCK MODE]\n"
                "Xin chào! Hiện hệ thống đang chạy mock chatbot (không gọi LLM thật).\n"
                "Bạn có thể test UI/endpoint và DB session/history bình thường."
            )

            meta = build_session_metadata(session_name=session_name, initial_context=initial_context)

            session.add(
                ChatHistoryDB(
                    session_id=session_id,
                    user_id=user_id,
                    message=meta,
                    bot_response=greeting,
                    created_at=now,
                )
            )
            session.flush()
            update_chat_session_name(session, session_id, session_name)
            session.commit()
            return session_id, greeting
        except Exception as e:
            session.rollback()
            raise Exception(f"Error starting chat session (mock): {str(e)}")

    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[Dict] = None,
    ) -> MockChatResponse:
        try:
            sid = (session_id or "").strip()
            if not sid:
                raise ValueError("session_id is required")
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == sid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            reply = (
                "[MOCK MODE]\n"
                "Mình đã nhận câu hỏi. Để phân tích cụ thể hơn, hãy cung cấp thêm:\n"
                "- Thu nhập/tháng, dư nợ hiện tại\n"
                "- Điểm tín dụng, DTI\n"
                "- Mục tiêu vay và kỳ hạn\n"
            )

            prior_rows = (
                session.query(ChatHistoryDB)
                .filter(ChatHistoryDB.session_id == sid)
                .order_by(ChatHistoryDB.created_at.asc())
                .all()
            )
            prior_user_messages = sum(1 for row in prior_rows if strip_session_metadata(row.message))

            now = datetime.utcnow()
            att = None
            if isinstance(customer_context, dict):
                raw_att = customer_context.get("uploaded_files")
                att = raw_att if isinstance(raw_att, list) else None
            session.add(
                ChatHistoryDB(
                    session_id=sid,
                    user_id=user_id,
                    message=build_message_with_attachments(message, att),
                    bot_response=reply,
                    created_at=now,
                )
            )
            chat_session.last_interaction = now
            if prior_user_messages == 0:
                auto_title = summary_title_from_message(message)
                if auto_title:
                    update_chat_session_name(session, sid, auto_title)
            session.commit()
            return MockChatResponse(
                session_id=sid,
                message=reply,
                role="assistant",
                timestamp=now,
                sources=["mock"],
            )
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise Exception(f"Error sending message (mock): {str(e)}")

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
            clean_message = (strip_session_metadata(m.message) or "").strip()
            attachments = extract_message_attachments(m.message)
            if clean_message or attachments:
                out.append(
                    {
                        "role": "user",
                        "content": clean_message,
                        "timestamp": m.created_at.isoformat(),
                        "attachments": attachments,
                    }
                )
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
        session_name = fetch_chat_session_names(session, [sid]).get(sid)
        return {
            "session_id": sid,
            "session_name": session_name or f"Session {sid[:8]}",
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
        pinned_ids = fetch_pinned_session_ids(session, user_id, [str(s.session_id) for s in sessions])

        sessions = sorted(sessions, key=lambda s: (0 if str(s.session_id) in pinned_ids else 1,))
        session_names = fetch_chat_session_names(session, [str(s.session_id) for s in sessions])
        return [
            {
                "session_id": str(s.session_id),
                "session_name": session_names.get(str(s.session_id)) or f"Session {str(s.session_id)[:8]}",
                "is_active": True,
                "is_pinned": str(s.session_id) in pinned_ids,
                "created_at": s.created_at.isoformat(),
                "closed_at": None,
            }
            for s in sessions
        ]

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        return "[MOCK MODE] Report mô phỏng."

