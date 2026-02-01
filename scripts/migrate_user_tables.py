#!/usr/bin/env python3
"""Drop User_Registration table and recreate User table with new schema"""
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

print("🗑️  Dropping User_Registration table...")
try:
    cursor.execute("DROP TABLE IF EXISTS [User_Registration]")
    conn.commit()
    print("✓ Dropped User_Registration table")
except Exception as e:
    print(f"Note: {e}")

print("\n🔍 Dropping dependent FK constraints...")
try:
    # Get all tables that have FK to User
    cursor.execute("""
        SELECT TABLE_NAME, CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_TYPE = 'FOREIGN KEY' AND TABLE_CATALOG = 'CreditRiskDB'
    """)
    
    for table_name, fk_name in cursor.fetchall():
        try:
            print(f"  - Dropping FK {fk_name} in {table_name}")
            cursor.execute(f"ALTER TABLE [{table_name}] DROP CONSTRAINT [{fk_name}]")
            conn.commit()
        except Exception as e:
            print(f"    Skipped: {e}")

except Exception as e:
    print(f"Error: {e}")

print("\n🗑️  Dropping User table...")
try:
    cursor.execute("DROP TABLE IF EXISTS [User]")
    conn.commit()
    print("✓ Dropped User table")
except Exception as e:
    print(f"Error: {e}")

conn.close()
print("\n✅ Database cleanup complete!")
print("⚠️  Run init_tables.py to recreate tables with new schema")
