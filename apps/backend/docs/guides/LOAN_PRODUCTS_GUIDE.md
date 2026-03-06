# Hệ Thống Quản Lý Loại Vay (Loan Products Management System)

## Tổng Quan

Hệ thống quản lý loại vay cung cấp:
- ✅ 5 loại sản phẩm vay chuẩn hóa theo tiêu chuẩn ngân hàng Việt Nam
- ✅ Tính toán hạn mức vay tự động dựa trên tiêu chí khách hàng
- ✅ So sánh lãi suất theo từng loại vay và tổ chức
- ✅ Khuyến nghị loại vay phù hợp cho từng khách hàng
- ✅ Quản lý giá cả (pricing rules) theo nhóm khách hàng

---

## 5 Loại Vay Được Hỗ Trợ

### 1. **Vay Tín Chấp Cá Nhân** (Unsecured Personal Loan)
```
Code: TIN_CHAP_01
- Hạn mức: 10M - 500M VND (một số ngân hàng lên 1B)
- Thời hạn: 1 - 7 năm (12 - 84 tháng)
- Lãi suất: 12% - 24%/năm (thường 18%)
- Yêu cầu: Không cần đảm bảo, dựa lương/thu nhập ổn định
- DTI tối đa: 50%
- Điểm tín dụng tối thiểu: 600
- Phê duyệt: Quản lý chi nhánh (3 ngày)
```

**Điều kiện cấp:**
- Cá nhân, hộ kinh doanh nhỏ
- Thu nhập ổn định (lương, kinh doanh)
- Yêu cầu hồ sơ: CCCD, bảng lương, đơn xác nhận công việc, sao kê ngân hàng

---

### 2. **Vay Kinh Doanh Tín Chấp** (Unsecured Business Loan)
```
Code: TIN_CHAP_02
- Hạn mức: 50M - 500M VND (một số ngân hàng lên 1B)
- Thời hạn: 6 - 7 năm (6 - 84 tháng)
- Lãi suất: 10% - 18%/năm (thường 14%)
- Yêu cầu: Không cần đảm bảo, dựa thu nhập kinh doanh
- DTI tối đa: 60%
- Điểm tín dụng tối thiểu: 550
- Phê duyệt: Hội đồng tín dụng (5 ngày)
```

**Điều kiện cấp:**
- Doanh nghiệp SME, hộ kinh doanh, cá nhân kinh doanh
- Doanh thu/lợi nhuận ổn định
- Yêu cầu hồ sơ: CCCD, đăng ký kinh doanh, tờ khai thuế, sao kê ngân hàng, kế hoạch kinh doanh

---

### 3. **Vay Thế Chấp Sổ Đỏ/Sổ Hồng** (Secured Real Estate Mortgage)
```
Code: THE_CHAP_01
- Hạn mức: 100M - 5B VND (70-90% giá trị bất động sản)
- Thời hạn: 5 - 35 năm (60 - 420 tháng)
- Lãi suất: 6% - 12%/năm (ưu đãi: 5.5%)
- Yêu cầu: Thế chấp sổ đỏ/sổ hồng
- LTV: 85% (Loan-to-Value)
- DTI tối đa: 50%
- Điểm tín dụng tối thiểu: 650
- Phê duyệt: Hội đồng tín dụng (15 ngày)
```

**Điều kiện cấp:**
- Cá nhân, doanh nghiệp
- Mục đích: Mua nhà, sửa nhà, kinh doanh
- Yêu cầu hồ sơ: CCCD, sổ đỏ/hồng, định giá bất động sản, giấy kết hôn, sao kê

---

### 4. **Vay Thế Chấp Ô Tô** (Secured Vehicle Loan)
```
Code: THE_CHAP_02
- Hạn mức: 50M - 2B VND (70-80% giá trị xe)
- Thời hạn: 1 - 7 năm (12 - 84 tháng)
- Lãi suất: 7% - 13%/năm (ưu đãi: 6.5%)
- Yêu cầu: Thế chấp ô tô/xe máy
- LTV: 80%
- DTI tối đa: 50%
- Điểm tín dụng tối thiểu: 600
- Phê duyệt: Quản lý chi nhánh (7 ngày)
```

