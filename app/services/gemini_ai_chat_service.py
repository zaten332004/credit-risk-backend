"""
Gemini AI Chatbot Service for Financial Risk Analysis
Integrates Google's Gemini AI with credit risk system
"""
import os
import json
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ChatSessionDB, ChatHistoryDB, UserDB
from app.services.powerbi_service import powerbi_service


@dataclass
class ChatMessage:
    """Chat message structure"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class ChatResponse:
    """Chat response structure"""
    session_id: str
    message: str
    role: str
    timestamp: datetime
    sources: Optional[List[str]] = None  # References/sources used


class GeminiAIChatService:
    """
    Gemini AI Chatbot Service for Financial Risk Analysis
    
    Features:
    - Real-time chat with Gemini AI
    - Financial risk analysis expertise
    - Chat history management
    - Session management
    - Context-aware responses
    """
    
    # System prompt for financial risk analysis
    SYSTEM_PROMPT = """
Bạn là một chuyên gia tài chính và quản lý rủi ro có kinh nghiệm trong ngân hàng Việt Nam.
Nhiệm vụ của bạn là:

1. **Phân Tích Rủi Ro Tín Dụng**
   - Đánh giá điểm tín dụng (credit score)
   - Phân loại khách hàng theo nhóm rủi ro
   - Dự báo khả năng vỡ nợ (PD - Probability of Default)
   - Tính tổn thất nếu vỡ nợ (LGD - Loss Given Default)
   - Xác định hạn mức vay phù hợp (EAD - Exposure at Default)

2. **Đánh Giá Khách Hàng**
   - Phân tích cấu trúc vốn (balance sheet)
   - Đánh giá dòng tiền (cash flow analysis)
   - Tính ratio tài chính (DTI, ROA, ROE, etc.)
   - Đánh giá lịch sử thanh toán
   - Phân tích ngành kinh doanh

3. **Quản Lý Portfolio**
   - Tính NPL ratio (Non-Performing Loan)
   - Phân tích concentration risk
   - Đề xuất diversification
   - Tính provision allocation
   - Monitoring escalation

4. **Tư Vấn Sản Phẩm Vay**
   - Khuyến nghị loại vay phù hợp
   - Tính toán lãi suất phù hợp
   - Đánh giá điều kiện vay
   - So sánh các sản phẩm

5. **Tuân Thủ Quy Định**
   - Hướng dẫn quy định SBV (Circular 11/2021)
   - Tuân thủ Basel III
   - Giải thích yêu cầu pháp lý
   - Cảnh báo rủi ro pháp lý

Trả lời bằng **tiếng Việt** một cách chuyên nghiệp, logic, có thể cung cấp:
- Phân tích chi tiết
- Công thức tính toán
- Ví dụ cụ thể
- Khuyến nghị hành động
- Cảnh báo rủi ro

