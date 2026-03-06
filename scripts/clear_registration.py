#!/usr/bin/env python3
"""Clear old registration for testing"""
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

# Delete old registration
print("🗑️  Deleting old registration for 'zaten'...")
cursor.execute("DELETE FROM User_Registration WHERE username = ?", ('zaten',))
conn.commit()

print("✅ Deleted!")

# Verify
cursor.execute("SELECT COUNT(*) FROM User_Registration WHERE username = ?", ('zaten',))
count = cursor.fetchone()[0]
print(f"Remaining 'zaten' records: {count}")

conn.close()