**Điều kiện cấp:**
- Cá nhân, doanh nghiệp
- Ô tô/xe máy đăng ký lần đầu hoặc xe cũ
- Yêu cầu hồ sơ: CCCD, giấy đăng ký xe, định giá xe, bảo hiểm, sao kê

---

### 5. **Vay Thế Chấp Sổ Tiết Kiệm** (Secured Savings Loan)
```
Code: THE_CHAP_03
- Hạn mức: 10M - 1B VND (90-100% giá trị sổ)
- Thời hạn: 3 - 60 tháng
- Lãi suất: 4% - 8%/năm (thường 6%)
- Yêu cầu: Thế chấp sổ tiết kiệm
- LTV: 95%
- DTI tối đa: 50%
- Điểm tín dụng tối thiểu: 500 (thấp nhất)
- Phê duyệt: Quản lý chi nhánh (1 ngày - nhanh nhất)
```

**Điều kiện cấp:**
- Cá nhân có sổ tiết kiệm
- Lãi suất thấp nhất, phê duyệt nhanh nhất
- Yêu cầu hồ sơ: CCCD, sổ tiết kiệm, sao kê

---

## Cấu Trúc Database

### Bảng Chính

#### 1. **Loan_Product**
```sql
- product_id (PK)
- product_code: TIN_CHAP_01, THE_CHAP_01, ...
- product_name: Tên tiếng Việt
- product_name_en: Tên tiếng Anh
- category: 'unsecured' hoặc 'secured'
- min_amount, max_amount: Hạn mức tối thiểu/tối đa
- min/max_term_months: Thời hạn
- min/max_interest_rate: Lãi suất
- typical_interest_rate: Lãi suất thường tính
- promotion_interest_rate: Lãi suất ưu đãi
- collateral_required: Có cần đảm bảo
- collateral_type: Loại đảm bảo (real_estate, vehicle, savings_account)
- ltv_ratio: Tỷ lệ LTV (%)
- max_dti_ratio: Tỷ lệ DTI tối đa (%)
- min_credit_score: Điểm tín dụng tối thiểu
- processing_time_days: Thời gian phê duyệt
- approval_authority: Cấp phê duyệt (branch_manager, credit_committee)
- is_active: Trạng thái hoạt động
```

#### 2. **Loan_Pricing_Rule**
```sql
- rule_id (PK)
- product_id (FK): Liên kết đến Loan_Product
- customer_type: 'individual', 'business', 'self_employed'
- credit_score_min/max: Phạm vi điểm tín dụng
- base_interest_rate: Lãi suất cơ bản
- risk_premium: Phí rủi ro bổ sung
- final_interest_rate: Lãi suất cuối cùng
- loyalty_discount: Chiết khấu khách hàng cũ (%)
- early_repayment_discount: Chiết khấu trả nợ sớm (%)
- effective_from/to: Thời gian hiệu lực
```

#### 3. **Loan_Approval_Limit**
```sql
- limit_id (PK)
- product_id (FK): Liên kết đến Loan_Product
- approval_level: 'branch_manager', 'credit_committee', 'senior_management'
- min/max_approval_amount: Hạn mức phê duyệt
- min_customer_credit_score: Điểm tín dụng tối thiểu
- max_dti_ratio: DTI tối đa
- max_processing_days: Thời gian phê duyệt tối đa
```