Luôn tuân thủ quy định ngân hàng Việt Nam và chuẩn mực quốc tế.
"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini AI service"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set GEMINI_API_KEY environment variable"
            )
        
        genai.configure(api_key=self.api_key)

        model_name = self._resolve_model_name(os.getenv("GEMINI_MODEL"))

        # Initialize model
        self.model = genai.GenerativeModel(model_name=model_name, system_instruction=self.SYSTEM_PROMPT)
        
        # Chat configuration
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_output_tokens": 2048,
            "response_mime_type": "text/plain"
        }

    def _resolve_model_name(self, preferred: Optional[str]) -> str:
        """
        Resolve a model name that is available for the current API key/project and supports generateContent.

        Notes:
        - `google.generativeai` returns model names like `models/<id>` via list_models().
        - Some keys/projects may not have access to certain model IDs.
        """
        preferred = (preferred or "").strip()

        try:
            models = list(genai.list_models())
        except Exception:
            # If listing models fails, fall back to the preferred value or a sane default.
            return preferred or "gemini-1.5-flash"

        supported = []
        for m in models:
            name = getattr(m, "name", None)
            methods = getattr(m, "supported_generation_methods", None) or []
            if name and any(str(x).lower() == "generatecontent" for x in methods):
                supported.append(str(name))

        if not supported:
            return preferred or "gemini-1.5-flash"

        # Try preferred first: accept either "gemini-*" or "models/gemini-*"
        if preferred:
            preferred_norm = preferred if preferred.startswith("models/") else f"models/{preferred}"
            for cand in (preferred, preferred_norm):
                if cand in supported:
                    return cand

        # Otherwise pick the first match from a stable preference list.
        preference = [
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro-latest",
            "models/gemini-1.5-pro",
            "models/gemini-pro",
        ]
        for p in preference:
            if p in supported:
                return p

        # Last resort: whatever is available.
        return supported[0]
    
    def start_chat_session(
        self,
        session: Session,
        user_id: int,
        session_name: str,
        initial_context: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Start a new chat session
        
        Args:
            session: Database session
            user_id: User ID
            session_name: Name for this chat session
            initial_context: Optional initial context (customer info, risk analysis, etc.)
            
        Returns:
            (session_id, greeting_message)
        """
        try:
            # Create chat session in database
            chat_session = ChatSessionDB(
                user_id=user_id,
                last_interaction=datetime.utcnow(),
            )
            session.add(chat_session)
            session.flush()
            session_id = chat_session.session_id
            
            # Create greeting message
            greeting = f"Xin chào! Tôi là trợ lý tài chính AI của bạn.\n"
            greeting += f"Tôi sẵn sàng giúp bạn:\n"
            greeting += f"• Phân tích rủi ro tín dụng\n"
            greeting += f"• Đánh giá khách hàng\n"
            greeting += f"• Quản lý portfolio\n"
            greeting += f"• Tư vấn sản phẩm vay\n"
            greeting += f"• Giải thích quy định ngân hàng\n\n"
            greeting += f"Bạn muốn tôi giúp gì?"
            
            # Persist session metadata in first history row (DB schema doesn't have session_name columns)
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
            raise Exception(f"Error starting chat session: {str(e)}")
    
    def send_message(
        self,
        session: Session,
        session_id: str,
        user_id: int,
        message: str,
        customer_context: Optional[Dict] = None
    ) -> ChatResponse:
        """
        Send a message and get response from Gemini AI
        
        Args:
            session: Database session
            session_id: Chat session ID
            user_id: User ID
            message: User message
            customer_context: Optional customer data context
            
        Returns:
            ChatResponse with AI response
        """
        try:
            session_uuid = UUID(session_id)

            # Get chat session
            chat_session = session.query(ChatSessionDB).filter(
                ChatSessionDB.session_id == session_uuid
            ).first()
            
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")
            
            # Build context-aware prompt
            enhanced_message = message
            if customer_context:
                enhanced_message = self._build_context_prompt(
                    message,
                    customer_context
                )
            
            # Get chat history for context
            history = session.query(ChatHistoryDB).filter(
                ChatHistoryDB.session_id == session_uuid
            ).order_by(ChatHistoryDB.created_at).limit(20).all()
            
            # Build conversation history
            conversation = []
            for msg in history:
                if msg.message:
                    conversation.append({"role": "user", "parts": [msg.message]})
                if msg.bot_response:
                    # Gemini API expects roles: "user" or "model"
                    conversation.append({"role": "model", "parts": [msg.bot_response]})
            
            # Add current message
            conversation.append({
                "role": "user",
                "parts": [enhanced_message]
            })
            
            # Get response from Gemini
            response = self.model.generate_content(
                conversation,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            ai_response = response.text

            now = datetime.utcnow()
            session.add(
                ChatHistoryDB(
                    session_id=session_uuid,
                    user_id=user_id,
                    message=enhanced_message,
                    bot_response=ai_response,
                    created_at=now,
                )
            )

            chat_session.last_interaction = now
            session.commit()
            
            return ChatResponse(
                session_id=str(session_uuid),
                message=ai_response,
                role="assistant",
                timestamp=now
            )
            
        except Exception as e:
            session.rollback()
            raise Exception(f"Error sending message: {str(e)}")
    
    def _build_context_prompt(
        self,
        message: str,
        customer_context: Dict,
        user: Optional[UserDB] = None
    ) -> str:
        """
        Build context-aware prompt with customer information and Power BI data
        
        Args:
            message: Original user message
            customer_context: Customer data dictionary
            user: Optional user object for Power BI integration
            
        Returns:
            Enhanced prompt with context and Power BI data
        """
        context_parts = []
        
        # Add customer info if available
        if customer_context.get("customer_id"):
            context_parts.append(
                f"[Khách hàng ID: {customer_context.get('customer_id')}]"
            )
        
        if customer_context.get("full_name"):
            context_parts.append(
                f"[Tên: {customer_context.get('full_name')}]"
            )
        
        if customer_context.get("credit_score"):
            context_parts.append(
                f"[Điểm tín dụng: {customer_context.get('credit_score')}]"
            )
        
        if customer_context.get("annual_income"):
            context_parts.append(
                f"[Thu nhập năm: VND {customer_context.get('annual_income'):,.0f}]"
            )
        
        if customer_context.get("outstanding_balance"):
            context_parts.append(
                f"[Dư nợ hiện tại: VND {customer_context.get('outstanding_balance'):,.0f}]"
            )
        
        if customer_context.get("risk_group"):
            context_parts.append(
                f"[Nhóm rủi ro: {customer_context.get('risk_group')}]"
            )
        
        # Add Power BI data if user is configured
        if user and user.power_bi_enabled:
            try:
                # Try to fetch Power BI risk data
                customer_id = customer_context.get("customer_id")
                if customer_id:
                    risk_profile = powerbi_service.get_customer_risk_profile(user, customer_id)
                    if risk_profile:
                        context_parts.append("[Dữ liệu từ Power BI]")
                        # Add Power BI data summary (simplified)
                        context_parts.append("Dữ liệu rủi ro từ hệ thống Power BI đã được tải")
            except Exception as e:
                # Log but don't fail if Power BI fetch fails
                print(f"Note: Không thể tải dữ liệu Power BI: {str(e)}")
        
        # Combine context with message
        if context_parts:
            return "\n".join(context_parts) + "\n\n" + message
        
        return message
    
    def get_chat_history(
        self,
        session: Session,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get chat history for a session
        
        Args:
            session: Database session
            session_id: Chat session ID
            limit: Maximum number of messages
            
        Returns:
            List of chat messages
        """
        try:
            session_uuid = UUID(session_id)
            messages = session.query(ChatHistoryDB).filter(
                ChatHistoryDB.session_id == session_uuid
            ).order_by(ChatHistoryDB.created_at).limit(limit).all()

            out: List[Dict] = []
            for m in messages:
                if m.message:
                    out.append({"role": "user", "content": m.message, "timestamp": m.created_at.isoformat()})
                if m.bot_response:
                    out.append({"role": "assistant", "content": m.bot_response, "timestamp": m.created_at.isoformat()})
            return out
            
        except Exception as e:
            raise Exception(f"Error getting chat history: {str(e)}")
    
    def close_chat_session(
        self,
        session: Session,
        session_id: str
    ) -> Dict:
        """
        Close a chat session and get summary
        
        Args:
            session: Database session
            session_id: Chat session ID
            
        Returns:
            Session summary with statistics
        """
        try:
            session_uuid = UUID(session_id)
            chat_session = session.query(ChatSessionDB).filter(
                ChatSessionDB.session_id == session_uuid
            ).first()
            
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")
            
            # Get statistics
            messages = session.query(ChatHistoryDB).filter(
                ChatHistoryDB.session_id == session_uuid
            ).all()
            
            user_messages = len([m for m in messages if m.role == "user"])
            assistant_messages = len([m for m in messages if m.role == "assistant"])
            
            # No explicit close columns in current DB schema; update last interaction.
            chat_session.last_interaction = datetime.utcnow()
            session.commit()
            
            return {
                "session_id": str(session_uuid),
                "session_name": f"Session {chat_session.session_id}",
                "duration": None,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "total_messages": len(messages),
                "closed_at": None
            }
            
        except Exception as e:
            session.rollback()
            raise Exception(f"Error closing chat session: {str(e)}")
    
    def get_user_sessions(
        self,
        session: Session,
        user_id: int
    ) -> List[Dict]:
        """
        Get all chat sessions for a user
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            List of user's chat sessions
        """
        try:
            sessions = session.query(ChatSessionDB).filter(
                ChatSessionDB.user_id == user_id
            ).order_by(ChatSessionDB.created_at.desc()).all()
            
            return [
                {
                    "session_id": str(s.session_id),
                    "session_name": f"Session {s.session_id}",
                    "is_active": True,
                    "created_at": s.created_at.isoformat(),
                    "closed_at": None
                }
                for s in sessions
            ]
            
        except Exception as e:
            raise Exception(f"Error getting user sessions: {str(e)}")
    
    def generate_analysis_report(
        self,
        session: Session,
        session_id: str
    ) -> str:
        """
        Generate analysis report from chat conversation
        
        Args:
            session: Database session
            session_id: Chat session ID
            
        Returns:
            Generated report
        """
        try:
            session_uuid = UUID(session_id)
            # Get chat history
            messages = session.query(ChatHistoryDB).filter(
                ChatHistoryDB.session_id == session_uuid
            ).all()
            
            # Build conversation summary
            conversation_text = ""
            for msg in messages:
                if msg.message:
                    conversation_text += f"\nUSER:\n{msg.message}\n"
                if msg.bot_response:
                    conversation_text += f"\nASSISTANT:\n{msg.bot_response}\n"
            
            # Generate report using Gemini
            report_prompt = f"""
Dựa trên cuộc trò chuyện sau, hãy tạo một báo cáo phân tích rủi ro tài chính chuyên nghiệp:

{conversation_text}

Báo cáo nên bao gồm:
1. Tóm tắt điểm chính
2. Đánh giá rủi ro tổng thể
3. Các chỉ số chính (KPIs)
4. Khuyến nghị hành động
5. Cảnh báo rủi ro

Định dạng báo cáo sao cho dễ đọc, chuyên nghiệp, phù hợp với tiêu chuẩn ngân hàng.
"""
            
            response = self.model.generate_content(
                report_prompt,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error generating report: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Initialize service
    chat_service = GeminiAIChatService()
    
    # Create session
    session = SessionLocal()
    
    try:
        # Start a chat session
        print("Starting chat session...")
        session_id, greeting = chat_service.start_chat_session(
            session=session,
            user_id=1,
            session_name="Financial Risk Analysis - Customer ABC",
            initial_context="Customer: ABC Company, Credit Score: 750, Income: 5B VND/year"
        )
        
        print(f"Session ID: {session_id}")
        print(f"Greeting: {greeting}\n")
        
        # Test messages
        test_messages = [
            "Phân tích rủi ro tín dụng cho khách hàng này",
            "Khách hàng này nên vay bao nhiêu tiền tối đa?",
            "Làm thế nào để giảm thiểu rủi ro?"
        ]
        
        for message in test_messages:
            print(f"\nUser: {message}")
            response = chat_service.send_message(
                session=session,
                session_id=session_id,
                user_id=1,
                message=message,
                customer_context={
                    "customer_id": 1,
                    "full_name": "ABC Company",
                    "credit_score": 750,
                    "annual_income": 5_000_000_000,
                    "outstanding_balance": 1_500_000_000,
                    "risk_group": "Group 1"
                }
            )
            print(f"Assistant: {response.message[:200]}...")
        
        # Get chat history
        history = chat_service.get_chat_history(session, session_id)
        print(f"\n\nChat History ({len(history)} messages):")
        for msg in history[-3:]:  # Last 3 messages
            print(f"{msg['role'].upper()}: {msg['content'][:100]}...")
        
        # Close session
        summary = chat_service.close_chat_session(session, session_id)
        print(f"\n\nSession Summary:")
        print(f"Duration: {summary['duration']:.1f} seconds")
        print(f"Messages: {summary['total_messages']}")
        
    finally:
        session.close()
