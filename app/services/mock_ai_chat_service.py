"""
Mock AI chat service (no external API key required).

Purpose:
- Allow end-to-end testing of the AI Chatbot API/UI when GEMINI_API_KEY is unavailable.
- Persist sessions/messages to the same DB tables (Chat_Session / Chat_History).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ChatHistoryDB, ChatSessionDB
from app.services.chat_service import simple_chat_reply


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
            chat_session = ChatSessionDB(
                user_id=user_id,
                last_interaction=datetime.utcnow(),
            )
            session.add(chat_session)
            session.flush()
            session_id = chat_session.session_id

            greeting = (
                "[MOCK MODE]\n"
                "Xin chào! Hiện chưa cấu hình GEMINI_API_KEY nên hệ thống đang chạy mock chatbot.\n"
                "Bạn vẫn có thể test luồng: login → start session → send message → history/report.\n\n"
                "Bạn muốn hỏi gì về rủi ro tín dụng / portfolio / Power BI?"
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
                    created_at=datetime.utcnow(),
                )
            )
            session.commit()
            return str(session_id), greeting
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
            session_uuid = UUID(session_id)
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == session_uuid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            enhanced_message = message
            if customer_context:
                enhanced_message = (
                    "Ngữ cảnh khách hàng (customer_context):\n"
                    f"{customer_context}\n\n"
                    f"Câu hỏi: {message}"
                )

            now = datetime.utcnow()

            reply = simple_chat_reply(message)
            reply = "[MOCK MODE]\n" + reply

            session.add(
                ChatHistoryDB(
                    session_id=session_uuid,
                    user_id=user_id,
                    message=enhanced_message,
                    bot_response=reply,
                    created_at=now,
                )
            )

            chat_session.last_interaction = now
            session.commit()
            return MockChatResponse(session_id=str(session_uuid), message=reply, role="assistant", timestamp=now)
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise Exception(f"Error sending message (mock): {str(e)}")

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50) -> List[Dict]:
        try:
            session_uuid = UUID(session_id)
            messages = (
                session.query(ChatHistoryDB)
                .filter(ChatHistoryDB.session_id == session_uuid)
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
        except Exception as e:
            raise Exception(f"Error getting chat history (mock): {str(e)}")

    def close_chat_session(self, session: Session, session_id: str) -> Dict:
        try:
            session_uuid = UUID(session_id)
            chat_session = session.query(ChatSessionDB).filter(ChatSessionDB.session_id == session_uuid).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            messages = session.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == session_uuid).all()
            user_messages = len([m for m in messages if m.message])
            assistant_messages = len([m for m in messages if m.bot_response])

            chat_session.last_interaction = datetime.utcnow()
            session.commit()

            return {
                "session_id": str(session_uuid),
                "session_name": f"Session {chat_session.session_id}",
                "duration": None,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "total_messages": len(messages),
                "closed_at": None,
            }
        except Exception as e:
            session.rollback()
            raise Exception(f"Error closing chat session (mock): {str(e)}")

    def get_user_sessions(self, session: Session, user_id: int) -> List[Dict]:
        try:
            sessions = (
                session.query(ChatSessionDB)
                .filter(ChatSessionDB.user_id == user_id)
                .order_by(ChatSessionDB.created_at.desc())
                .all()
            )
            return [
                {
                    "session_id": str(s.session_id),
                    "session_name": f"Session {s.session_id}",
                    "is_active": True,
                    "created_at": s.created_at.isoformat(),
                    "closed_at": None,
                }
                for s in sessions
            ]
        except Exception as e:
            raise Exception(f"Error getting user sessions (mock): {str(e)}")

    def generate_analysis_report(self, session: Session, session_id: str) -> str:
        try:
            session_uuid = UUID(session_id)
            messages = session.query(ChatHistoryDB).filter(ChatHistoryDB.session_id == session_uuid).all()
            user_questions = [m.message for m in messages if m.message][-5:]
            report = [
                "[MOCK MODE] Báo cáo mô phỏng",
                f"Session: {session_uuid}",
                "",
                "1) Tóm tắt",
                "- Đây là báo cáo mô phỏng vì chưa có GEMINI_API_KEY.",
                "",
                "2) Các câu hỏi gần đây",
            ]
            report.extend([f"- {q}" for q in user_questions] or ["- (không có)"])
            report += [
                "",
                "3) Khuyến nghị test tiếp",
                "- Cấu hình GEMINI_API_KEY để dùng Gemini thật.",
                "- Thử gửi message kèm customer_context để kiểm tra luồng ngữ cảnh.",
            ]
            return "\n".join(report)
        except Exception as e:
            raise Exception(f"Error generating report (mock): {str(e)}")
