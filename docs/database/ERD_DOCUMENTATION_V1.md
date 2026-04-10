# Tài liệu bảng dữ liệu và hướng dẫn vẽ ERD

## 1) Phạm vi và nguồn chuẩn

- **Nguồn chính (MySQL)**: `apps/backend/docs/database/Database_MySQL_V1.sql` (39 bảng) - **Sử dụng cho deployment**
- Nguồn cũ (SQL Server): `apps/backend/docs/database/Database_full_V1.sql` (39 bảng) - _Giữ lại cho tham khảo_
- Nguồn phụ: `apps/backend/docs/sql-scripts/Database_full_V1.sql` (25 bảng) - _Không sử dụng_
- Tài liệu này được cập nhật để phản ánh schema MySQL mới

## 2) Nguyên tắc quyết định bảng nào cần đưa vào ERD

- Đưa vào `ERD nghiệp vụ chính` nếu bảng:
- Là bảng giao dịch cốt lõi của quy trình cấp tín dụng, quản lý khoản vay, quản lý rủi ro.
- Có quan hệ FK trực tiếp với các bảng cốt lõi khác.
- Được dùng để vận hành màn hình nghiệp vụ hàng ngày.

- Đưa vào `ERD hỗ trợ` nếu bảng:
- Phục vụ quản trị hệ thống, audit, chat, phân quyền.

- Không đưa vào `ERD nghiệp vụ chính` nếu bảng:
- Là bảng staging/import (`stg_*`).
- Là bảng tổng hợp báo cáo snapshot/KPI chỉ đọc.

## 3) Công dụng từng bảng và khuyến nghị ERD

## 3.1 Nhóm Customer & Lending Core

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `Customer` | Hồ sơ khách hàng trung tâm của nghiệp vụ tín dụng | Có (Core) |
| `Customer_Employment` | Lịch sử công việc/thu nhập của khách hàng | Có (Core) |
| `FINANCIAL_INDICATOR` | Chỉ số tài chính theo thời điểm của khách hàng | Có (Core) |
| `Customer_Payment_Statistics` | Chỉ số tổng hợp hành vi trả nợ của khách hàng | Có (Core) |
| `Loan_Application` | Hồ sơ đề nghị vay vốn | Có (Core) |
| `Loan_Facility` | Khoản vay đã phê duyệt/giải ngân, thực thể trung tâm | Có (Core) |
| `Loan_Repayment_Schedule` | Lịch trả nợ dự kiến theo kỳ | Có (Core) |
| `Loan_Payment` | Giao dịch trả nợ thực tế | Có (Core) |
| `Loan_Delinquency` | Theo dõi trạng thái quá hạn | Có (Core) |
| `Loan_Classification` | Phân nhóm nợ/rủi ro theo quy tắc nghiệp vụ | Có (Core) |
| `Loan_Status_Migration` | Lịch sử chuyển nhóm nợ | Có (Core) |
| `Provision_Allocation` | Phân bổ dự phòng theo khoản vay và nhóm rủi ro | Có (Core) |
| `Risk_Group` | Danh mục nhóm rủi ro, mức dự phòng | Có (Core) |
| `Alert` | Cảnh báo rủi ro theo khách hàng/khoản vay | Có (Core) |
| `Transaction_Log` | Nhật ký giao dịch phát sinh trên khoản vay | Có (Core) |
| `Monthly_Delinquency` | Snapshot quá hạn theo tháng/facility | Tùy chọn (Reporting) |

## 3.2 Nhóm Product Policy

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `Loan_Product` | Danh mục sản phẩm tín dụng | Có (Product) |
| `Loan_Product_Requirement` | Điều kiện/chứng từ bắt buộc theo sản phẩm | Có (Product) |
| `Loan_Pricing_Rule` | Quy tắc lãi suất theo phân khúc/score | Có (Product) |
| `Loan_Approval_Limit` | Hạn mức và ngưỡng duyệt theo sản phẩm/cấp duyệt | Có (Product) |