#### 4. **Loan_Approval**
```sql
- approval_id (PK)
- facility_id (FK): Liên kết đến Loan_Facility (nếu được phê duyệt)
- product_id (FK): Loại vay
- customer_id (FK): Khách hàng
- requested_amount: Hạn mức yêu cầu
- requested_term_months: Thời hạn yêu cầu
- approved_amount: Hạn mức được phê duyệt
- approved_term_months: Thời hạn được phê duyệt
- approved_rate: Lãi suất phê duyệt
- status: 'pending', 'approved', 'rejected', 'cancelled'
- approved_by (FK): Người phê duyệt
- approval_date: Ngày phê duyệt
- special_conditions: Điều kiện đặc biệt
```

#### 5. **Loan_Product_Requirement**
```sql
- requirement_id (PK)
- product_id (FK): Loại vay
- requirement_type: 'document', 'collateral', 'ratio', 'score'
- requirement_code: Mã yêu cầu
- requirement_name: Tên yêu cầu
- is_mandatory: Bắt buộc hay không
- minimum_value/maximum_value: Giá trị tối thiểu/tối đa
```

---

## Service Layer - LoanProductService

### Các Phương Thức Chính

#### 1. **get_all_products()** 
Lấy danh sách tất cả các loại vay hoạt động
```python
products = LoanProductService.get_all_products()
# Returns: List[Dict] với đầy đủ thông tin sản phẩm
```

#### 2. **get_product_by_id(product_id)**
Lấy chi tiết một loại vay cụ thể
```python
product = LoanProductService.get_product_by_id(1)
# Returns: Dict chứa toàn bộ thông tin sản phẩm
```

#### 3. **recommend_product_for_customer(age, annual_income, monthly_income, credit_score, customer_type, collateral_available, dti_ratio)**
Khuyến nghị loại vay phù hợp dựa trên thông tin khách hàng
```python
recommendations = LoanProductService.recommend_product_for_customer(
    age=35,
    annual_income=500_000_000,  # VND
    monthly_income=40_000_000,
    credit_score=700,
    customer_type="individual",
    collateral_available="real_estate",
    dti_ratio=25
)
# Returns: List[Dict] các loại vay phù hợp
```

#### 4. **calculate_max_loan_amount(product_id, monthly_income, annual_income, collateral_value)**
Tính hạn mức vay tối đa dựa trên loại sản phẩm
```python
max_amount, reason = LoanProductService.calculate_max_loan_amount(
    product_id=1,
    monthly_income=40_000_000,
    annual_income=500_000_000,
    collateral_value=2_000_000_000  # optional
)
# Returns: (float, str) - (hạn mức, lý do giới hạn)
```

#### 5. **calculate_monthly_payment(loan_amount, annual_interest_rate, term_months)**
Tính thanh toán hàng tháng (dùng công thức khấu hao)
```python
monthly_payment = LoanProductService.calculate_monthly_payment(
    loan_amount=300_000_000,
    annual_interest_rate=18,
    term_months=36
)
# Returns: float - thanh toán hàng tháng
```

#### 6. **calculate_total_interest(loan_amount, annual_interest_rate, term_months)**
Tính tổng lãi suất phải trả
```python
total_interest = LoanProductService.calculate_total_interest(
    loan_amount=300_000_000,
    annual_interest_rate=18,
    term_months=36
)
# Returns: float - tổng lãi
```

#### 7. **generate_loan_scenario(product_id, loan_amount, annual_interest_rate, term_months)**
Tạo kịch bản vay chi tiết
```python
scenario = LoanProductService.generate_loan_scenario(
    product_id=1,
    loan_amount=300_000_000,
    annual_interest_rate=18,
    term_months=36
)
# Returns: Dict {
#     "product": str,
#     "loan_amount": float,
#     "interest_rate": float,
#     "term_months": int,
#     "monthly_payment": float,
#     "total_interest": float,
#     "total_amount_paid": float,
#     "daily_interest": float
# }
```

#### 8. **compare_products(loan_amount, term_months)**
So sánh lãi suất tất cả các loại vay có khả năng
```python
comparisons = LoanProductService.compare_products(
    loan_amount=200_000_000,
    term_months=24
)
# Returns: List[Dict] sắp xếp theo thanh toán hàng tháng (từ thấp đến cao)
```

