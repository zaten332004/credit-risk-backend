# MySQL Migration Guide - Credit Risk System

## Tổng quan sự thay đổi

Hệ thống đã được chuyển đổi từ **SQL Server 2025** sang **MySQL 8.0+** để dễ dàng deploy trên các nền tảng khác nhau (cloud, on-premise).

### Chính sách thay đổi Database

| Tiêu chí | Chi tiết |
|---------|---------|
| **Database Chính** | MySQL 8.0+ (`Database_MySQL_V1.sql`) |
| **Database Cũ** | SQL Server 2025 (`Database_full_V1.sql`) - Giữ lại để tham khảo |
| **Việc migration** | Chạy script MySQL trực tiếp, không cần migrate dữ liệu cũ |
| **Collation** | `utf8mb4_unicode_ci` (hỗ trợ tiếng Việt, emoji) |
| **Auto-increment** | Sử dụng `AUTO_INCREMENT` thay vì `IDENTITY` |

---

## 1) Chuẩn bị MySQL Workbench

### Yêu cầu hệ thống

```bash
# 1. Cài đặt MySQL Server 8.0+
# Windows: Tải từ https://dev.mysql.com/downloads/windows/installer/
# macOS: brew install mysql
# Linux: apt-get install mysql-server (Ubuntu) hoặc yum install mysql (CentOS)

# 2. Cài đặt MySQL Workbench
# https://dev.mysql.com/downloads/workbench/

# 3. Kiểm tra cài đặt
mysql --version
mysql -u root -p
```

### Kết nối MySQL Workbench

```
1. Mở MySQL Workbench
2. MySQL Connections → + (New Connection)
3. Connection Name: Credit Risk Dev
4. Connection Method: Standard (TCP/IP)
5. Hostname: localhost
6. Port: 3306
7. Username: root
8. Password: <nhập password>
9. Bấm "Test Connection" → Bấm "OK"
```

---

## 2) Import Database Schema

### Phương pháp 1: SQL Script (Khuyên dùng)

```bash
# Terminal / PowerShell
mysql -u root -p < Database_MySQL_V1.sql

# Nhập password root khi được hỏi
# Nếu thành công: "Query OK, X rows affected"
```

### Phương pháp 2: MySQL Workbench GUI

```
1. Mở MySQL Workbench
2. File → Open SQL Script
3. Chọn: apps/backend/docs/database/Database_MySQL_V1.sql
4. Nhấn Ctrl+Shift+Enter (hoặc Lightning icon)
5. Chọn connection "Credit Risk Dev"
6. Chạy script
```

### Phương pháp 3: Sử dụng Database schema creation wizard

```
1. MySQL Workbench → Create New Schema
2. Name: CreditRiskDB
3. Collation: utf8mb4_unicode_ci
4. Chạy từng CREATE TABLE command từ script
```

---

## 3) Kiểm tra Import thành công

```sql
-- Chạy lệnh này để xác nhận
USE CreditRiskDB;
SHOW TABLES;
-- Kết quả: Phải có 39 bảng

-- Kiểm tra FK
SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME 
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
WHERE CONSTRAINT_SCHEMA = 'CreditRiskDB';

-- Kiểm tra dữ liệu mẫu
SELECT * FROM Risk_Group;
-- Kết quả: 4 bảng rủi ro (Group 1-4)

SELECT * FROM Role;
-- Kết quả: 5 vai trò
```

---

## 4) Cập nhật Application Connection

### Python Backend

Trong file `apps/backend/app/core/config.py`:

```python
# ❌ CŨ - SQL Server (commented)
# DATABASE_URL = "mssql+pyodbc://user:password@SERVER/CreditRiskDB?driver=ODBC+Driver+17+for+SQL+Server"

# ✅ MỚI - MySQL
DATABASE_URL = "mysql+pymysql://root:your_password@localhost:3306/CreditRiskDB"

# Hoặc sử dụng environment variable
import os
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:password@localhost:3306/CreditRiskDB"
)
```

### Cài đặt Python dependencies

```bash
# Trong backend folder
pip install mysql-connector-python
pip install pymysql
pip install sqlalchemy
pip install alembic
```

### Docker Compose (Nếu dùng container)

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: CreditRiskDB
    ports:
      - "3306:3306"
    volumes:
      - ./apps/backend/docs/database/Database_MySQL_V1.sql:/docker-entrypoint-initdb.d/init.sql
      - mysql_data:/var/lib/mysql

  backend:
    build: ./apps/backend
    environment:
      DATABASE_URL: "mysql+pymysql://root:root_password@mysql:3306/CreditRiskDB"
    ports:
      - "8000:8000"
    depends_on:
      - mysql

volumes:
  mysql_data:
