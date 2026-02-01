#!/usr/bin/env python3
"""Check database tables and structure."""
import pyodbc

conn = pyodbc.connect(
    'Driver={ODBC Driver 18 for SQL Server};'
    'Server=DESKTOP-7EPLMS3\\SQLEXPRESS;'
    'Database=CreditRiskDB;'
    'UID=sa;'
    'PWD=12345;'
    'Encrypt=no;'
)

cursor = conn.cursor()

# Get all tables
cursor.execute("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'dbo'
    ORDER BY TABLE_NAME
""")

tables = [row[0] for row in cursor.fetchall()]
print(f"📊 Found {len(tables)} tables in database:")
for table in tables:
    print(f"  - {table}")

# Check User table structure
print("\n🔍 User table structure:")
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'User'
    ORDER BY ORDINAL_POSITION
""")

user_cols = cursor.fetchall()
if user_cols:
    for col in user_cols:
        print(f"  {col[0]}: {col[1]} (Nullable: {col[2]})")
else:
    print("  ⚠️  User table not found!")

conn.close()
