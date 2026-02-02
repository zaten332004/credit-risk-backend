# 📋 Sample Users Created - One for Each Role

Dữ liệu mẫu đã được insert thành công cho mỗi role. Mỗi role có 1 người dùng mẫu.

## ✅ Dữ Liệu Đã Insert

| ID | Role | Username | Email | Mật Khẩu |
|-------|----------|-----------|----------|-----------|
| - | Admin | `admin_demo` | admin.demo@creditbank.com | `Admin@123456` |
| - | Manager | `manager_demo` | manager.demo@creditbank.com | `Manager@123456` |
| - | Officer | `officer_demo` | officer.demo@creditbank.com | `Officer@123456` |
| - | Customer | `customer_demo` | customer.demo@email.com | `Customer@123456` |
| - | Analyst | `analyst_demo` | analyst.demo@creditbank.com | `Analyst@123456` |

## 🔐 Thông Tin Đăng Nhập

```
Admin:    admin_demo / Admin@123456
Manager:  manager_demo / Manager@123456
Officer:  officer_demo / Officer@123456
Customer: customer_demo / Customer@123456
Analyst:  analyst_demo / Analyst@123456
```

## 📁 Files Tạo Ra

1. **`docs/INSERT_SAMPLE_USERS_PER_ROLE.sql`** - Script SQL để insert dữ liệu
2. **`scripts/insert_demo_users.py`** - Script Python để insert dữ liệu trực tiếp
3. **`scripts/verify_sample_users.py`** - Script để xác minh dữ liệu đã insert
4. **`scripts/check_demo_users.py`** - Script để kiểm tra các user demo

## 🚀 Cách Sử Dụng

### Chạy script Python:
```powershell
python scripts/insert_demo_users.py
```

### Hoặc chạy SQL trực tiếp:
```sql
-- Chạy file docs/INSERT_SAMPLE_USERS_PER_ROLE.sql trong SQL Server Management Studio
```

## 📝 Ghi Chú

- Mật khẩu được hash bằng bcrypt
- Hash được sử dụng: `$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga` (password mẫu)
- Các user này có thể được sử dụng để test các API endpoints
- Trạng thái mặc định là `pending` (chưa xác minh email)
