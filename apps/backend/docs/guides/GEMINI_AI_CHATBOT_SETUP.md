# 🤖 Gemini AI Chatbot Setup Guide

## 📋 Tổng Quan

Chatbot AI tích hợp **Google Gemini AI** để phân tích rủi ro tài chính với khả năng:
- 💬 Chat real-time với AI
- 📊 Phân tích rủi ro tín dụng
- 👤 Đánh giá khách hàng
- 💼 Quản lý portfolio
- 📈 Tư vấn sản phẩm vay
- 📋 Sinh báo cáo tự động

---

## 🚀 Setup

### 1. Cài Đặt Dependencies

```bash
pip install google-generativeai
```

Hoặc cập nhật `requirements.txt`:
```
google-generativeai==0.3.0
```

Sau đó:
```bash
pip install -r requirements.txt
```

### 2. Lấy Gemini API Key

1. **Truy cập Google AI Studio**
   - Vào https://aistudio.google.com/app/apikeys
   - Đăng nhập với Google account

2. **Tạo API Key**
   - Click "Create API Key"
   - Copy API key

3. **Lưu Environment Variable**

   **Windows (PowerShell):**
   ```powershell
   $env:GEMINI_API_KEY = "your-api-key-here"
   ```

   **Windows (CMD):**
   ```cmd
   set GEMINI_API_KEY=your-api-key-here
   ```

   **Linux/Mac:**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

   **Hoặc thêm vào `.env` file:**
   ```
   GEMINI_API_KEY=your-api-key-here
   ```

### 3. Tạo Database Tables

```bash
# Database tables sẽ được tạo tự động khi chạy ứng dụng
# Hoặc chạy migration:
python -c "from app.db.models import ChatSessionDB, ChatHistoryDB; from app.db.session import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 4. Chạy Backend

```bash
python -m uvicorn app.main:app --reload
```

---

## 📡 API Endpoints

### Base URL
```
/api/v1/ai-chat
```

### 1. Bắt Đầu Chat Session
```http
POST /api/v1/ai-chat/start
Content-Type: application/json

{
  "session_name": "Phân tích rủi ro - Khách hàng ABC",
  "initial_context": "Customer: ABC Corp, Credit Score: 750, Income: 5B VND/year"
}
```

**Response (200):**
```json
{
  "session_id": 1,
  "greeting_message": "Xin chào! Tôi là trợ lý tài chính AI...",
  "created_at": "2026-02-01T10:30:00"
}
```

---

### 2. Gửi Tin Nhắn
```http
POST /api/v1/ai-chat/send
Content-Type: application/json

{
  "session_id": 1,
  "message": "Phân tích rủi ro tín dụng cho khách hàng này",
  "customer_context": {
    "customer_id": 1,
    "full_name": "ABC Company",
    "credit_score": 750,
    "annual_income": 5000000000,
    "outstanding_balance": 1500000000,
    "risk_group": "Group 1"
  }
}
```

**Response (200):**
```json
{
  "session_id": 1,
  "message": "Dựa trên thông tin khách hàng, đây là phân tích rủi ro tín dụng...",
  "role": "assistant",
  "timestamp": "2026-02-01T10:31:00"
}
```

---

### 3. Lấy Lịch Sử Chat
```http
GET /api/v1/ai-chat/history/1?limit=50
```

**Response (200):**
```json
[
  {
    "role": "assistant",
    "content": "Xin chào! Tôi là trợ lý tài chính AI...",
    "timestamp": "2026-02-01T10:30:00"
  },
  {
    "role": "user",
    "content": "Phân tích rủi ro tín dụng...",
    "timestamp": "2026-02-01T10:31:00"
  }
]
```

---

### 4. Lấy Danh Sách Sessions
```http
GET /api/v1/ai-chat/sessions
```

**Response (200):**
```json
[
  {
    "session_id": 1,
    "session_name": "Phân tích rủi ro - ABC",
    "is_active": true,
    "created_at": "2026-02-01T10:30:00",
    "closed_at": null
  }
]
```

---

### 5. Đóng Chat Session
```http
POST /api/v1/ai-chat/close/1
```

**Response (200):**
```json
{
  "session_id": 1,
  "session_name": "Phân tích rủi ko - ABC",
  "duration": 300.5,
  "user_messages": 3,
  "assistant_messages": 3,
  "total_messages": 6,
  "closed_at": "2026-02-01T10:35:00"
}
```

---

### 6. Sinh Báo Cáo Phân Tích
```http
GET /api/v1/ai-chat/report/1
```

**Response (200):**
```json
{
  "session_id": 1,
  "report": "BÁOÁO PHÂN TÍCH RỦI RO TÀI CHÍNH...",
  "generated_at": "2026-02-01T10:36:00"
}
```

---

## 💡 Ví Dụ Sử Dụng

### Scenario: Phân tích rủi ro khách hàng

```bash
# 1. Bắt đầu session
curl -X POST http://localhost:8000/api/v1/ai-chat/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Phân tích ABC Corp",
    "initial_context": "Customer: ABC Corp, Score: 750, Income: 5B/year"
  }'