---

## API Endpoints

### Base URL
```
/api/v1/products
```

### 1. **GET /api/v1/products**
Lấy danh sách tất cả loại vay
```bash
curl http://localhost:8000/api/v1/products
```

**Response:**
```json
[
  {
    "product_id": 1,
    "product_code": "TIN_CHAP_01",
    "product_name": "Vay tín chấp cá nhân",
    "product_name_en": "Unsecured Personal Loan",
    "category": "unsecured",
    "min_amount": 10000000,
    "max_amount": 500000000,
    "min_term_months": 12,
    "max_term_months": 84,
    "min_interest_rate": 12.0,
    "max_interest_rate": 24.0,
    "typical_interest_rate": 18.0,
    "collateral_required": false,
    "collateral_type": null,
    "ltv_ratio": null,
    "max_dti_ratio": 50.0,
    "min_credit_score": 600,
    "processing_time_days": 3
  }
]
```

---

### 2. **GET /api/v1/products/{product_id}**
Lấy chi tiết một loại vay
```bash
curl http://localhost:8000/api/v1/products/1
```

---

### 3. **POST /api/v1/products/recommend**
Khuyến nghị loại vay cho khách hàng
```bash
curl -X POST http://localhost:8000/api/v1/products/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "age": 35,
    "annual_income": 500000000,
    "monthly_income": 40000000,
    "credit_score": 700,
    "customer_type": "individual",
    "collateral_available": "real_estate",
    "dti_ratio": 25
  }'
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "recommendations": [
    {
      "product_id": 1,
      "product_name": "Vay tín chấp cá nhân",
      "category": "unsecured",
      "min_amount": 10000000,
      "max_amount": 500000000,
      "interest_rate_range": "12.0%-24.0%",
      "term_range": "12-84 tháng",
      "processing_time": "3 ngày",
      "reason": "Eligible"
    },
    {
      "product_id": 3,
      "product_name": "Vay thế chấp sổ đỏ/sổ hồng",
      "category": "secured",
      "min_amount": 100000000,
      "max_amount": 5000000000,
      "interest_rate_range": "6.0%-12.0%",
      "term_range": "60-420 tháng",
      "processing_time": "15 ngày",
      "reason": "Eligible"
    }
  ]
}
```

---

### 4. **POST /api/v1/products/calculate-max-loan**
Tính hạn mức vay tối đa
```bash
curl -X POST http://localhost:8000/api/v1/products/calculate-max-loan \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "monthly_income": 40000000,
    "annual_income": 500000000
  }'
```

**Response:**
```json
{
  "success": true,
  "product_id": 1,
  "max_loan_amount": 500000000,
  "reason": "Based on product maximum"
}
```

---

### 5. **POST /api/v1/products/calculate-payment**
Tính thanh toán hàng tháng
```bash
curl -X POST http://localhost:8000/api/v1/products/calculate-payment \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "loan_amount": 300000000,
    "annual_interest_rate": 18,
    "term_months": 36
  }'
```

**Response:**
```json
{
  "monthly_payment": 10845719.12,
  "total_interest": 90445872.36,
  "total_amount_paid": 390445872.36,
  "daily_interest": 164383.56
}
```

---

### 6. **POST /api/v1/products/loan-scenario**
Tạo kịch bản vay chi tiết
```bash
curl -X POST http://localhost:8000/api/v1/products/loan-scenario \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "loan_amount": 300000000,
    "annual_interest_rate": 18,
    "term_months": 36
  }'
```

**Response:**
```json
{
  "product": "Vay tín chấp cá nhân",
  "loan_amount": 300000000,
  "interest_rate": 18,
  "term_months": 36,
  "monthly_payment": 10845719.12,
  "total_interest": 90445872.36,
  "total_amount_paid": 390445872.36,
  "daily_interest": 164383.56
}
```

---

