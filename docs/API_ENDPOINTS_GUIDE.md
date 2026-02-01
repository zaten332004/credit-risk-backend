# API Endpoints Organization Guide

## Overview
Hệ thống API được chia thành các nhóm chức năng logic để dễ quản lý và sử dụng.

---

## 📋 API Structure

### 1️⃣ **Authentication & Authorization** (`/api/v1/auth`)
Quản lý authentication, login, đăng kí

#### Login
- **POST** `/auth/login`
  - Username/Email + Password → JWT Token
  - Response: Token + User Info + Role
  - Public

#### Registration (User Sign Up)
- **POST** `/auth/register/signup`
  - Register analyst hoặc manager
  - Response: Registration ID + Status
  - Public
  
- **GET** `/auth/register/verify-email?token=...`
  - Verify email with token
  - Response: Verification status
  - Public

#### Registration Management (Admin Only)
- **GET** `/auth/register/pending`
  - Get all pending registrations
  - Query: `?reg_type=manager` (optional)
  - Admin only
  
- **GET** `/auth/register/registration/{registration_id}`
  - Get registration details
  - Admin only
  
- **POST** `/auth/register/approve`
  - Approve/reject manager registration
  - Body: { registration_id, action: "approve"/"reject", rejection_reason? }
  - Admin only

---

### 2️⃣ **Loan Management** (`/api/v1/loan`)
Quản lý các khoản vay, ứng dụng vay, quyết định

- **POST** `/loan/apply`
  - Submit loan application
  - Analyst/Manager
  
- **GET** `/loan/{application_id}`
  - Get loan application details
  - Authenticated users
  
- **POST** `/loan/score/{application_id}`
  - Calculate risk score for application
  - Analyst/Manager
  
- **POST** `/loan/approve/{application_id}`
  - Approve loan
  - Manager
  
- **POST** `/loan/reject/{application_id}`
  - Reject loan
  - Manager
  
- **GET** `/loan/decision/{application_id}`
  - Get approval/rejection decision
  - Analyst/Manager

---

### 3️⃣ **Risk Analysis** (`/api/v1/analyze`)
Phân tích rủi ro chi tiết

#### Risk Scoring
- **POST** `/analyze/risk-score`
  - Calculate risk score for parameters
  - Body: { income, debt_obligation, age, credit_history_months, employment_status }
  - Response: Risk score + Level + Components

#### Facility Analysis
- **GET** `/analyze/facility/{facility_id}`
  - Get detailed facility risk metrics
  - Response: Facility risk data with GROUP classification
  - Analyst/Manager

#### Customer Analysis
- **GET** `/analyze/customer/{customer_id}`
  - Get customer risk profile
  - Response: Customer profile + all facilities + overall risk
  - Analyst/Manager

#### Portfolio Analysis
- **GET** `/analyze/portfolio`
  - Get portfolio summary & GROUP distribution
  - Response: Portfolio metrics + GROUP_1-4 distribution
  - Manager/Admin

#### Dashboard
- **GET** `/analyze/dashboard/summary`
  - Get complete dashboard data
  - Response: All metrics combined for Power BI
  - Manager/Admin

---

### 4️⃣ **Risk Management** (`/api/v1/risk`)
Quản lý rủi ro, mô hình risk, simulation

- **POST** `/risk/score`
  - Calculate risk score (legacy)
  - Analyst
  
- **GET** `/risk/score/{customer_id}`
  - Get customer risk score
  - Analyst
  
- **POST** `/risk/analyze`
  - Analyze customer risk
  - Analyst
  
- **POST** `/risk/batch`
  - Batch risk calculation
  - Analyst
  
- **POST** `/risk/simulation`
  - Run risk simulation
  - Analyst
  
- **GET** `/risk/model/version`
  - Get risk model versions
  - Analyst
  
- **GET** `/risk/explain/{customer_id}`
  - Get risk explanation (SHAP)
  - Analyst

---

### 5️⃣ **Portfolio Management** (`/api/v1/portfolio`)
Phân tích danh mục đầu tư

- **GET** `/portfolio/kpi`
  - Get portfolio KPIs
  - Manager/Admin
  
- **GET** `/portfolio/risk-distribution`
  - Get risk distribution by GROUP
  - Manager/Admin
  
- **GET** `/portfolio/concentration`
  - Get concentration analysis
  - Manager/Admin
  
- **GET** `/portfolio/trend`
  - Get portfolio trend
  - Manager/Admin
  
- **POST** `/portfolio/compare`
  - Compare portfolios
  - Manager/Admin

---

### 6️⃣ **Data Upload & Processing** (`/api/v1/upload`)
Import dữ liệu từ file CSV

- **POST** `/upload/`
  - Upload CSV file
  - Response: Upload ID + rows processed + counts
  - Analyst/Manager
  
- **GET** `/upload/status/{upload_id}`
  - Check upload progress
  - Authenticated users
  
- **GET** `/upload/`
  - Get upload service info
  - Authenticated users

---

### 7️⃣ **System** (`/api/v1/system`)
System health & info

- **GET** `/system/health`
  - Health check
  - Public
  
- **GET** `/system/status`
  - System status
  - Admin

---

## 🔐 Role-Based Access

### Public (No Auth)
- `/auth/login`
- `/auth/register/signup`
- `/auth/register/verify-email`
- `/system/health`

### Analyst
- Login + all read operations
- Loan application
- Risk analysis
- Upload data
- View customer/facility data

### Manager
- Analyst + 
- Approve/reject loans
- Portfolio analysis
- Approve manager registrations
- View KPIs & trends

### Admin
- Manager +
- System management
- User management
- View all registrations

---

## 📊 Common Response Patterns

### Success Response
```json
{
  "data": { ... },
  "message": "Operation successful",
  "timestamp": "2026-01-28T10:30:00Z"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2026-01-28T10:30:00Z"
}
```

### Pagination
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

---

## 🔍 Query Parameters

### Common Filters
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `search`: Search query
- `sort_by`: Sort field
- `sort_order`: asc/desc

### Date Filters
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD

### Status Filters
- `status`: pending/approved/rejected/verified
- `risk_level`: low/medium/high/very_high
- `group`: GROUP_1/GROUP_2/GROUP_3/GROUP_4

---

## 🚀 Usage Examples

### 1. Login
```bash
POST /api/v1/auth/login
{
  "username_or_email": "admin_system",
  "password": "hashed_pwd_123"
}
```

### 2. Register Analyst
```bash
POST /api/v1/auth/register/signup
{
  "username": "newanalyst",
  "email": "analyst@example.com",
  "password": "secure123",
  "full_name": "New Analyst",
  "registration_type": "analyst"
}
```

### 3. Get Portfolio Risk
```bash
GET /api/v1/analyze/portfolio
Headers: Authorization: Bearer <token>
```

### 4. Calculate Risk Score
```bash
POST /api/v1/analyze/risk-score
{
  "income": 50000000,
  "debt_obligation": 10000000,
  "age": 35,
  "credit_history_months": 24,
  "employment_status": "Employed"
}
```

---

## 📝 Best Practices

1. **Always include Authorization header** with Bearer token
2. **Use pagination** for list endpoints (page, limit)
3. **Filter by status** to reduce data
4. **Check role requirements** before calling endpoints
5. **Use query parameters** to narrow down results

---

*Last Updated: 2026-01-28*