# Response: session_id = 1

# 2. Gửi tin nhắn hỏi
curl -X POST http://localhost:8000/api/v1/ai-chat/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "message": "Khách hàng này có nên vay 500 triệu không?",
    "customer_context": {
      "credit_score": 750,
      "annual_income": 5000000000
    }
  }'

# 3. Lấy lịch sử
curl http://localhost:8000/api/v1/ai-chat/history/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Sinh báo cáo
curl http://localhost:8000/api/v1/ai-chat/report/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Đóng session
curl -X POST http://localhost:8000/api/v1/ai-chat/close/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🎯 Chuyên Gia AI Có Thể Giúp

### 1. Phân Tích Rủi Ro Tín Dụng
```
User: Phân tích rủi ro khách hàng ABC có điểm tín dụng 680?

AI: Dựa trên điểm tín dụng 680:
- Phân loại: Nhóm 2 (Nợ cần chú ý)
- Tỷ lệ PD (mặc định): 5-8%
- Khuyến nghị DTI tối đa: 45%
- Lãi suất: +2% từ lãi suất cơ bản
```

### 2. Đánh Giá Hạn Mức Vay
```
User: Hạn mức vay tối đa cho khách hàng có lương 40M/tháng?

AI: Cho khách hàng loại tín chấp:
- Hạn mức tối đa: min(500M, 40M × 15) = 500M
- Hạn mức khuyến nghị: 300-400M (dựa DTI)
- Điều kiện: DTI không vượt 50%
```

### 3. Tư Vấn Sản Phẩm
```
User: Loại vay nào phù hợp nhất cho khách hàng này?

AI: Khuyến nghị:
1. Vay thế chấp BĐS (6-8% lãi, nếu có sổ đỏ)
2. Vay tín chấp (12-18%, không cần đảm bảo)
Lý do: DTI và tài chính ổn định
```

### 4. Quản Lý Portfolio
```
User: NPL ratio của portfolio là bao nhiêu?

AI: Dựa trên dữ liệu:
- NPL Ratio: 2.5%
- Provision cần thiết: 150 tỷ VND
- Cảnh báo: Concentration risk cao
```

### 5. Thông Báo Quy Định
```
User: Điều kiện vay theo SBV là gì?

AI: Theo Circular 11/2021/TT-NHNN:
- 5 nhóm phân loại dựa ngày quá hạn
- Provision rate: 0% - 100%
- Yêu cầu báo cáo: Hàng tháng
```

---

## 📚 Database Schema

### Chat_Session
```
- session_id (PK)
- user_id (FK)
- session_name: Tên phiên chat
- initial_context: Thông tin ban đầu
- is_active: Trạng thái
- created_at, closed_at
```

