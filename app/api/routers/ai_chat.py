"""
Gemini AI Chatbot API Router
Endpoints for chat conversations with financial risk analysis
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Protocol
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import get_current_active_user
from app.schemas.schemas import User
from app.services.mock_ai_chat_service import MockAIChatService


# Router
router = APIRouter(prefix="/ai-chat", tags=["AI Chat - Gemini"])


# Schemas
class StartChatRequest(BaseModel):
    """Request to start a new chat session"""
    session_name: str
    initial_context: Optional[str] = None
    
    class Config:
        example = {
            "session_name": "Phân tích rủi ro - Khách hàng ABC",
            "initial_context": "Customer: ABC Corp, Credit Score: 750, Income: 5B VND/year"
        }


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    session_id: str
    message: str
    customer_context: Optional[dict] = None
    
    class Config:
        example = {
            "session_id": "00000000-0000-0000-0000-000000000000",
            "message": "Phân tích rủi ro tín dụng cho khách hàng này",
            "customer_context": {
                "customer_id": 1,
                "full_name": "ABC Company",
                "credit_score": 750,
                "annual_income": 5000000000
            }
        }


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    role: str
    content: str
    timestamp: str


class StartChatResponse(BaseModel):
    """Response when starting a chat session"""
    session_id: str
    greeting_message: str
    created_at: str


class SendMessageResponse(BaseModel):
    """Response from sending a message"""
    session_id: str
    message: str
    role: str
    timestamp: str


class ChatSessionResponse(BaseModel):
    """Chat session summary"""
    session_id: str
    session_name: str
    is_active: bool
    created_at: str
    closed_at: Optional[str] = None


class SessionSummaryResponse(BaseModel):
    """Session summary when closing"""
    session_id: str
    session_name: str
    duration: Optional[float]
    user_messages: int
    assistant_messages: int
    total_messages: int
    closed_at: Optional[str]


# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chat_service():
    """Get AI chat service (Gemini or Mock)."""
    provider = (os.getenv("AI_CHAT_PROVIDER") or "gemini").strip().lower()

    if provider == "mock":
        return MockAIChatService()

    # Default: Gemini
    try:
        from app.services.gemini_ai_chat_service import GeminiAIChatService

        return GeminiAIChatService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to initialize AI chat service: {str(e)}. "
                "If you don't have a Gemini key, set AI_CHAT_PROVIDER=mock and restart the server."
            ),
        )


class AIChatService(Protocol):
    def start_chat_session(
        self, session: Session, user_id: int, session_name: str, initial_context: Optional[str] = None
    ): ...

    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[dict] = None,
    ): ...

    def get_chat_history(self, session: Session, session_id: str, limit: int = 50): ...

    def close_chat_session(self, session: Session, session_id: str): ...

    def get_user_sessions(self, session: Session, user_id: int): ...

    def generate_analysis_report(self, session: Session, session_id: str): ...


# Endpoints

@router.post("/start", response_model=StartChatResponse)
async def start_chat_session(
    request: StartChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Start a new AI chat session
    
    Parameters:
    - session_name: Name for this chat session
    - initial_context: Optional context (customer info, previous analysis, etc)
    
    Returns:
    - session_id: ID of the new chat session
    - greeting_message: AI's greeting message
    """
    try:
        session_id, greeting = chat_service.start_chat_session(
            session=db,
            user_id=current_user.id,
            session_name=request.session_name,
            initial_context=request.initial_context
        )
        
        return StartChatResponse(
            session_id=session_id,
            greeting_message=greeting,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Send a message in a chat session
    
    Parameters:
    - session_id: ID of the chat session
    - message: User's message
    - customer_context: Optional customer data for context-aware analysis
    
    Returns:
    - AI response message with timestamp
    """
    try:
        response = chat_service.send_message(
            session=db,
            session_id=request.session_id,
            user_id=current_user.id,
            message=request.message,
            customer_context=request.customer_context
        )
        
        return SendMessageResponse(
            session_id=response.session_id,
            message=response.message,
            role=response.role,
            timestamp=response.timestamp.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history/{session_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Get chat history for a session
    
    Parameters:
    - session_id: ID of the chat session
    - limit: Maximum number of messages to return (default 50)
    
    Returns:
    - List of chat messages with timestamps
    """
    try:
        history = chat_service.get_chat_history(
            session=db,
            session_id=session_id,
            limit=limit
        )
        
        return [
            ChatMessageResponse(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in history
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/close/{session_id}", response_model=SessionSummaryResponse)
async def close_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Close a chat session
    
    Parameters:
    - session_id: ID of the chat session to close
    
    Returns:
    - Session summary with statistics
    """
    try:
        summary = chat_service.close_chat_session(
            session=db,
            session_id=session_id
        )
        
        return SessionSummaryResponse(**summary)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Get all chat sessions for current user
    
    Returns:
    - List of user's chat sessions sorted by creation date (newest first)
    """
    try:
        sessions = chat_service.get_user_sessions(
            session=db,
            user_id=current_user.id
        )
        
        return [
            ChatSessionResponse(**s)
            for s in sessions
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/models")
async def list_available_models(
    current_user: User = Depends(get_current_active_user),
):
    """
    List available Gemini models for the current API key/project.

    If you're seeing "model not found", use this endpoint to pick a supported model id
    and set it via env var `GEMINI_MODEL` (restart server after changing env).
    """
    try:
        from app.services.gemini_ai_chat_service import genai

        models = []
        for m in genai.list_models():
            models.append(
                {
                    "name": getattr(m, "name", None),
                    "display_name": getattr(m, "display_name", None),
                    "supported_generation_methods": getattr(m, "supported_generation_methods", None),
                }
            )
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/report/{session_id}")
async def generate_analysis_report(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_service: AIChatService = Depends(get_chat_service)
):
    """
    Generate an analysis report from chat conversation
    
    Parameters:
    - session_id: ID of the chat session
    
    Returns:
    - Generated analysis report based on conversation
    """
    try:
        report = chat_service.generate_analysis_report(
            session=db,
            session_id=session_id
        )
        
        return {
            "session_id": session_id,
            "report": report,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