```

---

## 5) EER Diagram trong MySQL Workbench

### Tạo EER Diagram tự động

```
1. MySQL Workbench → Mở connection CreditRiskDB
2. Database → Reverse Engineer
3. Chọn CreditRiskDB
4. Chọn tất cả bảng
5. Finish → EER Diagram sẽ được tạo
```

### Format EER Diagram

Diagram sẽ tự động hiển thị:
- Foreign Key relationships (mũi tên)
- Primary Key (khóa vàng)
- Data types & constraints
- Indexes

### Export EER Diagram

```
1. Chuột phải trên diagram
2. Export as PNG / PDF / ...
3. Lưu vào: apps/backend/docs/diagrams/
```

---

## 6) Schema Thay đổi từ SQL Server → MySQL

### Data Types Mapping

| SQL Server | MySQL | Ghi chú |
|-----------|-------|---------|
| `BIGINT IDENTITY` | `BIGINT AUTO_INCREMENT` | PK tự tăng |
| `INT IDENTITY` | `INT AUTO_INCREMENT` | - |
| `nvarchar(n)` | `VARCHAR(n)` | UTF-8 mặc định |
| `datetime2(7)` | `DATETIME(6)` | 6 chữ số precision |
| `numeric(18,2)` | `NUMERIC(18,2)` hoặc `DECIMAL(18,2)` | - |
| `bit` | `BOOLEAN` | - |
| `uniqueidentifier` | `CHAR(36)` | UUID format |
| `COLLATE SQL_Latin1...` | `COLLATE utf8mb4_unicode_ci` | Unicode support |
| `nvarchar(max)` | `LONGTEXT` | Hỗ trợ dài tối đa |
| `text` | `LONGTEXT` | - |

### Syntax Thay đổi

```sql
-- ❌ SQL Server
[dbo].[Table_Name]
IDENTITY(1,1)
datetime2(7)
COLLATE SQL_Latin1_General_CP1_CI_AS

-- ✅ MySQL
`Table_Name`
AUTO_INCREMENT
DATETIME(6)
COLLATE utf8mb4_unicode_ci
```

### Foreign Key Cascades

```sql
-- ❌ SQL Server
ALTER TABLE [dbo].[Customer_Employment] WITH CHECK ADD CONSTRAINT [FK] 
FOREIGN KEY([customer_id]) REFERENCES [dbo].[Customer]([customer_id])
ON DELETE CASCADE

-- ✅ MySQL
ALTER TABLE `Customer_Employment` ADD CONSTRAINT `FK_Employment_Customer_Cascade`
FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`)
ON DELETE CASCADE;
```

---

## 7) Logic Thay đổi - Loan Classification

### Cấu trúc cũ (SQL Server)

```
Customer (submit) → Loan_Application 
                  → Loan_Facility (giải ngân)
                  → Loan_Classification (phân loại sau)
```

### Cấu trúc mới (MySQL)

```
Customer (submit) → Loan_Application (phân loại NGAY TẠI ĐÂY)
                  → Loan_Classification (với application_id)
                  → Loan_Facility (nếu được duyệt)
```

### Bảng liên quan

```sql
-- Loan_Classification có 2 FK:
- application_id (REQUIRED) → Loan_Application
- facility_id (NULLABLE) → Loan_Facility

-- Ý nghĩa:
- application_id: Phân loại rủi ro ban đầu khi nộp đơn
- facility_id: Tracking phân loại trạng thái sau khi giải ngân
```

### SQL Query ví dụ

```sql
-- Lấy các đơn vay đang chờ duyệt
SELECT 
  a.application_id,
  c.full_name,
  a.loan_amount,
  lc.group_id,
  rg.group_name,
  lc.classification_status
FROM Loan_Application a
JOIN Customer c ON a.customer_id = c.customer_id
LEFT JOIN Loan_Classification lc ON a.application_id = lc.application_id
LEFT JOIN Risk_Group rg ON lc.group_id = rg.group_id
WHERE a.loan_status = 'PENDING';

-- Lấy các khoản vay được duyệt
SELECT 
  f.facility_id,
  c.full_name,
  f.approved_amount,
  lc.group_id,
  rg.risk_level
FROM Loan_Facility f
JOIN Loan_Application a ON f.application_id = a.application_id
JOIN Customer c ON f.customer_id = c.customer_id
LEFT JOIN Loan_Classification lc ON f.application_id = lc.application_id
LEFT JOIN Risk_Group rg ON lc.group_id = rg.group_id
WHERE f.status = 'ACTIVE';
```

---

## 8) Troubleshooting

### Lỗi: "Unknown database 'CreditRiskDB'"

```bash
# Kiểm tra xem database đã tạo chưa
mysql -u root -p -e "SHOW DATABASES;"

# Nếu chưa, chạy lại script
mysql -u root -p < Database_MySQL_V1.sql
```

### Lỗi: "Access denied for user 'root'@'localhost'"

```bash
# Reset MySQL password
# Windows
mysql -u root --skip-password

# macOS/Linux
sudo mysql -u root
# Trong MySQL shell:
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

### Lỗi: "Foreign key constraint failed"

```sql
-- Kiểm tra FK
SHOW CREATE TABLE Loan_Classification;

-- Disable/Enable FK tạm thời
SET FOREIGN_KEY_CHECKS=0;
-- ... chạy queries ...
SET FOREIGN_KEY_CHECKS=1;
```

### Lỗi: "pymysql" module not found

```bash
pip install pymysql
# hoặc
pip install mysql-connector-python
```

---

## 9) File tham khảo

| File | Mục đích |
|------|---------|
| `Database_MySQL_V1.sql` | ✅ Schema MySQL chính - SỬ DỤNG |
| `Database_full_V1.sql` | SQL Server schema - Tham khảo |
| `ERD_DOCUMENTATION_V1.md` | Tài liệu ERD & logic - Cập nhật |
| `database_architecture_guide.py` | Generator schema từ Python |
| `DATABASE_ARCHITECTURE.txt` | Tổng quan kiến trúc |

---

## 10) Bước tiếp theo

- [ ] Chạy `Database_MySQL_V1.sql` trong MySQL
- [ ] Kiểm tra tables & FKs
- [ ] Cập nhật `DATABASE_URL` trong app config
- [ ] Test connection từ Python backend
- [ ] Seed dữ liệu mẫu (nếu cần)
- [ ] Generate EER Diagram trong MySQL Workbench
- [ ] Deploy lên production

---

**Liên hệ**: Nếu có câu hỏi, tham khảo `ERD_DOCUMENTATION_V1.md` hoặc liên hệ team backend.
