# 🏦 Credit Risk Backend - Intelligent Financial Risk Analysis System

A comprehensive financial risk analysis system with AI-powered chatbot, loan management, portfolio analysis, and compliance tracking. Built with FastAPI, MySQL, and Google Gemini AI.

---

## 📋 Quick Overview

### **Core Features**

#### 🤖 **AI Chatbot (Gemini Integration)**
- Real-time financial risk analysis chat
- Vietnamese language support
- Customer credit evaluation
- Portfolio management advisory
- Loan product recommendations
- Regulatory compliance guidance (SBV - State Bank of Vietnam)
- Session-based conversation persistence
- Automatic analysis report generation

#### 💼 **Loan Management System**
- 5 Standardized Loan Products:
  1. **Tín Chấp Cá Nhân** (Unsecured Personal Loan) - 10M-500M VND, 12-24% APY
  2. **Tín Chấp Kinh Doanh** (Business Loan) - 50M-500M VND, 10-18% APY
  3. **Thế Chấp Bất Động Sản** (Real Estate Mortgage) - 100M-5B VND, 6-12% APY
  4. **Thế Chấp Ô Tô** (Vehicle Loan) - 50M-2B VND, 7-13% APY
  5. **Vay Cấu Trúc/Liên Kết** (Structured Finance) - Variable

- Automatic Credit Limit Calculation
- Interest Rate Comparison
- Product Recommendations
- Pricing Rules Management

#### 📊 **Risk Analysis & Portfolio Management**
- Credit risk scoring
- Portfolio risk assessment
- Customer classification
- Alert management
- Regulatory compliance tracking

#### 👥 **User & Role Management**
- Multi-role support: Admin, Manager, Analyst
- Registration workflow with email verification
- User profile management
- Access control

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.9+
- MySQL 8.0+
- Google Gemini API Key
- PowerShell 5.1+ (for Windows)

### **Installation**

1. **Clone Repository**
   ```bash
   git clone https://github.com/zaten332004/credit-risk-backend.git
   cd credit-risk-backend
   ```

2. **Create Virtual Environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   ```powershell
   $env:DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/CreditRiskDB?charset=utf8mb4"
   $env:GEMINI_API_KEY = "your-gemini-api-key"
   $env:SECRET_KEY = "your-jwt-secret-key"
   ```

5. **Initialize Database**
   ```bash
   python app/db/init_db.py
   ```

   If you are upgrading an existing database, run incremental migrations before starting API:
   ```bash
   # Add account PIN columns to User table
   mysql -u <user> -p <database_name> < scripts/migrations/20260411_add_user_pin_columns.up.sql
   ```

6. **Run Development Server**
   ```powershell
   .\run_dev.ps1
   # Or manually:
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access API**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

## 📚 API Endpoints

### **Authentication** (`/api/v1/auth`)
- `POST /auth/login` - User login
- `POST /auth/register/signup` - User registration
- `GET /auth/register/verify-email` - Email verification

### **AI Chatbot** (`/api/v1/ai-chat`)
- `POST /ai-chat/start` - Start new chat session
- `POST /ai-chat/send` - Send message & get AI response
- `GET /ai-chat/history/{session_id}` - Get conversation history
- `POST /ai-chat/close/{session_id}` - Close session with summary
- `POST /ai-chat/sessions/{session_id}/close` - Close session (alias)
- `GET /ai-chat/sessions` - List user's chat sessions
- `DELETE /ai-chat/sessions/{session_id}` - Delete a chat session (and its messages)
- `POST /ai-chat/sessions/{session_id}/pin` - Pin a session
- `POST /ai-chat/sessions/{session_id}/unpin` - Unpin a session
- `GET /ai-chat/models` - List selectable AI models (if supported by provider)
- `GET /ai-chat/debug` - Debug provider/model/config
- `GET /ai-chat/context-preview` - Preview analysis context (db/powerbi)
- `GET /ai-chat/report/{session_id}` - Generate analysis report

> Note (MySQL): import `docs/database/Database_MySQL_V1.sql` for the canonical schema and seed data.

> Note (Legacy SQL Server helpers): `scripts/sqlserver_*.sql` are retained only for reference.

### **Loan Management** (`/api/v1/loan`)
- `POST /loan/apply` - Apply for loan
- `GET /loan/{loan_id}` - Get loan details
- `GET /loan/list` - List user's loans
- `POST /loan/{loan_id}/approve` - Approve loan (admin)
- `POST /loan/{loan_id}/reject` - Reject loan (admin)

### **Customer Management** (`/api/v1/customer`)
- `POST /customer/` - Create customer
- `GET /customer/{customer_id}` - Get customer details
- `PUT /customer/{customer_id}` - Update customer

### **Portfolio Analysis** (`/api/v1/portfolio`)
- `GET /portfolio/` - Get portfolio analysis
- `GET /portfolio/risk-assessment` - Get risk assessment
- `GET /portfolio/metrics` - Get portfolio metrics

### **System** (`/api/v1/system`)
- `GET /health` - Health check
- `GET /config` - System configuration

---

## 🗄️ Database Schema

### **Key Tables**

**Users** - User accounts with roles (admin, manager, analyst)

**Customers** - Customer profiles with credit information

**Loan_Products** - Loan product definitions (5 types)

**Loans** - Loan applications and details

**Chat_Session** - AI chatbot conversation sessions

**Chat_History** - Individual chat messages

**Risk_Analysis** - Risk assessment records

**Portfolio** - Portfolio aggregations

**Alerts** - Risk alerts and notifications

Full database schema available in: `docs/sql-scripts/Database_full_V1.sql`

---

## 🤖 Gemini AI Chatbot

### **Setup**

1. **Get API Key**
   - Visit: https://aistudio.google.com/app/apikeys
   - Create new API key
   - Copy to environment variable: `GEMINI_API_KEY`

2. **Install SDK**
   ```bash
   pip install google-generativeai
   ```

3. **Configuration**
   - Model: `gemini-2.0-flash` (latest)
   - Language: Vietnamese (financial domain expertise)
   - Temperature: 0.7 (balanced responses)
   - Max Tokens: 2048

### **System Prompt Features**
- Vietnamese financial risk expert
- Credit risk analysis
- Customer evaluation
- Portfolio management
- Loan product advisory
- SBV regulatory compliance
- Best practices recommendations

### **Example Usage**

```python
# Start chat session
POST /api/v1/ai-chat/start
{
  "session_name": "Risk Analysis - Customer XYZ"
}

