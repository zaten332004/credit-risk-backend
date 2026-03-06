# Credit Risk Backend - API Summary

## 🎯 Quick Start

### 1. Start Server
```bash
cd d:\GitHub\credit-risk-backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Server chạy tại: `http://localhost:8000`

### 2. Access API Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Guide**: See `docs/API_ENDPOINTS_GUIDE.md`

---

## 📚 API Endpoints Overview

| Group | Prefix | Purpose |
|-------|--------|---------|
| **Auth** | `/api/v1/auth` | Login, Register, Email Verification |
| **Loan** | `/api/v1/loan` | Loan Applications, Approvals |
| **Risk Analysis** | `/api/v1/analyze` | Risk Scores, Portfolio Analysis |
| **Risk Mgmt** | `/api/v1/risk` | Risk Modeling, Simulation |
| **Portfolio** | `/api/v1/portfolio` | Portfolio KPIs, Distribution |
| **Upload** | `/api/v1/upload` | CSV File Import |
| **System** | `/api/v1/system` | Health Check |

---

## 🔐 Authentication

### Login
```bash
POST /api/v1/auth/login
{
  "username_or_email": "admin_system",
  "password": "hashed_pwd_123"
}
```

**Demo Credentials:**
| Username | Password | Role |
|----------|----------|------|
| admin_system | hashed_pwd_123 | Admin |
| manager_portfolio | manager123 | Manager |
| analyst_risk | analyst123 | Analyst |

### JWT Token
- Returned from login endpoint
- Include in all requests: `Authorization: Bearer <token>`
- Expires: 60 minutes

---

## 👤 User Registration

### Type 1: Analyst (Auto-Approved)
```bash
POST /api/v1/auth/register/signup
{
  "username": "newanalyst",
  "email": "analyst@example.com",
  "password": "password123",
  "full_name": "John Analyst",
  "registration_type": "analyst"
}
```
→ Email verification → Auto-approved → User created

### Type 2: Manager (Admin Approval)
```bash
POST /api/v1/auth/register/signup
{
  "username": "newmanager",
  "email": "manager@example.com",
  "password": "password123",
  "full_name": "Jane Manager",
  "registration_type": "manager"
}
```
→ Email verification → Pending admin approval → User created

### Admin Approval
```bash
POST /api/v1/auth/register/approve
{
  "registration_id": 1,
  "action": "approve"
}
```

---

## 📊 Key Features

### 1. Risk Scoring
- DTI (60%) + Age (20%) + History (20%)
- Risk levels: low, medium, high
- Customer risk profiles

### 2. Portfolio Analysis
- GROUP classification (GROUP_1-4 based on DPD)
- Risk distribution
- Concentration analysis
- KPI metrics

### 3. Loan Management
- Application submission
- Risk-based scoring
- Manager approval workflow

### 4. Data Import
- CSV file upload
- Batch processing
- Automatic risk calculation

---

## 📁 Project Structure

```
app/
├── api/
│   ├── endpoints.py          # Main endpoints
│   └── routers/              # Grouped routers
│       ├── auth.py           # Auth endpoints
│       ├── loan.py           # Loan endpoints
│       ├── risk.py           # Risk endpoints
│       ├── portfolio.py       # Portfolio endpoints
│       ├── analysis.py        # Risk analysis
│       ├── upload.py          # File upload
│       ├── registration.py    # User registration
│       └── ...
├── services/                 # Business logic
│   ├── registration_service.py
│   ├── risk_analysis_service.py
│   ├── upload_service.py
│   └── ...
├── db/
│   ├── models.py             # ORM models
│   ├── session.py            # DB connection
│   └── init_db.py
├── schemas/                  # Pydantic models
├── core/
│   ├── security.py           # JWT, password hashing
│   └── config.py             # Settings
└── main.py                   # FastAPI app

docs/
├── API_ENDPOINTS_GUIDE.md    # API documentation
├── ETL_IMPORT_PIPELINE.sql   # SQL import script
└── UPLOAD_AND_ANALYSIS_GUIDE.md
```

---

## 🗄️ Database

**Server**: `DESKTOP-7EPLMS3\SQLEXPRESS`
**Database**: `CreditRiskDB`
**User**: `sa` / Password: `12345`

### Main Tables
- **User** - User accounts
- **User_Registration** - Registration requests
- **Customer** - Customer info
- **Loan_Application** - Loan applications
- **Loan_Facility** - Loan facilities/credit lines
- **Loan_Delinquency** - Delinquency tracking
- **Role** - User roles
- ... (and more)

---

## 🚀 Workflow Examples

### Workflow 1: Analyst Login & Analysis
1. Analyst login: `POST /auth/login`
2. Get customer data: `GET /analyze/customer/{customer_id}`
3. Calculate risk: `POST /analyze/risk-score`
4. View facility: `GET /analyze/facility/{facility_id}`

### Workflow 2: Manager Approves Loan
1. Manager login
2. Get pending applications: `GET /loan` (filtered)
3. Score application: `POST /loan/score/{application_id}`
4. Approve loan: `POST /loan/approve/{application_id}`

### Workflow 3: Admin Approves Manager Registration
1. Admin login
2. View pending: `GET /auth/register/pending`
3. Approve: `POST /auth/register/approve`

### Workflow 4: New User Registration
1. User signup: `POST /auth/register/signup`
2. User verifies email: Click link with token
3. Auto-approved (analyst) or pending (manager)
4. Can login after approval

---

## 📈 API Statistics

| Metric | Value |
|--------|-------|
| Total Endpoints | 30+ |
| Authentication Methods | JWT Bearer |
| Request Format | JSON |
| Response Format | JSON |
| Rate Limit | Not implemented |
| Pagination Support | Yes (page, limit) |

---

## 🔧 Common Tasks

### Task 1: Get Risk Analysis Dashboard
```bash
GET /api/v1/analyze/dashboard/summary
```
Returns all metrics for Power BI dashboard

### Task 2: Upload Data for Analysis
```bash
POST /api/v1/upload/
(multipart/form-data with CSV file)
```

### Task 3: Approve New Manager Registration
```bash
POST /api/v1/auth/register/approve
{
  "registration_id": 1,
  "action": "approve"
}
```

### Task 4: Get Portfolio KPIs
```bash
GET /api/v1/portfolio/kpi
```

---

## 📞 Support

**API Documentation**: See `docs/API_ENDPOINTS_GUIDE.md`

**Database Issues**: Check connection to SQL Server

**Authentication Issues**: Ensure JWT token is valid and not expired

---

*Generated: 2026-01-28*
*Version: 1.0.0*
