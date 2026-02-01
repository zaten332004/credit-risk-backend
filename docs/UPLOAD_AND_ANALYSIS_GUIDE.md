# Upload & Analysis Pipeline Guide

## Overview

Hệ thống gồm 3 thành phần chính:

1. **ETL Import Pipeline** - Import CSV files vào database
2. **Upload API** - File upload endpoint với validation
3. **Risk Analysis Service** - Phân tích rủi ro và tính toán metrics

---

## 1️⃣ ETL Import Pipeline

### Mục đích
Import 7 file CSV (Adventure Works dataset) vào database, map thành Credit Risk model.

### Files được import
| File | Nội dung | Rows |
|------|---------|------|
| Data_1.csv | Sales Orders | 27,661 |
| Data_2.csv | Chart of Accounts | 100 |
| Data_3.csv | Currencies | 100 |
| Data_4.csv | Date Dimension | 3,654 |
| Data_5.csv | Scenarios | 3 |
| Data_6.csv | Exchange Rates | 14,266 |
| Data_8.csv | Finance Facts | 2,468 |

### Cách chạy

```bash
# Chạy ETL script SQL
sqlcmd -S DESKTOP-7EPLMS3\SQLEXPRESS -U sa -P 12345 -d CreditRiskDB \
  -i "D:\GitHub\credit-risk-backend\docs\ETL_IMPORT_PIPELINE.sql"
```

### Kết quả
- ✅ 7 staging tables được tạo
- ✅ CSV files được import vào staging
- ✅ Data được transform thành Credit Risk model:
  - Customers: Created từ CustomerKey
  - Loan Applications: Created từ SalesAmount
  - Loan Facilities: Created từ SalesOrder details

### Staging Tables (tạm thời)
```sql
-- Sau import, có thể xoá staging tables
DROP TABLE dbo.stg_SalesOrder;
DROP TABLE dbo.stg_Account;
DROP TABLE dbo.stg_Currency;
DROP TABLE dbo.stg_Date;
DROP TABLE dbo.stg_Scenario;
DROP TABLE dbo.stg_ExchangeRate;
DROP TABLE dbo.stg_FinanceFact;
```

---

## 2️⃣ Upload API

### Endpoints

#### POST /api/v1/upload
Upload và process CSV file

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.csv" \
  -F "limit_rows=1000"
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully uploaded and processed 1000 records",
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "sales_data.csv",
  "rows_processed": 1000,
  "customers_created": 150,
  "applications_created": 1000,
  "facilities_created": 1000,
  "processing_time_seconds": 12.5,
  "errors": []
}
```

#### GET /api/v1/upload/status/{upload_id}
Kiểm tra trạng thái upload

**Request:**
```bash
curl "http://localhost:8000/api/v1/upload/status/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Successfully uploaded and processed 1000 records",
  "progress_percent": 100,
  "file_name": "sales_data.csv",
  "created_at": "2026-01-28T10:30:00",
  "completed_at": "2026-01-28T10:30:15"
}
```

#### GET /api/v1/upload
Lấy thông tin service

**Request:**
```bash
curl "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "service": "File Upload & ETL Processing",
  "supported_formats": [".csv", ".xlsx", ".xls"],
  "max_file_size_mb": 50,
  "max_rows_per_file": null,
  "endpoints": [...],
  "recent_uploads": 5,
  "active_uploads": 0
}
```

### File Requirements
- **Format**: CSV, XLSX, XLS
- **Size limit**: 50 MB
- **Encoding**: UTF-8
- **Header row**: Required (first row)

### Column Mapping
Upload Service tự động detect columns:

```
upload file columns → credit risk model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CustomerKey → customer_id
SalesAmount → loan_amount / income
OrderQuantity → loan_term
UnitPrice → interest_rate
OrderDateKey → order_date
```

---

## 3️⃣ Risk Analysis Service

### Endpoints

#### POST /api/v1/analyze/risk-score
Tính risk score

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/risk-score" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "income": 50000000,
    "debt_obligation": 10000000,
    "age": 35,
    "credit_history_months": 24,
    "employment_status": "Employed"
  }'
```

**Response:**
```json
{
  "risk_score": 0.28,
  "risk_level": "low",
  "dti_ratio": 20.0,
  "components": {
    "dti": {"weight": 0.6, "score": 0.4},
    "age": {"weight": 0.2, "score": 0.2},
    "history": {"weight": 0.2, "score": 0.3}
  },
  "timestamp": "2026-01-28T10:30:00"
}
```

#### GET /api/v1/analyze/facility/{facility_id}
Lấy risk metrics cho facility

**Request:**
```bash
curl "http://localhost:8000/api/v1/analyze/facility/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "facility_id": 1,
  "customer_id": 1,
  "facility_type": "Term Loan",
  "approved_amount": 500000000,
  "interest_rate": 8.5,
  "status": "active",
  "days_past_due": 0,
  "risk_group": "GROUP_1",
  "risk_group_name": "NORMAL",
  "on_time_payment_rate": 100.0,
  "overdue_amount": 0
}
```

#### GET /api/v1/analyze/portfolio
Lấy portfolio summary