# Send message
POST /api/v1/ai-chat/send
{
  "session_id": "abc123",
  "message": "Khách hàng này có rủi ro gì?"
}

# Get analysis report
GET /api/v1/ai-chat/report/abc123
```

---

## 💼 Loan Products

### **Product Details**

| Loại Vay | Hạn Mức | Thời Hạn | Lãi Suất | LTV |
|---------|---------|---------|---------|-----|
| Tín Chấp Cá Nhân | 10M-500M | 1-7 năm | 12-24% | N/A |
| Tín Chấp Kinh Doanh | 50M-500M | 6-7 năm | 10-18% | N/A |
| Thế Chấp BĐS | 100M-5B | 5-35 năm | 6-12% | 85% |
| Thế Chấp Ô Tô | 50M-2B | 1-7 năm | 7-13% | 80% |
| Vay Cấu Trúc | Flexible | Flexible | Variable | Variable |

### **Credit Evaluation Criteria**
- Credit Score (300-900)
- Income Level & Stability
- Debt-to-Income Ratio (DTI)
- Employment Status
- Collateral Value (if secured)
- Industry Risk (for business)

---

## 📁 Project Structure

```
credit-risk-backend/
├── app/
│   ├── api/
│   │   ├── routers/          # API route handlers
│   │   │   ├── admin.py
│   │   │   ├── ai_chat.py    # AI chatbot endpoints
│   │   │   ├── auth.py
│   │   │   ├── loan.py
│   │   │   ├── customer.py
│   │   │   └── ...
│   │   └── endpoints.py
│   ├── core/
│   │   ├── config.py         # Configuration
│   │   └── security.py       # Auth & security
│   ├── db/
│   │   ├── models.py         # Database models
│   │   ├── session.py        # DB session
│   │   └── init_db.py        # DB initialization
│   ├── services/
│   │   ├── gemini_ai_chat_service.py    # AI service
│   │   ├── loan_product_service.py
│   │   ├── customer_service.py
│   │   ├── risk_analysis_service.py
│   │   └── ...
│   ├── schemas/              # Pydantic request/response models
│   └── main.py               # FastAPI app
├── docs/
│   ├── guides/               # Implementation guides
│   ├── api/                  # API documentation
│   ├── database/             # Database architecture
│   └── sql-scripts/          # SQL migration scripts
│       └── Database_full_V1.sql
├── scripts/                  # Utility scripts
├── data/                     # Sample data files
└── requirements.txt
```

---

## 🔧 Environment Configuration

### **Required Variables**

```env
# Database
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/CreditRiskDB?charset=utf8mb4

# API
API_V1_PREFIX=/api/v1
SECRET_KEY=your-super-secret-key

# Gemini AI
GEMINI_API_KEY=your-google-gemini-api-key
# Optional: default Gemini model (backend can also be overridden per message via /ai-chat/models + model param)
GEMINI_MODEL=gemini-2.5-flash-lite
# AI chat provider (optional): gemini|openai|langflow|mock
AI_CHAT_PROVIDER=gemini
# If set to 1/true, fallback to mock responses on provider errors (default: 0/false)
AI_CHAT_FALLBACK_TO_MOCK=0
# Optional: allowlist/tier mapping for UI model picker (defaults shown below)
AI_CHAT_GEMINI_MODEL_FAST=gemini-2.5-flash-lite
AI_CHAT_GEMINI_MODEL_THINKING=gemini-2.5-flash
AI_CHAT_GEMINI_MODEL_PRO=gemini-2.5-pro
# AI analytics context source (optional): db|powerbi (default: db)
AI_CHAT_CONTEXT_SOURCE=db

