#!/usr/bin/env python3
"""Check User_Registration table"""
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

# Get all registrations
print("📋 All User Registrations:")
cursor.execute("SELECT registration_id, username, email, status FROM User_Registration ORDER BY created_at DESC")

rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  ID: {row[0]}, Username: {row[1]}, Email: {row[2]}, Status: {row[3]}")
else:
    print("  (Empty)")

# Check specific user
print("\n🔍 Checking for 'zaten' / 'nhutpham0303@gmail.com':")
cursor.execute("""
    SELECT registration_id, username, email, status 
    FROM User_Registration 
    WHERE username = ? OR email = ?
""", ('zaten', 'nhutpham0303@gmail.com'))

result = cursor.fetchone()
if result:
    print(f"  FOUND: ID={result[0]}, Username={result[1]}, Email={result[2]}, Status={result[3]}")
else:
    print("  NOT FOUND in User_Registration")

# Check User table
print("\n🔍 Checking User table:")
cursor.execute("""
    SELECT user_id, username, email 
    FROM [User] 
    WHERE username = ? OR email = ?
""", ('zaten', 'nhutpham0303@gmail.com'))

result = cursor.fetchone()
if result:
    print(f"  FOUND: user_id={result[0]}, username={result[1]}, email={result[2]}")
else:
    print("  NOT FOUND in User table")

conn.close()