## 3.3 Nhóm Risk/Model

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `LINEAR_MODEL` | Danh mục model chấm điểm | Có (Risk/ML) |
| `REGRESSION_COEFFICIENT` | Hệ số từng biến của model | Có (Risk/ML) |
| `RISK_PREDICTION` | Kết quả chấm điểm rủi ro cho hồ sơ vay/khách hàng | Có (Risk/ML) |
| `SHAP_Explanation` | Giải thích đóng góp đặc trưng cho dự đoán | Có (Risk/ML) |
| `Model_Version` | Metadata version model và metrics | Tùy chọn (Model Ops) |

## 3.4 Nhóm User & Support

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `Role` | Danh mục vai trò hệ thống | Có (Support) |
| `User` | Người dùng hệ thống và trạng thái vận hành | Có (Support) |
| `Chat_Session` | Phiên chat của người dùng | Có (Support) |
| `Chat_History` | Nội dung chat theo phiên | Có (Support) |
| `Audit_Log` | Nhật ký thao tác để truy vết | Có (Support) |

## 3.5 Nhóm Portfolio Aggregation

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `Portfolio_Snapshot` | Snapshot tổng quan danh mục theo ngày | Không đưa vào ERD nghiệp vụ chính |
| `Portfolio_Risk_Summary` | KPI tổng hợp theo kỳ báo cáo | Không đưa vào ERD nghiệp vụ chính |

## 3.6 Nhóm Staging/Import

| Bảng | Công dụng | Khuyến nghị ERD |
|---|---|---|
| `stg_Account` | Dữ liệu staging tài khoản | Không (Staging) |
| `stg_Currency` | Dữ liệu staging tiền tệ | Không (Staging) |
| `stg_Date` | Dữ liệu staging ngày/thời gian | Không (Staging) |
| `stg_ExchangeRate` | Dữ liệu staging tỷ giá | Không (Staging) |
| `stg_FinanceFact` | Dữ liệu staging fact tài chính | Không (Staging) |
| `stg_SalesOrder` | Dữ liệu staging bán hàng | Không (Staging) |
| `stg_Scenario` | Dữ liệu staging kịch bản | Không (Staging) |

## 4) Quan hệ FK chính cần thể hiện trên ERD

### 4.1 Customer/Lending (CẬP NHẬT - Logic phân loại rủi ro)

**Thay đổi quan trọng:**
- ❌ **Cũ**: `Loan_Classification.facility_id -> Loan_Facility.facility_id` (phân loại sau khi giải ngân)
- ✅ **Mới**: `Loan_Classification.application_id -> Loan_Application.application_id` (phân loại tại nơi nộp đơn)
- Lợi ích: Khách hàng nộp đơn vay → Hệ thống phân loại rủi ro trực tiếp → Quyết định duyệt/từ chối

**FK quan hệ chính:**
- `Customer.user_id -> User.user_id`
- `Customer_Employment.customer_id -> Customer.customer_id` (CASCADE)
- `Customer_Payment_Statistics.customer_id -> Customer.customer_id`
- `FINANCIAL_INDICATOR.customer_id -> Customer.customer_id`
- `Loan_Application.customer_id -> Customer.customer_id`
- `Loan_Facility.application_id -> Loan_Application.application_id`
- `Loan_Facility.customer_id -> Customer.customer_id`
- `Loan_Repayment_Schedule.facility_id -> Loan_Facility.facility_id`
- `Loan_Payment.facility_id -> Loan_Facility.facility_id`
- `Loan_Payment.schedule_id -> Loan_Repayment_Schedule.schedule_id`
- `Loan_Delinquency.facility_id -> Loan_Facility.facility_id`
- `Loan_Classification.application_id -> Loan_Application.application_id` **[NEW]**
- `Loan_Classification.facility_id -> Loan_Facility.facility_id` (optional, có thể NULL)
- `Loan_Classification.group_id -> Risk_Group.group_id`
- `Loan_Classification.classified_by -> User.user_id`
- `Loan_Status_Migration.facility_id -> Loan_Facility.facility_id`
- `Provision_Allocation.facility_id -> Loan_Facility.facility_id`
- `Provision_Allocation.risk_group_id -> Risk_Group.group_id`
- `Provision_Allocation.allocated_by -> User.user_id`
- `Alert.customer_id -> Customer.customer_id`
- `Alert.facility_id -> Loan_Facility.facility_id`
- `Transaction_Log.facility_id -> Loan_Facility.facility_id`
- `Monthly_Delinquency.facility_id -> Loan_Facility.facility_id`

