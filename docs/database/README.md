# Database Documentation - Credit Risk System

## 📚 Tổng quan

Bộ tài liệu database cho Credit Risk Management System, bao gồm schema definition, migration guide, và documentation.

**Status**: ✅ MySQL v1.0 Ready for Production

---

## 📁 File Structure & Mô tả

### 🔴 Core Schema Files

#### `Database_MySQL_V1.sql` ⭐ **PRIMARY**
- **Loại**: SQL Script
- **Mục đích**: Schema định nghĩa chính cho MySQL 8.0+
- **Bảng**: 39 bảng với đầy đủ PK, FK, Index, Reference Data
- **Tính năng**:
  - ✅ Tất cả FK relationships
  - ✅ Cascade deletes nơi cần thiết
  - ✅ Tối ưu indexes cho performance
  - ✅ Reference data (Role, Risk_Group)
  - ✅ UTF-8 collation (utf8mb4_unicode_ci)
  - ✅ Comment cho SQL Server alternative
- **Cách dùng**: 
  ```bash
  mysql -u root -p < Database_MySQL_V1.sql
  ```

#### `Database_full_V1.sql` 
- **Loại**: SQL Script (Legacy)
- **Mục đích**: Schema SQL Server - Giữ lại để tham khảo
- **Ghi chú**: Nếu muốn quay lại SQL Server, sử dụng file này
- **Cách dùng**: Tham khảo, hoặc restore nếu cần migrate ngược lại

---

### 📖 Documentation Files

#### `MYSQL_MIGRATION_GUIDE.md` ⭐ **START HERE**
- **Loại**: Hướng dẫn chi tiết (Step-by-step)
- **Nội dung**:
  - ✅ Cài đặt MySQL & Workbench
  - ✅ Import schema (3 phương pháp)
  - ✅ Cập nhật app connection
  - ✅ Tạo EER Diagram
  - ✅ Troubleshooting & FAQ
  - ✅ Docker Compose example
- **Đối tượng**: Developers, DevOps, DBAs
- **Thời gian**: ~30 phút để hoàn thành

#### `ERD_DOCUMENTATION_V1.md`
- **Loại**: Tài liệu kiến trúc
- **Nội dung**:
  - ✅ 39 bảng & công dụng từng bảng
  - ✅ FK relationships chính
  - ✅ 4 ER Diagrams (Lending, Product, Risk/ML, Support)
  - ✅ **CẬP NHẬT**: Logic Loan Classification mới
  - ✅ MySQL Workbench import guide
- **Đối tượng**: Business Analysts, Architects, Developers

#### `CHANGELOG_MYSQL_V1.md`
- **Loại**: Tóm tắt thay đổi
- **Nội dung**:
  - ✅ Tóm tắt 3 thay đổi chính
  - ✅ File mới tạo & cập nhật
  - ✅ SQL Server config (commented)
  - ✅ Schema summary (39 bảng)
  - ✅ Key FK paths
  - ✅ Data types conversion table
  - ✅ Deployment checklist
  - ✅ Version history & roadmap
- **Đối tượng**: Project Managers, Release Managers

#### `QUICK_REFERENCE.md`
- **Loại**: Cheat sheet nhanh
- **Nội dung**:
  - ✅ Connection strings (Local, Docker, Cloud)
  - ✅ Essential tables & fields
  - ✅ Key relationships diagram
  - ✅ Risk Groups & Roles reference
  - ✅ 3 Common queries ví dụ
  - ✅ Useful commands (backup, restore)
  - ✅ Troubleshooting guide
  - ✅ File location reference
- **Đối tượng**: Developers (Daily reference)

#### `DATABASE_ARCHITECTURE.txt`
- **Loại**: Architecture overview (cũ)
- **Mục đích**: Tổng quan kiến trúc database
- **Ghi chú**: Đã update, có thể tham khảo

#### `database_architecture_guide.py`
- **Loại**: Python generator
- **Mục đích**: Tự động generate schema từ Python definitions
- **Ghi chú**: Tùy chọn, sử dụng nếu cần tự động hóa schema updates

---

## 🎯 Lựa chọn theo công việc

### 👨‍💻 Developers (Muốn sử dụng database)
1. **Đọc**: `QUICK_REFERENCE.md` (5 phút)
2. **Làm**: `MYSQL_MIGRATION_GUIDE.md` Section 1-2 (Import schema)
3. **Tham khảo**: `QUICK_REFERENCE.md` connection strings & queries

### 🏗️ Architects (Muốn hiểu logic)
1. **Đọc**: `CHANGELOG_MYSQL_V1.md` (10 phút)
2. **Đọc**: `ERD_DOCUMENTATION_V1.md` (20 phút)
3. **Tạo**: EER Diagram (Section 7 trong MYSQL_MIGRATION_GUIDE.md)

### 🔧 DevOps/DBA (Muốn deploy)
1. **Đọc**: `MYSQL_MIGRATION_GUIDE.md` Sections 1-5 (30 phút)
2. **Thực hiện**: Import & test connection
3. **Tham khảo**: Troubleshooting section
4. **Backup**: Tạo backup script

