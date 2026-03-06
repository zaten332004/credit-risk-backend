# 🏆 Hệ Thống Quản Lý Loại Vay - Loan Products Management

## 📌 Tóm Tắt

Một hệ thống quản lý **5 loại sản phẩm vay tiêu chuẩn** theo nền tảng ngân hàng Việt Nam với các tính năng:

✅ **Khuyến nghị loại vay tự động** dựa trên thông tin khách hàng
✅ **Tính hạn mức vay tối đa** dựa trên lương/doanh thu/tài sản  
✅ **Tính toán thanh toán hàng tháng** sử dụng công thức khấu hao
✅ **So sánh lãi suất** giữa các loại vay  
✅ **Quản lý quy tắc giá cả** theo nhóm khách hàng  
✅ **API RESTful hoàn chỉnh** (9 endpoints)  

---

## 🎯 5 Loại Vay Được Hỗ Trợ

| # | Tên | Code | Hạn Mức | Lãi Suất | Thời Hạn | Đảm Bảo | Phê Duyệt |
|---|---|---|---|---|---|---|---|
| 1️⃣ | Tín chấp cá nhân | TIN_CHAP_01 | 10-500M | 12-24% | 1-7yr | ❌ | 3d |
| 2️⃣ | Tín chấp kinh doanh | TIN_CHAP_02 | 50-500M | 10-18% | 6m-7yr | ❌ | 5d |
| 3️⃣ | Thế chấp BĐS | THE_CHAP_01 | 100M-5B | 6-12% | 5-35yr | ✓ | 15d |
| 4️⃣ | Thế chấp ô tô | THE_CHAP_02 | 50M-2B | 7-13% | 1-7yr | ✓ | 7d |
| 5️⃣ | Thế chấp sổ tiết kiệm | THE_CHAP_03 | 10M-1B | 4-8% | 3-60m | ✓ | 1d |

---

## 🚀 Quick Start

### 1️⃣ Khởi Tạo Database
```bash
python scripts/init_loan_products.py
```

### 2️⃣ Chạy Backend
```bash
python -m uvicorn app.main:app --reload
```

### 3️⃣ Truy Cập API
```
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

---

## 💡 API Examples

### Khuyến Nghị Loại Vay
```bash
curl -X POST http://localhost:8000/api/v1/products/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "age": 35,
    "annual_income": 500000000,
    "monthly_income": 40000000,
    "credit_score": 700,
    "customer_type": "individual",
    "collateral_available": "real_estate"
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
      "max_amount": 500000000,
      "interest_rate_range": "12.0%-24.0%",
      "processing_time": "3 ngày"
    },
    {
      "product_id": 3,
      "product_name": "Vay thế chấp sổ đỏ",
      "max_amount": 5000000000,
      "interest_rate_range": "6.0%-12.0%",
      "processing_time": "15 ngày"
    }
  ]
}
```

### Tính Thanh Toán Hàng Tháng
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

### So Sánh Sản Phẩm
```bash
curl -X POST http://localhost:8000/api/v1/products/compare \
  -H "Content-Type: application/json" \
  -d '{
    "loan_amount": 200000000,
    "term_months": 24
  }'
```

---

## 📁 Cấu Trúc File

```
app/
├── services/
│   └── loan_product_service.py        # Service layer chính (550+ dòng)
├── db/
│   └── loan_product_models.py         # Database models (187 dòng)
├── api/
│   └── routers/
│       └── loan_products.py           # API endpoints (360 dòng)
└── main.py                            # Đã thêm router

scripts/
└── init_loan_products.py              # Migration script (430 dòng)

docs/
├── LOAN_PRODUCTS_GUIDE.md             # Tài liệu chi tiết (500+ dòng)
└── LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md # Tóm tắt triển khai

