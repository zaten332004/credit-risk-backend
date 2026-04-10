# Quick Reference - MySQL Database

## 🔌 Connection String

```python
# Development (Local MySQL)
DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/CreditRiskDB"

# Docker
DATABASE_URL = "mysql+pymysql://root:password@mysql:3306/CreditRiskDB"

# AWS RDS
DATABASE_URL = "mysql+pymysql://admin:password@credit-risk-db.xxxxx.us-east-1.rds.amazonaws.com:3306/CreditRiskDB"
```

## 📊 Essential Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `Customer` | Khách hàng | customer_id, full_name, credit_score |
| `Loan_Application` | Đơn vay | application_id, customer_id, loan_amount |
| `Loan_Classification` | Phân loại rủi ro | classification_id, application_id (NEW!), group_id |
| `Loan_Facility` | Khoản vay được duyệt | facility_id, application_id, approved_amount |
| `Risk_Group` | Danh mục rủi ro | group_id (1-4), provision_rate |
| `User` | Người dùng hệ thống | user_id, role_id |
| `Role` | Vai trò | role_id (1-5) |

## 🔑 Key Relationships

```
Customer → Loan_Application → Loan_Classification → Risk_Group
                ↓
         Loan_Facility → Loan_Payment
                ↓
         Loan_Delinquency
```

## 📋 Risk Groups (Risk_Group)

| group_id | Tên | days_overdue | provision_rate |
|----------|-----|-------------|----------------|
| 1 | Nhóm 1 - Tốt | 0 | 0% |
| 2 | Nhóm 2 - Bình thường | 1-29 | 5% |
| 3 | Nhóm 3 - Theo dõi | 30-89 | 20% |
| 4 | Nhóm 4 - Rủi ro cao | 90+ | 50% |

## 👤 Roles (Role)

| role_id | Tên |
|---------|-----|
| 1 | Admin |
| 2 | Risk Officer |
| 3 | Loan Officer |
| 4 | Customer |
| 5 | Audit |

## 🔍 Common Queries

### Lấy danh sách đơn vay đang chờ duyệt
```sql
SELECT a.application_id, c.full_name, a.loan_amount, lc.group_id
FROM Loan_Application a
JOIN Customer c ON a.customer_id = c.customer_id
LEFT JOIN Loan_Classification lc ON a.application_id = lc.application_id
WHERE a.loan_status = 'PENDING';
```

### Lấy khoản vay quá hạn
```sql
SELECT f.facility_id, c.full_name, ld.days_past_due, ld.overdue_amount
FROM Loan_Facility f
JOIN Customer c ON f.customer_id = c.customer_id
JOIN Loan_Delinquency ld ON f.facility_id = ld.facility_id
WHERE ld.days_past_due > 0
ORDER BY ld.days_past_due DESC;
```

### Thống kê theo nhóm rủi ro
```sql
SELECT rg.group_id, rg.group_name, COUNT(*) as count, 
       SUM(f.approved_amount) as total_exposure
FROM Risk_Group rg
LEFT JOIN Loan_Classification lc ON rg.group_id = lc.group_id
LEFT JOIN Loan_Facility f ON lc.facility_id = f.facility_id
GROUP BY rg.group_id
ORDER BY rg.group_id;
```

## 🛠️ Useful Commands

```bash
# Kết nối MySQL
mysql -u root -p -h localhost

# Import schema
mysql -u root -p < Database_MySQL_V1.sql

# Backup database
mysqldump -u root -p CreditRiskDB > backup.sql

# Restore database
mysql -u root -p CreditRiskDB < backup.sql

# Check database size
SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'CreditRiskDB'
ORDER BY (data_length + index_length) DESC;
```

## 🚨 Troubleshooting

| Lỗi | Giải pháp |
|-----|----------|
| "Unknown database" | Chạy script: `mysql -u root -p < Database_MySQL_V1.sql` |
| "Access denied" | Kiểm tra username/password, run: `mysql -u root -p` |
| "Foreign key constraint" | Kiểm tra FK: `SHOW CREATE TABLE table_name;` |
| "Connection timeout" | Kiểm tra MySQL service chạy: `sudo service mysql status` |
| "pymysql not found" | Cài: `pip install pymysql` |

## 📁 Important Files Location

```
apps/backend/docs/database/
├── Database_MySQL_V1.sql              ← Schema chính
├── Database_full_V1.sql               ← SQL Server (reference)
├── ERD_DOCUMENTATION_V1.md            ← ER diagram & logic
├── MYSQL_MIGRATION_GUIDE.md           ← Setup guide
├── CHANGELOG_MYSQL_V1.md              ← Changes summary
└── QUICK_REFERENCE.md                 ← File này
```

## 🔄 Migration from SQL Server

Nếu cần quay lại SQL Server:
1. Restore từ `Database_full_V1.sql`
2. Cập nhật connection: `mssql+pyodbc://...`
3. Không cần thay đổi code (SQLAlchemy handles both)

## ⚡ Performance Tips

- Index trên FK columns: ✅ Đã tạo
- Collation `utf8mb4`: ✅ Tối ưu cho Việt Nam
- AUTO_INCREMENT: ✅ Không cần reset
- Connection pooling: Dùng `pool_size=10`, `pool_pre_ping=True`

## 📞 Quick Contacts

- Database Schema Questions → Xem `ERD_DOCUMENTATION_V1.md`
- Setup Issues → Xem `MYSQL_MIGRATION_GUIDE.md`
- Connection Problems → Xem `QUICK_REFERENCE.md` section Troubleshooting

---

Last Updated: 2025-02-26