### 📊 Business Analysts
1. **Đọc**: `CHANGELOG_MYSQL_V1.md` (10 phút)
2. **Đọc**: Section "Loan Classification Logic" 
3. **Tham khảo**: `ERD_DOCUMENTATION_V1.md` Sections 3-4

### 👔 Project/Release Managers
1. **Đọc**: `CHANGELOG_MYSQL_V1.md` Deployment Checklist
2. **Tham khảo**: Version history
3. **Theo dõi**: Roadmap (v1.1, v1.2, v2.0)

---

## 🚀 Nhanh chóng bắt đầu (5 phút)

### 1️⃣ Install MySQL
```bash
# macOS
brew install mysql

# Windows
# Download từ https://dev.mysql.com/downloads/windows/installer/

# Linux
apt-get install mysql-server
```

### 2️⃣ Import Schema
```bash
mysql -u root -p < Database_MySQL_V1.sql
# Nhập password khi được hỏi
```

### 3️⃣ Kiểm tra
```bash
mysql -u root -p -e "USE CreditRiskDB; SHOW TABLES;"
# Kết quả: 39 bảng
```

### 4️⃣ Cập nhật App (Python)
```python
# File: apps/backend/app/core/config.py
DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/CreditRiskDB"
```

### 5️⃣ Install Dependencies
```bash
pip install pymysql sqlalchemy
```

✅ Done! Database sẵn sàng.

---

## 📊 Key Statistics

| Metric | Value |
|--------|-------|
| **Tổng bảng** | 39 |
| **FK relationships** | 35+ |
| **Indexes** | 15+ |
| **Collation** | utf8mb4_unicode_ci |
| **Engine** | InnoDB |
| **Tối ưu cho** | MySQL 8.0+ |

---

## 🔄 Migration Path

### Từ SQL Server sang MySQL
```
Database_full_V1.sql (SQL Server)
           ↓
    Manual conversion
           ↓
Database_MySQL_V1.sql (MySQL 8.0+)
```

### Nếu cần quay lại SQL Server
```
Database_MySQL_V1.sql (MySQL 8.0+)
           ↓
    Restore Database_full_V1.sql
           ↓
    Update connection string
           ↓
Database_full_V1.sql (SQL Server)
```

---

## 🔑 Điểm thay đổi quan trọng

### 1. Loan Classification Logic ⭐

**Cũ (SQL Server):**
```
Customer → Loan_Application → Loan_Facility (giải ngân) → Loan_Classification
```

**Mới (MySQL):**
```
Customer → Loan_Application (phân loại NGAY) → Loan_Classification → Risk_Group → Loan_Facility
```

### 2. Connection String

**Cũ**: `mssql+pyodbc://...`  
**Mới**: `mysql+pymysql://root:password@localhost:3306/CreditRiskDB`

### 3. SQL Syntax

**Cũ**: `[Table_Name]`, `IDENTITY`, `nvarchar(max)`  
**Mới**: `` `Table_Name` ``, `AUTO_INCREMENT`, `LONGTEXT`

---

## 📋 File Checklist

- [x] `Database_MySQL_V1.sql` - Schema MySQL ✅
- [x] `MYSQL_MIGRATION_GUIDE.md` - Setup guide ✅
- [x] `ERD_DOCUMENTATION_V1.md` - ER diagrams & logic ✅
- [x] `CHANGELOG_MYSQL_V1.md` - Changes summary ✅
- [x] `QUICK_REFERENCE.md` - Cheat sheet ✅
- [x] `DATABASE_ARCHITECTURE.txt` - Architecture (old) ✅
- [x] `database_architecture_guide.py` - Schema generator (optional) ✅

---

## 🆘 Cần giúp?

| Vấn đề | Giải pháp |
|--------|----------|
| Làm sao import schema? | Xem `MYSQL_MIGRATION_GUIDE.md` Section 2 |
| Connection string là gì? | Xem `QUICK_REFERENCE.md` Section "Connection String" |
| Các bảng là gì? | Xem `ERD_DOCUMENTATION_V1.md` Section 3 |
| Làm sao tạo EER Diagram? | Xem `MYSQL_MIGRATION_GUIDE.md` Section 5 |
| Có lỗi gì đó? | Xem `QUICK_REFERENCE.md` Section "Troubleshooting" |
| Muốn biết thay đổi? | Xem `CHANGELOG_MYSQL_V1.md` Section "Key Changes" |

---

## 📞 Contact

- **Database Questions**: Tham khảo `ERD_DOCUMENTATION_V1.md`
- **Setup Issues**: Tham khảo `MYSQL_MIGRATION_GUIDE.md` → Troubleshooting
- **Quick Answers**: Tham khảo `QUICK_REFERENCE.md`

---

## 📅 Version Info

**Current Version**: 1.0 - MySQL Baseline  
**Last Updated**: 2025-02-26  
**Status**: ✅ Ready for Production  

**Next Version**: 1.1 (Customer Data Encryption)  
**Planned**: 2025-03-26

---

**Ready to deploy!** 🚀