### 7. **POST /api/v1/products/compare**
So sánh lãi suất tất cả các loại vay
```bash
curl -X POST http://localhost:8000/api/v1/products/compare \
  -H "Content-Type: application/json" \
  -d '{
    "loan_amount": 200000000,
    "term_months": 24
  }'
```

**Response:**
```json
{
  "success": true,
  "loan_amount": 200000000,
  "term_months": 24,
  "comparison_count": 4,
  "comparisons": [
    {
      "product_id": 5,
      "product_name": "Vay thế chấp sổ tiết kiệm",
      "category": "secured",
      "interest_rate": 6.0,
      "monthly_payment": 8864122.44,
      "total_interest": 12738929.56,
      "collateral_required": true
    },
    {
      "product_id": 4,
      "product_name": "Vay thế chấp ô tô",
      "category": "secured",
      "interest_rate": 10.0,
      "monthly_payment": 9228985.67,
      "total_interest": 21495646.33,
      "collateral_required": true
    }
  ]
}
```

---

### 8. **GET /api/v1/products/pricing-rules/{product_id}**
Lấy quy tắc giá cả cho loại vay
```bash
curl http://localhost:8000/api/v1/products/pricing-rules/1
```

**Response:**
```json
[
  {
    "customer_type": "individual",
    "credit_score_range": "700-999",
    "base_rate": 12.0,
    "risk_premium": 2.0,
    "final_rate": 14.0,
    "loyalty_discount": 1.0,
    "early_repayment_discount": 0.5
  },
  {
    "customer_type": "individual",
    "credit_score_range": "650-699",
    "base_rate": 15.0,
    "risk_premium": 3.0,
    "final_rate": 18.0,
    "loyalty_discount": 0.5,
    "early_repayment_discount": 0.3
  }
]
```

---

### 9. **GET /api/v1/products/search**
Tìm kiếm sản phẩm theo tiêu chí
```bash
curl "http://localhost:8000/api/v1/products/search?category=secured&max_rate=10"
```

**Parameters:**
- `category`: 'unsecured' hoặc 'secured'
- `min_amount`: Hạn mức tối thiểu
- `max_rate`: Lãi suất tối đa

**Response:**
```json
{
  "success": true,
  "count": 2,
  "products": [
    {
      "product_id": 5,
      "product_name": "Vay thế chấp sổ tiết kiệm",
      "category": "secured",
      "interest_rate": "4.0%-8.0%",
      "max_amount": 1000000000
    }
  ]
}
```

---

## Các Ví Dụ Thực Tế

### Ví dụ 1: Khách hàng cá nhân, lương ổn định

**Tình huống:**
- Tên: Nguyễn Văn A
- Tuổi: 35
- Thu nhập tháng: 40 triệu VND
- Điểm tín dụng: 700
- Có sổ đỏ trị giá: 2 tỷ VND

**Khuyến nghị:**
1. **Vay tín chấp cá nhân**: Hạn mức tối đa 500M, lãi suất 14% (được ưu tiên vì có tín dụng tốt)
2. **Vay thế chấp sổ đỏ**: Hạn mức tối đa 1.8 tỷ (85% × 2B), lãi suất ưu đãi 5.5%-7%

**Tính toán vay 300M, 36 tháng:**
- Loại vay tín chấp (18%): Thanh toán tháng = 10.8M, tổng lãi = 90.4M
- Loại vay thế chấp (6%): Thanh toán tháng = 8.8M, tổng lãi = 15.8M
→ **Khuyến nghị:** Dùng sổ đỏ để tiết kiệm 74.6M lãi

---

### Ví dụ 2: Khách hàng kinh doanh

**Tình huống:**
- Tên: Công ty ABC
- Doanh thu năm: 5 tỷ VND
- Lợi nhuận: 500 triệu VND
- Điểm tín dụng: 650
- Mục đích: Tăng vốn lưu động