LOAN_PRODUCTS_QUICKSTART.md            # Quick start guide
```

---

## 🔌 API Endpoints (9 endpoints)

| Method | Endpoint | Mô Tả |
|--------|----------|-------|
| GET | `/api/v1/products` | Danh sách tất cả loại vay |
| GET | `/api/v1/products/{id}` | Chi tiết sản phẩm |
| POST | `/api/v1/products/recommend` | Khuyến nghị loại vay |
| POST | `/api/v1/products/calculate-max-loan` | Tính hạn mức tối đa |
| POST | `/api/v1/products/calculate-payment` | Tính thanh toán hàng tháng |
| POST | `/api/v1/products/loan-scenario` | Tạo kịch bản vay |
| POST | `/api/v1/products/compare` | So sánh sản phẩm |
| GET | `/api/v1/products/pricing-rules/{id}` | Lấy quy tắc giá cả |
| GET | `/api/v1/products/search` | Tìm kiếm sản phẩm |

---

## 💾 Database Schema

### Bảng Chính (5 bảng)

1. **Loan_Product** - Thông tin sản phẩm vay
2. **Loan_Pricing_Rule** - Quy tắc giá cả theo nhóm khách hàng
3. **Loan_Approval_Limit** - Hạn mức phê duyệt theo cấp
4. **Loan_Approval** - Hồ sơ phê duyệt vay
5. **Loan_Product_Requirement** - Yêu cầu cụ thể sản phẩm

### Dữ Liệu Khởi Tạo

- 5 sản phẩm vay chính
- 7 quy tắc giá cả (theo nhóm khách hàng)
- 10 hạn mức phê duyệt (theo cấp phê duyệt)

---

## 🎓 Chức Năng Chính

### 1. Khuyến Nghị Loại Vay
Tự động đề xuất loại vay phù hợp dựa trên:
- Tuổi, lương/doanh thu
- Điểm tín dụng
- Loại khách hàng (cá nhân/kinh doanh)
- Tài sản có sẵn (sổ đỏ, ô tô, sổ tiết kiệm)
- Tỷ lệ DTI hiện tại

### 2. Tính Hạn Mức Tối Đa
- **Tín chấp**: Hạn mức = min(product_max, lương × tỷ lệ)
- **Thế chấp**: Hạn mức = min(product_max, tài sản × LTV%)

### 3. Tính Thanh Toán
Sử dụng công thức khấu hao tiêu chuẩn:
$$M = P \times \frac{r(1+r)^n}{(1+r)^n - 1}$$

### 4. So Sánh Sản Phẩm
Hiển thị tất cả loại vay phù hợp sắp xếp theo:
- Lãi suất (từ thấp đến cao)
- Thanh toán hàng tháng
- Tổng lãi phải trả

### 5. Quản Lý Giá Cả
- Base rate + Risk premium = Final rate
- Loyalty discount cho khách hàng cũ
- Early repayment discount

---

## 📊 Ví Dụ Thực Tế

### Scenario 1: Khách hàng cá nhân
**Input:** 35 tuổi, 40M/tháng, điểm 700, có sổ đỏ 2B
**Khuyến nghị:** 
- Vay tín chấp 500M @ 14% (tốc độ phê duyệt cao)
- Vay thế chấp BĐS 1.8B @ 5.5% (tiết kiệm lãi)

### Scenario 2: Khách hàng kinh doanh
**Input:** Doanh thu 5B/năm, điểm 650, nhu cầu 500M
**Khuyến nghị:**
- Vay tín chấp kinh doanh 500M @ 14%
- Hoặc thế chấp nếu có tài sản (lãi suất thấp hơn)

### Scenario 3: Cần vay gấp
**Input:** Có sổ tiết kiệm 200M, cần 180M ngay
**Khuyến nghị:**
- Vay thế chấp sổ tiết kiệm 180M @ 6% (phê duyệt 1 ngày)

---

## 🔄 Tích Hợp

### Tích Hợp Risk Management
```python
monthly_payment = LoanProductService.calculate_monthly_payment(...)
new_dti = (obligations + monthly_payment) / income * 100

if new_dti <= product.max_dti_ratio:
    approve_application()
else:
    reject_application("DTI vượt quá quy định")
```

### Tích Hợp Approval System
```python
recommendations = LoanProductService.recommend_product_for_customer(...)
max_loan = LoanProductService.calculate_max_loan_amount(...)

LoanApprovalDB.create(
    product_id=recommendations[0].product_id,
    requested_amount=customer_request,
    approved_amount=min(customer_request, max_loan)
)
```

---

## 📚 Tài Liệu

| Tài Liệu | Mô Tả |
|----------|-------|
| 📖 **LOAN_PRODUCTS_GUIDE.md** | Hướng dẫn chi tiết (500+ dòng) |
| 📋 **LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md** | Tóm tắt triển khai |
| 🚀 **LOAN_PRODUCTS_QUICKSTART.md** | Quick start guide |
| 🔌 **Swagger UI** | `/docs` - Interactive API docs |

---

## ✅ Kết Quả Kiểm Thử

```
✓ 5 sản phẩm được tải thành công
✓ Khuyến nghị 2 loại vay phù hợp cho khách hàng mẫu
✓ Tính thanh toán hàng tháng: 10.84M (300M @ 18%, 36 tháng)
✓ Tổng lãi: 90.44M
✓ So sánh 4 loại vay: sắp xếp đúng theo lãi suất
✓ Tất cả 9 API endpoints hoạt động
```

---

## 🎯 Lợi Ích

### 💼 Cho Khách Hàng
- Dễ so sánh các loại vay
- Tính toán chính xác thanh toán hàng tháng
- Biết được hạn mức có thể vay
- Nhận khuyến nghị loại vay phù hợp

### 🏦 Cho Ngân Hàng
- Tự động hóa khuyến nghị sản phẩm
- Chuẩn hóa quy tắc phê duyệt
- Tăng cơ hội bán chéo (cross-sell)
- Tuân thủ quy định lãi suất
- Giảm thời gian phê duyệt

### 💻 Cho IT
- API RESTful chuẩn
- Dễ tích hợp với các module
- Tài liệu đầy đủ
- Dễ mở rộng (thêm sản phẩm mới)

---

## 🔮 Hướng Phát Triển

- [ ] Seasonal promotions (ưu đãi theo mùa)
- [ ] Cross-sell recommendations
- [ ] Early settlement calculator
- [ ] Dashboard visualization
- [ ] Mobile API integration
- [ ] ML-based recommendations

---

## 📞 Hỗ Trợ

- 📖 **Full Documentation**: `docs/LOAN_PRODUCTS_GUIDE.md`
- 🔌 **API Docs**: http://localhost:8000/docs
- 💬 **Source Code**: 
  - Service: `app/services/loan_product_service.py`
  - Models: `app/db/loan_product_models.py`
  - API: `app/api/routers/loan_products.py`

---

## ✨ Tóm Tắt

Hệ thống quản lý loại vay đã được triển khai **hoàn toàn** với:
- ✅ 5 loại vay tiêu chuẩn
- ✅ Service layer đầy đủ
- ✅ 9 API endpoints
- ✅ 5 database tables
- ✅ Khởi tạo dữ liệu mẫu
- ✅ Tài liệu chi tiết
- ✅ Kiểm thử thành công

**Sẵn sàng để sử dụng ngay!** 🎉

---

*Last Updated: February 1, 2026*
*Version: 1.0*
