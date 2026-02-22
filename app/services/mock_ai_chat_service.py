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

            now = datetime.utcnow()
            session.add(
                ChatHistoryDB(
                    session_id=sid,
                    user_id=user_id,
                    message=message,
                    bot_response=reply,
                    created_at=now,
                )
            )
            chat_session.last_interaction = now
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
        return [
            {
                "session_id": str(s.session_id),
                "session_name": f"Session {str(s.session_id)[:8]}",
                "is_active": True,
                "created_at": s.created_at.isoformat(),
                "closed_at": None,
            }
            for s in sessions
        ]

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        return "[MOCK MODE] Report mô phỏng."