### 4.2 Product

- `Loan_Product_Requirement.product_id -> Loan_Product.product_id`
- `Loan_Pricing_Rule.product_id -> Loan_Product.product_id`
- `Loan_Approval_Limit.product_id -> Loan_Product.product_id`

### 4.3 Risk/Model

- `REGRESSION_COEFFICIENT.model_id -> LINEAR_MODEL.model_id`
- `RISK_PREDICTION.model_id -> LINEAR_MODEL.model_id`
- `RISK_PREDICTION.application_id -> Loan_Application.application_id`
- `RISK_PREDICTION.customer_id -> Customer.customer_id`
- `SHAP_Explanation.prediction_id -> RISK_PREDICTION.prediction_id`

### 4.4 User/Support

- `User.role_id -> Role.role_id`
- `Chat_Session.user_id -> User.user_id`
- `Chat_History.session_id -> Chat_Session.session_id`
- `Chat_History.user_id -> User.user_id`
- `Audit_Log.user_id -> User.user_id`

## 5) Nên vẽ ERD thành 4 sơ đồ riêng

## 5.1 ERD-01: Lending Core (quan trọng nhất)

Mục tiêu: mô tả vòng đời khoản vay từ khách hàng, hồ sơ vay, **phân loại rủi ro tại nơi nộp đơn**, khoản vay, lịch trả, trả nợ, quá hạn, dự phòng, cảnh báo.

**Luồng mới:**
1. Customer nộp Loan_Application
2. Hệ thống phân loại Risk (Loan_Classification) dựa trên Risk_Group
3. Duyệt/từ chối → Giải ngân Loan_Facility
4. Tracking: Payment, Delinquency, Classification status migration

```mermaid
erDiagram
    Role ||--o{ User : has
    User ||--o{ Customer : owns
    Customer ||--o{ Customer_Employment : has
    Customer ||--o{ FINANCIAL_INDICATOR : has
    Customer ||--o{ Customer_Payment_Statistics : has
    Customer ||--o{ Loan_Application : submits
    Loan_Application ||--o{ Loan_Facility : creates
    Customer ||--o{ Loan_Facility : borrows
    Loan_Facility ||--o{ Loan_Repayment_Schedule : plans
    Loan_Facility ||--o{ Loan_Payment : receives
    Loan_Repayment_Schedule ||--o{ Loan_Payment : maps
    Loan_Facility ||--o{ Loan_Delinquency : tracks
    Loan_Facility ||--o{ Loan_Classification : classifies
    Risk_Group ||--o{ Loan_Classification : assigns
    User ||--o{ Loan_Classification : classified_by
    Loan_Facility ||--o{ Loan_Status_Migration : migrates
    Loan_Facility ||--o{ Provision_Allocation : allocates
    Risk_Group ||--o{ Provision_Allocation : rates
    User ||--o{ Provision_Allocation : allocated_by
    Customer ||--o{ Alert : triggers
    Loan_Facility ||--o{ Alert : triggers
    Loan_Facility ||--o{ Transaction_Log : logs
    Loan_Facility ||--o{ Monthly_Delinquency : snapshots
```

## 5.2 ERD-02: Product Policy

Mục tiêu: quản trị catalogue sản phẩm và rule vận hành duyệt giá.

```mermaid
erDiagram
    Loan_Product ||--o{ Loan_Product_Requirement : has
    Loan_Product ||--o{ Loan_Pricing_Rule : priced_by
    Loan_Product ||--o{ Loan_Approval_Limit : approved_by
```

## 5.3 ERD-03: Risk/ML

Mục tiêu: mô tả pipeline chấm điểm và giải thích model.

```mermaid
erDiagram
    LINEAR_MODEL ||--o{ REGRESSION_COEFFICIENT : contains
    LINEAR_MODEL ||--o{ RISK_PREDICTION : scores
    Customer ||--o{ RISK_PREDICTION : predicted_for
    Loan_Application ||--o{ RISK_PREDICTION : predicted_for
    RISK_PREDICTION ||--o{ SHAP_Explanation : explains
```

## 5.4 ERD-04: User/Support

Mục tiêu: phân quyền, audit, chat hỗ trợ vận hành.

