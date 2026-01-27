"""
Chatbot & interactive query endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_active_user
from app.schemas.schemas import ChatMessage, ChatRequest, ChatResponse, ChatSessionSummary, User
from app.services import chat_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_legacy_endpoint(body: ChatRequest) -> ChatResponse:
    """
    Endpoint giữ lại theo thiết kế ban đầu /api/v1/chat, không yêu cầu JWT,
    dùng cho các client đơn giản (demo, test).
    """
    answer = chat_service.simple_chat_reply(body.message)
    return ChatResponse(answer=answer)


@router.post("/chat/query", response_model=ChatResponse, tags=["chat"])
async def chat_query_endpoint(
    body: ChatRequest,
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    _, resp = chat_service.upsert_chat_session(body)
    return resp


@router.get("/chat/sessions", response_model=List[ChatSessionSummary], tags=["chat"])
async def chat_sessions_endpoint(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
) -> List[ChatSessionSummary]:
    return chat_service.list_chat_sessions(user_id)


@router.get("/chat/sessions/{session_id}", response_model=List[ChatMessage], tags=["chat"])
async def chat_session_detail_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
) -> List[ChatMessage]:
    return chat_service.get_chat_session_messages(session_id)


@router.get("/chat/suggest", response_model=List[str], tags=["chat"])
async def chat_suggest_endpoint(
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
) -> List[str]:
    return chat_service.suggest_queries(customer_id)