**Khuyến nghị:**
1. **Vay tín chấp kinh doanh**: Hạn mức 500M-1B, lãi suất 14%, thời hạn 2-3 năm
2. **Vay thế chấp (nếu có tài sản)**: Hạn mức cao hơn, lãi suất thấp hơn

---

### Ví dụ 3: Khách hàng có sổ tiết kiệm

**Tình huống:**
- Sổ tiết kiệm: 200M VND
- Nhu cầu vay nhanh: 180M VND
- Thời gian cấp: Gấp

**Khuyến nghị:**
- **Vay thế chấp sổ tiết kiệm**: 
  - Hạn mức: 90-100% × 200M = 180-200M ✓
  - Lãi suất: 6% (thấp nhất)
  - Phê duyệt: 1 ngày (nhanh nhất)
  - Thanh toán 24 tháng: 7.5M/tháng + 15M tổng lãi

---

## Tích Hợp Với Hệ Thống Hiện Tại

### 1. **Hệ Thống Phê Duyệt**
Tích hợp với `Loan_Approval` table + workflow approval:
- Khách hàng submit yêu cầu vay → Loan_Approval record được tạo
- Quản lý chi nhánh/Hội đồng phê duyệt dựa trên `approval_limits`
- Nếu được phê duyệt → Tạo Loan_Facility record

### 2. **Hệ Thống Rủi Ro**
Tích hợp với `credit_risk_management_service`:
- Sử dụng `recommend_product_for_customer()` để gợi ý loại vay phù hợp
- Sử dụng `calculate_monthly_payment()` để tính DTI ratio
- Tích hợp risk score vào quy tắc phê duyệt

### 3. **Hệ Thống Giá**
Tích hợp với `Loan_Pricing_Rule`:
- Tự động tính lãi suất dựa trên credit score + customer type
- Áp dụng loyalty discount cho khách hàng cũ
- Áp dụng early repayment discount

### 4. **Dashboard/Reports**
- Danh sách các sản phẩm có sẵn
- So sánh lãi suất theo thời gian
- Hạn mức được phê duyệt vs yêu cầu
- Top products by volume

---

## Hướng Phát Triển Tiếp Theo

1. ✅ **Hoàn thành**: 5 loại vay chuẩn hóa
2. ✅ **Hoàn thành**: Service layer + API endpoints
3. ⏳ **Tiếp theo**: Thêm seasonal promotions (ưu đãi theo mùa)
4. ⏳ **Tiếp theo**: Thêm cross-sell opportunities (bán chéo)
5. ⏳ **Tiếp theo**: Thêm early settlement calculator (tính trả nợ sớm)
6. ⏳ **Tiếp theo**: Dashboard so sánh lãi suất theo thời gian
7. ⏳ **Tiếp theo**: Mobile app integration

---

## Tham Chiếu Nhanh

| Loại Vay | Code | Hạn Mức | Lãi Suất | Thời Hạn | Đảm Bảo | Phê Duyệt |
|----------|------|---------|----------|---------|--------|-----------|
| Tín chấp cá nhân | TIN_CHAP_01 | 10-500M | 12-24% | 1-7yr | ❌ | 3 ngày |
| Tín chấp kinh doanh | TIN_CHAP_02 | 50-500M | 10-18% | 6m-7yr | ❌ | 5 ngày |
| Thế chấp BĐS | THE_CHAP_01 | 100M-5B | 6-12% | 5-35yr | ✓ Sổ đỏ | 15 ngày |
| Thế chấp ô tô | THE_CHAP_02 | 50M-2B | 7-13% | 1-7yr | ✓ Xe | 7 ngày |
| Thế chấp sổ tiết kiệm | THE_CHAP_03 | 10M-1B | 4-8% | 3-60m | ✓ Sổ | 1 ngày |

---

## Liên Hệ & Hỗ Trợ

- **API Documentation**: `/docs` (Swagger UI)
- **Feedback**: Tạo issue trên GitHub
- **Từng câu hỏi cụ thể**: contact@creditrisk.vn
