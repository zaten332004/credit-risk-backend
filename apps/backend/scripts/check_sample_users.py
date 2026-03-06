#!/usr/bin/env python3
"""Verify sample users inserted"""
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
cursor.execute("""
    SELECT user_id, username, email, r.role_name, status 
    FROM [User] u 
    LEFT JOIN Role r ON u.role_id = r.role_id 
    ORDER BY user_id DESC
""")

print("\n📊 Sample Users in Database:")
print("=" * 80)
print(f"{'ID':<4} | {'Username':<15} | {'Email':<30} | {'Role':<10} | {'Status':<10}")
print("-" * 80)

for row in cursor.fetchall():
    user_id, username, email, role, status = row
    print(f"{user_id:<4} | {username:<15} | {email:<30} | {role:<10} | {status:<10}")

print("=" * 80)
conn.close()