# Power BI (optional, for AI_CHAT_CONTEXT_SOURCE=powerbi)
POWER_BI_TENANT_ID=your-tenant-id
POWER_BI_CLIENT_ID=your-service-principal-client-id
POWER_BI_CLIENT_SECRET=your-service-principal-client-secret
POWER_BI_WORKSPACE_ID=your-workspace-id
POWER_BI_DATASET_ID=your-dataset-id
# Approach A (recommended): query a fixed "contract" table inside the dataset
POWER_BI_AI_CONTEXT_TABLE=AI_Context
POWER_BI_AI_CONTEXT_MAX_ROWS=200
# Optional: limit formatted context length
POWER_BI_AI_CONTEXT_MAX_CHARS=4000
# Optional: warn if these keys are missing (comma-separated)
POWER_BI_AI_CONTEXT_REQUIRED_KEYS=DatasetName,DateRange
# Optional: custom DAX query for AI context (overrides contract table)
POWER_BI_AI_CONTEXT_DAX=
# Optional (debug only): allow calling /ai-chat/powerbi-query without admin role
AI_CHAT_POWERBI_QUERY_ALLOW_ANY=0

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Frontend (CORS) - optional, comma-separated
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## Power BI AI Context (Approach A)

If you want AI chat to use only Power BI dataset data (and not read analytics from the SQL DB), set:
- `AI_CHAT_CONTEXT_SOURCE=powerbi`

Then, inside the Power BI dataset, create a **calculated table** named `AI_Context` (or set `POWER_BI_AI_CONTEXT_TABLE`).
The backend will query this table to build prompt context, so each dataset can have different internal tables without changing backend code.

Recommended columns:
- `Key` (text, required)
- `TextValue` (text, optional)
- `NumberValue` (numeric, optional)
- `UpdatedAt` (datetime/text, optional)

Example calculated table (Power BI Desktop → Modeling → New table):

```DAX
AI_Context =
UNION (
    ROW ( "Key", "DatasetName", "TextValue", "Finance Model", "NumberValue", BLANK (), "UpdatedAt", NOW () ),
    ROW ( "Key", "TotalSales", "TextValue", BLANK (), "NumberValue", SUM ( FactInternetSales[SalesAmount] ), "UpdatedAt", NOW () ),
    ROW ( "Key", "TotalFinanceAmount", "TextValue", BLANK (), "NumberValue", SUM ( FactFinance[Amount] ), "UpdatedAt", NOW () )
)
```

Notes:
- Pick measures/columns that exist in your dataset.
- The backend only reads from Power BI in this mode; it still stores chat history in the app database.

## 🧪 Testing

### **Run Tests**
```bash
pytest tests/
```

### **Test Coverage**
```bash
pytest --cov=app tests/
```

### **Manual Testing**
```powershell
# Test registration
python test_reg.ps1

# Health check
curl http://localhost:8000/health
```

---

## 📊 Key Metrics & Features

### **AI Chatbot Capabilities**
- ✅ Multi-turn conversations (up to 50 messages per session)
- ✅ Context-aware responses using customer data
- ✅ Session persistence in database
- ✅ Automatic session timeout
- ✅ Analysis report generation
- ✅ Vietnamese language support

### **Loan Management**
- ✅ 5 loan products with automated pricing
- ✅ Credit limit calculation algorithm
- ✅ Loan application workflow
- ✅ Multi-stage approval process
- ✅ Interest rate comparison

### **Security & Compliance**
- ✅ OAuth2 with JWT authentication
- ✅ Role-based access control (RBAC)
- ✅ Email verification workflow
- ✅ Secure password hashing (bcrypt)
- ✅ SBV regulatory compliance
- ✅ Audit logging

---

## 🚢 Deployment

### **Development**
```powershell
.\run_dev.ps1
```

### **Production**
```bash
# Using Gunicorn
gunicorn app.main:app -w 4 -b 0.0.0.0:8000

# Using Docker
docker build -t credit-risk-backend .
docker run -p 8000:8000 credit-risk-backend
```

---

## 📞 Support & Documentation

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Detailed Guides**: `docs/guides/`
- **Database Schema**: `docs/sql-scripts/Database_full_V1.sql`
- **API Reference**: `docs/api/API_ENDPOINTS_GUIDE.md`

---

## 📝 License

This project is proprietary and confidential.

---

## 👥 Authors

- **Dev Team**: Zaten332004
- **Project**: Credit Risk Backend
- **Status**: Active Development (Phase 1: AI Chatbot ✅, Phase 2-5: Planned)

---

## 🎯 Roadmap

- [x] Phase 1: Gemini AI Chatbot Integration
- [x] Phase 1: Loan Products Management
- [ ] Phase 2: Mobile App Integration (Flutter)
- [ ] Phase 3: PowerBI Dashboard Integration
- [ ] Phase 4: Langflow Workflow Automation
- [ ] Phase 5: AWS Cloud Deployment

---

## 📞 Contact

For inquiries or support, contact the development team.