**Request:**
```bash
curl "http://localhost:8000/api/v1/analyze/portfolio" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "portfolio_summary": {
    "total_facilities": 9,
    "total_amount": 2325000000,
    "average_dpd": 15.5,
    "average_on_time_rate": 85.0
  },
  "group_distribution": {
    "GROUP_1": {"name": "NORMAL", "count": 3, "percentage": 33.3},
    "GROUP_2": {"name": "SPECIAL MENTION", "count": 2, "percentage": 22.2},
    "GROUP_3": {"name": "SUBSTANDARD", "count": 2, "percentage": 22.2},
    "GROUP_4": {"name": "DOUBTFUL", "count": 2, "percentage": 22.2}
  },
  "risk_trend": {...},
  "timestamp": "2026-01-28T10:30:00"
}
```

#### GET /api/v1/analyze/customer/{customer_id}
Lấy customer risk profile

**Request:**
```bash
curl "http://localhost:8000/api/v1/analyze/customer/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "customer_id": 1,
  "name": "Customer_1",
  "age": 35,
  "monthly_income": 5833333.33,
  "credit_score": 750,
  "employment_status": "Employed",
  "total_exposure": 750000000,
  "num_facilities": 3,
  "worst_risk_group": "GROUP_1",
  "overall_risk_score": 0.28,
  "overall_risk_level": "low",
  "facilities": [...]
}
```

#### GET /api/v1/analyze/dashboard/summary
Lấy dashboard summary

**Request:**
```bash
curl "http://localhost:8000/api/v1/analyze/dashboard/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔧 Risk Scoring Formula

```
Risk Score = (DTI × 60%) + (Age × 20%) + (History × 20%)

Where:
  DTI Score = Debt-to-Income analysis
    dti > 60% → 1.0 (very high)
    dti > 40% → 0.7 (high)
    dti > 20% → 0.4 (medium)
    dti ≤ 20% → 0.1 (low)
  
  Age Score = Age-based risk
    age < 25   → 0.6 (higher risk)
    age < 35   → 0.4
    age < 50   → 0.2 (lower risk)
    age ≥ 50   → 0.3 (slightly higher)
  
  History Score = Credit history
    < 6 months   → 0.8 (no history)
    < 12 months  → 0.5
    < 24 months  → 0.3
    ≥ 24 months  → 0.1 (established)

Risk Level:
  0.00 - 0.33 → low
  0.33 - 0.66 → medium
  0.66 - 1.00 → high
```

---

## 📊 Risk Group Classification

```
GROUP_1: NORMAL
  Days Past Due: 0
  Meaning: On-time payment

GROUP_2: SPECIAL MENTION
  Days Past Due: 1-30
  Meaning: Early delinquency

GROUP_3: SUBSTANDARD
  Days Past Due: 31-90
  Meaning: Significant delinquency

GROUP_4: DOUBTFUL
  Days Past Due: 90+
  Meaning: Default/Severe delinquency
```

---

## 📁 File Structure

```
app/
├── services/
│   ├── upload_service.py         # ETL & file processing
│   └── risk_analysis_service.py  # Risk calculations
├── api/
│   ├── routers/
│   │   ├── upload.py             # Upload API endpoints
│   │   └── analysis.py           # Analysis API endpoints
│   └── endpoints.py              # Main router
└── main.py                       # FastAPI app config

docs/
├── ETL_IMPORT_PIPELINE.sql       # SQL ETL script
└── UPLOAD_AND_ANALYSIS_GUIDE.md  # This file
```

---

## 🚀 Quick Start

### Step 1: Import Data (1 lần)
```bash
sqlcmd -S DESKTOP-7EPLMS3\SQLEXPRESS -U sa -P 12345 -d CreditRiskDB \
  -i "D:\GitHub\credit-risk-backend\docs\ETL_IMPORT_PIPELINE.sql"
```

### Step 2: Start Server
```bash
python -m uvicorn app.main:app --reload
```

### Step 3: Test Upload (Optional)
```bash
# Upload file (replace with your actual file)
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@D:\GitHub\credit-risk-backend\data\Data_1.csv"
```

### Step 4: Analyze Risks
```bash
# Calculate risk score
curl -X POST "http://localhost:8000/api/v1/analyze/risk-score" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"income": 50000000, "debt_obligation": 10000000, "age": 35}'

# Get portfolio summary
curl "http://localhost:8000/api/v1/analyze/portfolio" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get customer profile
curl "http://localhost:8000/api/v1/analyze/customer/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ❓ FAQ

### Q: Làm sao để upload file nhiều lần?
**A:** Mỗi upload được track bằng `upload_id`. Có thể upload multiple files tuần tự.

### Q: File size tối đa là bao nhiêu?
**A:** 50 MB mỗi file.

### Q: Tôi có thể upload file XLSX không?
**A:** Có, hỗ trợ CSV, XLSX, XLS.

### Q: Risk score được tính như thế nào?
**A:** Xem **Risk Scoring Formula** section ở trên.

### Q: GROUP_1-4 là gì?
**A:** Xem **Risk Group Classification** section ở trên.

### Q: Dữ liệu được lưu ở đâu?
**A:** SQL Server database `CreditRiskDB`, tables: Customer, Loan_Application, Loan_Facility, etc.

### Q: Tôi có thể xoá staging tables không?
**A:** Có, sau khi import hoàn tất, staging tables có thể xoá.

---

## 📞 Support

Nếu có lỗi, kiểm tra:
1. File CSV format (header row required)
2. Database connection (check CreditRiskDB)
3. JWT token (Authorization header)
4. File size (< 50 MB)

---

*Last Updated: 2026-01-28*