### Chat_History
```
- message_id (PK)
- session_id (FK)
- user_id (FK)
- role: 'user' | 'assistant'
- content: Nội dung tin nhắn
- created_at
```

---

## 🔒 Security & Best Practices

### 1. API Key Management
✅ Sử dụng environment variables  
✅ Không commit API key vào git  
✅ Rotate API key thường xuyên  

### 2. Authentication
✅ Tất cả endpoints yêu cầu authentication  
✅ Sử dụng JWT tokens  
✅ Kiểm tra user_id match với session_id  

### 3. Rate Limiting
```python
# Recommend: 100 messages/giờ/user
# 10 sessions/giờ/user
```

### 4. Cost Management
- Gemini API miễn phí cho request < 1500/ngày
- Recommend: Implement caching cho queries tương tự
- Monitor usage qua Google Cloud Console

---

## 🧪 Testing

### Test với Python
```python
from app.services.gemini_ai_chat_service import GeminiAIChatService
from app.db.session import SessionLocal

# Initialize
service = GeminiAIChatService()
session = SessionLocal()

# Start session
session_id, greeting = service.start_chat_session(
    session=session,
    user_id=1,
    session_name="Test Session",
    initial_context="Customer: Test, Score: 750"
)

# Send message
response = service.send_message(
    session=session,
    session_id=session_id,
    user_id=1,
    message="Phân tích rủi ro cho tôi"
)

print(response.message)
```

### Test với cURL
```bash
# Lấy token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# Start session
curl -X POST http://localhost:8000/api/v1/ai-chat/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Test",
    "initial_context": "Test customer"
  }' | jq .
```

---

## 📊 Monitoring & Analytics

### Metrics to Track
- **Messages per session**: Average 5-10 messages
- **Response time**: < 3 seconds per message
- **Session duration**: 5-30 minutes
- **User satisfaction**: Collect feedback

### Logs
```python
# Service logs all conversations
# Location: Chat_History table
# Query: SELECT * FROM Chat_History WHERE user_id = X
```

---

## ⚙️ Configuration

### Model Settings
```python
GEMINI_MODEL = "gemini-2.0-flash"
TEMPERATURE = 0.7  # Creativity level
TOP_P = 0.95       # Diversity
MAX_TOKENS = 2048  # Response length
```

### Safety Settings
```python
BLOCK_NONE = True  # Allow all content
# (For financial analysis, safe to allow all)
```

---

## 🔧 Troubleshooting

### Lỗi: "GEMINI_API_KEY not found"
**Solution:**
```bash
# Set environment variable
export GEMINI_API_KEY="your-key"

# Or add to .env file
echo "GEMINI_API_KEY=your-key" >> .env
```

### Lỗi: "Connection timeout"
**Solution:**
- Check internet connection
- Verify API key is valid
- Check Google API quota

### Lỗi: "Session not found"
**Solution:**
- Verify session_id is correct
- Check session hasn't expired
- User must own the session

---

## 📖 Tài Liệu

- **Google Gemini API Docs**: https://ai.google.dev/tutorials/python_quickstart
- **API Reference**: https://ai.google.dev/api
- **Pricing**: https://ai.google.dev/pricing

---

## 🚀 Roadmap

- [ ] Multi-language support (English, Vietnamese, Chinese)
- [ ] Voice input/output
- [ ] Real-time collaboration (multiple users per session)
- [ ] Custom fine-tuning for bank-specific terms
- [ ] Integration with PowerBI for visualization
- [ ] Flutter mobile app integration
- [ ] AWS Bedrock alternative (multi-model support)
- [ ] Langflow integration for visual workflow

---

## 💬 Support

- **Issues**: Create GitHub issue
- **Questions**: Contact development team
- **Feedback**: Email: support@creditrisk.vn

---

**Version**: 1.0  
**Last Updated**: February 1, 2026  
**Status**: ✅ Ready for Production
