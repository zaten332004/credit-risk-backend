# Credit Risk Backend - Database Setup & API Guide

## Database Setup

### 1. Create Database & Tables

Chạy các SQL scripts theo thứ tự:

```bash
# 1. Create database and tables
SQLQuery1.sql

# 2. Create indexes
SQLQuery2.sql

# 3. Optional: Apply schema improvements
SQLQuery3.sql
```

### 2. Configure Connection String

File: `app/core/config.py` hoặc `app/db/session.py`

```python
SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc://sa:YourPassword@localhost\\SQLEXPRESS/CreditRiskDB"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)
```

**Thay đổi cần thiết:**
- `sa` → Tên user SQL Server của bạn
- `YourPassword` → Password của user
- `localhost\SQLEXPRESS` → Server name (hoặc IP address)
- `CreditRiskDB` → Tên database

### 3. Install Dependencies

```bash
pip install sqlalchemy
pip install pyodbc
pip install "python-dateutil"
```

## Database Schema

### Bảng chính:

| Bảng | Mục đích |
|------|---------|
| User | Người dùng hệ thống |
| Role | Phân quyền (Admin, Manager, Analyst, Viewer) |
| Customer | Thông tin khách hàng |
| Customer_Employment | Lịch sử công việc |
| Loan_Application | Đơn xin vay |
| Loan_Facility | Hạn mức vay phê duyệt |
| Loan_Repayment_Schedule | Lịch trả nợ |
| Loan_Payment | Ghi nhận thanh toán |
| Loan_Delinquency | Nợ xấu, quá hạn |
| RISK_PREDICTION | Dự báo rủi ro |
| Alert | Cảnh báo hệ thống |
| Chat_Session & Chat_History | Lịch sử chat |
| Audit_Log | Nhật ký kiểm toán |

## API Endpoints

### Loan Application & Approval Workflow

#### 1. Create Loan Application

```http
POST /api/v1/loan/apply
Content-Type: application/json
Authorization: Bearer {token}

{
  "customer_id": 1,
  "loan_amount": 50000,
  "loan_term": 24,
  "loan_purpose": "Business expansion"
}
```

**Response:**
```json
{
  "application_id": 1,
  "customer_id": 1,
  "loan_amount": 50000.0,
  "loan_term": 24,
  "loan_status": "pending",
  "created_at": "2026-01-28T10:00:00"
}
```

#### 2. Score Application

```http
POST /api/v1/loan/score/1
Content-Type: application/json
Authorization: Bearer {token}

{
  "income": 10000,
  "debt": 3000,
  "age": 35,
  "credit_history_months": 60
}
```

**Response:**
```json
{
  "pd": 0.3246,
  "lgd": 0.5074,
  "ead": 100000.0,
  "el": 1645.21,
  "risk_score": 0.3246,
  "confidence": 0.8,
  "model_version": "v1"
}
```

#### 3. Get Approval Decision

```http
GET /api/v1/loan/decision/1?risk_threshold=0.66
Authorization: Bearer {token}
```

**Response:**
```json
{
  "application_id": 1,
  "decision": "approved",
  "reason": "Risk score 0.3246 is acceptable",
  "risk_score": 0.3246,
  "risk_level": "low"
}
```

#### 4. Approve Application

```http
POST /api/v1/loan/approve/1
Content-Type: application/json
Authorization: Bearer {token}

{
  "approved_amount": 45000
}
```

**Response:**
```json
{
  "status": "approved",
  "application_id": 1,
  "facility_id": 1
}
```

#### 5. Reject Application

```http
POST /api/v1/loan/reject/1
Content-Type: application/json
Authorization: Bearer {token}

{
  "reason": "High risk score"
}
```

## Loan Approval Workflow

### Quy trình tiêu chuẩn:

```
1. Customer applies for loan
   POST /api/v1/loan/apply

2. System scores the application  
   POST /api/v1/loan/score/{id}

3. Get automated decision
   GET /api/v1/loan/decision/{id}

4. Manager approves or rejects
   POST /api/v1/loan/approve/{id}  OR  POST /api/v1/loan/reject/{id}

5. If approved, loan facility is created (active)
```

### Status Flow:

```
pending → approved → (facility created, status=active)
   ↓
rejected
```

## Risk Scoring

### Scoring Algorithm:

```python
DTI_Factor = min(max(debt/income, 0), 2) / 2
Age_Factor = 1 - (age-18)/(70-18)
History_Factor = 1 - (credit_months/120)

risk_score = 0.6*DTI + 0.2*Age + 0.2*History

Risk Levels:
- Low: risk_score < 0.33
- Medium: 0.33 ≤ risk_score < 0.66
- High: risk_score ≥ 0.66
```

### PD/LGD/EAD Calculation:

```python
PD = clamp(risk_score, 0.01, 0.99)
LGD = 0.4 + 0.3 * risk_score
EAD = 100,000 (fixed for now)
EL = PD * LGD * EAD
```

## Common Issues & Solutions

### 1. Connection Error: "ODBC Driver 18 not found"

**Solution:**
```bash
# Windows: Check installed ODBC drivers
odbcad32.exe

# Or install ODBC Driver
# Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### 2. Authentication Error

**Check:**
- SQL Server is running
- Username and password are correct
- User has permissions on database

### 3. Table Creation Errors

**Check:**
- Database exists and is accessible
- No existing tables with same name
- Run scripts in order: SQLQuery1.sql → SQLQuery2.sql

## Testing

### Test Data: Seed a Customer

```python
from app.db.session import SessionLocal
from app.db.models import CustomerDB
from app.services.customer_repo import CustomerRepository
from app.schemas.schemas import CustomerCreate

db = SessionLocal()

customer = CustomerCreate(
    full_name="John Doe",
    age=35,
    monthly_income=10000,
    credit_score=750,
    employment_status="employed"
)

result = CustomerRepository.create(db, customer)
print(f"Created customer: {result.customer_id}")
```

### Test Loan Application

```python
from app.services.loan_approval_service import LoanApprovalService

# Apply
app = LoanApprovalService.apply_for_loan(
    db=db,
    customer_id=1,
    loan_amount=50000,
    loan_term=24,
    loan_purpose="Business"
)

# Score
scored_app, pred = LoanApprovalService.score_application(
    db=db,
    application_id=app.application_id,
    income=10000,
    debt=3000,
    age=35,
    credit_history_months=60
)

# Decide
decision = LoanApprovalService.make_approval_decision(db, app.application_id)
print(decision)

# Approve
approved_app, facility = LoanApprovalService.approve_application(
    db=db,
    application_id=app.application_id,
    approved_amount=45000
)
```

## Next Steps

### High Priority:
1. ✅ Implement loan approval workflow
2. ⬜ Add payment recording endpoints
3. ⬜ Add delinquency tracking
4. ⬜ Implement alert system

### Medium Priority:
5. ⬜ Replace heuristic with ML model
6. ⬜ Add KYC/AML verification
7. ⬜ Add document upload & verification
8. ⬜ Implement repayment schedule generation

### Low Priority:
9. ⬜ Add portfolio analytics
10. ⬜ Add reporting & export

## Questions?

For issues or questions, check:
- Database logs: SQL Server Management Studio
- Application logs: Console output
- Swagger docs: http://localhost:8000/docs
