#!/usr/bin/env python3
"""Check all table structures and data types."""
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

for table in tables:
    if table.startswith('sys'):
        continue
    
    cursor.execute(f"""
        SELECT COLUMN_NAME, DATA_TYPE, COLUMNPROPERTY(OBJECT_ID('{table}'), COLUMN_NAME, 'IsIdentity') as IsIdentity
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
    """)
    
    cols = cursor.fetchall()
    print(f"\n{table}:")
    for col in cols:
        col_name, data_type, is_identity = col
        identity_mark = " (PK)" if is_identity else ""
        print(f"  {col_name}: {data_type}{identity_mark}")

conn.close()
