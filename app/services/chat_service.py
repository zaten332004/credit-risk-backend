"""
Chat service: business logic for chatbot & interactive queries
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.models.models import ChatSession
from app.schemas.schemas import ChatMessage, ChatRequest, ChatResponse, ChatSessionSummary

# In-memory "repository" cho demo
_chat_sessions: Dict[str, ChatSession] = {}


def simple_chat_reply(message: str) -> str:
    """
    Placeholder chatbot behavior.
    Later: extend with additional LLM backends or AWS (Bedrock/Lambda) if needed.
    """
    msg = message.strip().lower()
    if "risk" in msg or "rủi ro" in msg:
        return (
            "Bạn có thể gọi POST /api/v1/risk/score với income, debt, age, credit_history_months "
            "để nhận điểm rủi ro (0..1) và nhãn low/medium/high."
        )
    if "power bi" in msg:
        return "Backend này cung cấp API để Power BI/Flutter gọi lấy điểm rủi ro và dữ liệu tổng hợp."
    return "Mình đã nhận câu hỏi. Hãy mô tả dữ liệu khách hàng/bài toán để mình hướng dẫn endpoint phù hợp."


def upsert_chat_session(body: ChatRequest) -> tuple[ChatSession, ChatResponse]:
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.utcnow()
    session = _chat_sessions.get(
        session_id,
        ChatSession(session_id=session_id, started_at=now, last_activity_at=now, messages=[]),
    )
    # Append user message
    session.messages.append({"role": "user", "content": body.message, "timestamp": now.isoformat()})
    answer = simple_chat_reply(body.message)
    session.messages.append({"role": "assistant", "content": answer, "timestamp": now.isoformat()})
    session.last_activity_at = now
    _chat_sessions[session_id] = session

    response = ChatResponse(answer=answer, extracted_metrics=None, sources=None)
    return session, response


def list_chat_sessions(user_id: Optional[int]) -> List[ChatSessionSummary]:
    return [
        ChatSessionSummary(
            session_id=s.session_id,
            started_at=s.started_at,
            last_activity_at=s.last_activity_at,
        )
        for s in _chat_sessions.values()
    ]


def get_chat_session_messages(session_id: str) -> List[ChatMessage]:
    session = _chat_sessions.get(session_id)
    if not session:
        return []
    return [
        ChatMessage(role=m["role"], content=m["content"], timestamp=datetime.fromisoformat(m["timestamp"]))
        for m in session.messages
    ]


def suggest_queries(customer_id: Optional[int]) -> List[str]:
    return [
        "Tổng dư nợ và PD trung bình của portfolio hiện tại là bao nhiêu?",
        "Liệt kê top 10 khách hàng có Expected Loss cao nhất.",
        "So sánh NPL ratio quý này với quý trước.",
    ]