```mermaid
erDiagram
    Role ||--o{ User : has
    User ||--o{ Audit_Log : performs
    User ||--o{ Chat_Session : starts
    Chat_Session ||--o{ Chat_History : contains
    User ||--o{ Chat_History : writes
```

## 6) Bảng nào không cần vẽ trong ERD nghiệp vụ chính

- `Portfolio_Snapshot`, `Portfolio_Risk_Summary`: bảng tổng hợp KPI; nên vẽ ở sơ đồ báo cáo riêng nếu cần.
- Tất cả bảng `stg_*`: staging/import; chỉ vẽ nếu làm tài liệu ETL/Data Warehouse.
- `Model_Version`: có thể để trong ERD Model Ops riêng, không bắt buộc trong sơ đồ vận hành tín dụng.

## 7) Cách vẽ thực tế (khuyến nghị)

- Chỉ hiển thị các cột: `PK`, `FK`, cột nghiệp vụ quan trọng (`status`, `amount`, `date`, `risk_level`).
- Tránh đưa toàn bộ cột để không làm rối sơ đồ.
- Mỗi sơ đồ giới hạn khoảng 8-15 bảng.
- Dùng màu/nhóm theo domain:
- Customer/Lending: xanh dương.
- Risk/ML: cam.
- Product Policy: xanh lá.
- Support: xám.
- Gắn nhãn quan hệ theo hành động nghiệp vụ (`submits`, `creates`, `scores`, `allocates`) để người nghiệp vụ đọc nhanh.

## 7.1 Hướng dẫn import vào MySQL Workbench

```bash
# 1. Mở MySQL Workbench
# 2. File → Open SQL Script → Chọn Database_MySQL_V1.sql
# 3. Chạy script (Ctrl+Shift+Enter)
# 4. Server → Data Export → Chọn CreditRiskDB → Export database
# 5. File → Create New EER Diagram (Edit → Preferences → Model → Diagram)
# 6. Database → Reverse Engineer → Chọn connection MySQL
# 7. Select schema CreditRiskDB → Chọn tất cả bảng
# 8. Hết! EER Diagram sẽ được tạo tự động
```

**Color coding cho ERD trong MySQL Workbench:**
- Customer/Lending: Xanh dương (#0099FF)
- Product Policy: Xanh lá (#00CC00)
- Risk/ML: Cam (#FF9900)
- Support/Chat: Xám (#CCCCCC)

## 8) Chênh lệch cần lưu ý giữa SQL Server và MySQL

### SQL Server (Cũ - giữ lại cho tham khảo)
- Sử dụng `[database]` syntax, `COLLATE SQL_Latin1_General_CP1_CI_AS`
- Auto-increment: `IDENTITY(1,1)`
- UUID: `uniqueidentifier`
- Type: `datetime2(7)`, `numeric`
- File: `apps/backend/docs/database/Database_full_V1.sql`

### MySQL (Mới - sử dụng cho production)
- Sử dụng backtick `` `database` `` syntax
- Auto-increment: `AUTO_INCREMENT`
- UUID: `CHAR(36)`
- Type: `DATETIME(6)`, `DECIMAL`
- Collation: `utf8mb4_unicode_ci` (hỗ trợ emoji, ký tự đặc biệt)
- File: `apps/backend/docs/database/Database_MySQL_V1.sql`

**Kết nối trong ứng dụng:**
- MySQL (mặc định): `mysql+pymysql://user:pass@localhost/CreditRiskDB`
- SQL Server (tùy chọn): `mssql+pyodbc://user:pass@server/CreditRiskDB?driver=ODBC+Driver+17+for+SQL+Server`

## 9) Khuyến nghị quản trị tài liệu

- ✅ **Chốt nguồn chuẩn**: `Database_MySQL_V1.sql` dùng cho production
- ✅ **Giữ lại**: `Database_full_V1.sql` (SQL Server) cho tham khảo/migration về sau
- ✅ **Cập nhật API connection**: Chuyển từ SQL Server sang MySQL trong `apps/backend/app/core/config.py`
- ✅ **Bổ sung changelog schema** theo phiên bản (`v1.0` - MySQL baseline, `v1.1` - Loan Classification changes)
- ✅ **Database Workbench**: Import `Database_MySQL_V1.sql` để visualize ERD trong MySQL Workbench
