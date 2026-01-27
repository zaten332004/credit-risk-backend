# Hướng dẫn Setup Database cho Credit Risk Backend

## Bước 1: Tạo Database Instance trong SQL Server

**Bạn PHẢI tạo database instance trước** (không thể tạo từ backend).

### Cách 1: Dùng SQL Server Management Studio (SSMS)

1. Mở **SQL Server Management Studio**.
2. Kết nối với SQL Server instance (ví dụ: `localhost\SQLEXPRESS`).
3. Right-click vào **Databases** → **New Database**.
4. Đặt tên: `CreditRiskDB`.
5. Click **OK**.

### Cách 2: Dùng SQL Script

Chạy script sau trong SSMS hoặc `sqlcmd`:

```sql
-- Tạo database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'CreditRiskDB')
BEGIN
    CREATE DATABASE CreditRiskDB;
END
GO

USE CreditRiskDB;
GO
```

---

## Bước 2: Cấu hình Connection String

Sửa file `app/db/session.py`:

```python
SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc://sa:YourPassword@localhost\\SQLEXPRESS/CreditRiskDB"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)
```

**Thay đổi:**
- `sa` → username SQL Server của bạn
- `YourPassword` → password
- `localhost\\SQLEXPRESS` → server name (có thể là `localhost`, `localhost\\MSSQLSERVER`, v.v.)
- `CreditRiskDB` → tên database bạn vừa tạo

---

## Bước 3: Tạo Tables từ Backend

Sau khi database instance đã tồn tại, bạn có thể tạo **tất cả tables** từ backend:

### Cách 1: Dùng script Python

```bash
python -m app.db.init_db
```

### Cách 2: Tạo tables thủ công trong code

Thêm vào `app/main.py` (chỉ chạy 1 lần khi khởi động lần đầu):

```python
from app.db.session import Base, engine
from app.db.models import CustomerDB, LoanDB, RiskScoreDB, UserDB, AlertDB

# Tạo tables (chỉ chạy 1 lần)
Base.metadata.create_all(bind=engine)
```

---

## Bước 4: Kiểm tra

Sau khi chạy script, mở SSMS và kiểm tra:

```sql
USE CreditRiskDB;
GO

-- Xem danh sách tables
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE';
```

Bạn sẽ thấy:
- `customers`
- `loans`
- `risk_scores`
- `users`
- `alerts`

---

## Lưu ý

- **Database instance** (`CreditRiskDB`) phải tạo trước trong SQL Server.
- **Tables** có thể tạo từ backend bằng SQLAlchemy.
- Nếu muốn quản lý migrations chuyên nghiệp, nên dùng **Alembic** (sẽ hướng dẫn sau).
