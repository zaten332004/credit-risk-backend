#!/usr/bin/env python3
"""Insert sample users for each role"""
import pyodbc
from app.core.security import pwd_context
from datetime import datetime

# Connect to database
conn = pyodbc.connect(
    'Driver={ODBC Driver 18 for SQL Server};'
    'Server=DESKTOP-7EPLMS3\\SQLEXPRESS;'
    'Database=CreditRiskDB;'
    'UID=sa;'
    'PWD=12345;'
    'Encrypt=no;'
)

cursor = conn.cursor()

# Get all roles
print("📋 Available Roles:")
cursor.execute("SELECT role_id, role_name FROM Role ORDER BY role_id")
roles = cursor.fetchall()

if not roles:
    print("  (No roles found)")
else:
    for role_id, role_name in roles:
        print(f"  {role_id}. {role_name}")

# Sample users for each role
sample_users = [
    {
        "username": "admin",
        "email": "admin@creditrisk.com",
        "password": "admin123",
        "full_name": "Administrator",
        "role_name": "Admin"
    },
    {
        "username": "manager",
        "email": "manager@creditrisk.com",
        "password": "manager123",
        "full_name": "Portfolio Manager",
        "role_name": "Manager"
    },
    {
        "username": "analyst",
        "email": "analyst@creditrisk.com",
        "password": "analyst123",
        "full_name": "Risk Analyst",
        "role_name": "Analyst"
    },
    {
        "username": "viewer",
        "email": "viewer@creditrisk.com",
        "password": "viewer123",
        "full_name": "Data Viewer",
        "role_name": "Viewer"
    }
]

print("\n\n🔐 Inserting Sample Users:")
print("=" * 60)

for user in sample_users:
    # Find role_id
    cursor.execute("SELECT role_id FROM Role WHERE role_name = ?", (user["role_name"],))
    result = cursor.fetchone()
    
    if not result:
        print(f"⚠️  Role '{user['role_name']}' not found, skipping {user['username']}")
        continue
    
    role_id = result[0]
    
    # Hash password
    hashed_pwd = pwd_context.hash(user["password"])
    
    # Check if user already exists
    cursor.execute("SELECT user_id FROM [User] WHERE username = ? OR email = ?", 
                   (user["username"], user["email"]))
    existing = cursor.fetchone()
    
    if existing:
        print(f"⚠️  User '{user['username']}' already exists, skipping")
        continue
    
    # Insert user
    try:
        cursor.execute("""
            INSERT INTO [User] 
            (role_id, username, email, password, full_name, status, is_email_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            role_id,
            user["username"],
            user["email"],
            hashed_pwd,
            user["full_name"],
            "approved",  # Already approved
            1,  # Email verified
            datetime.utcnow()
        ))
        
        print(f"✅ {user['role_name']:10} | username: {user['username']:15} | password: {user['password']}")
        
    except Exception as e:
        print(f"❌ Error inserting {user['username']}: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ Sample users inserted successfully!")
print("\nYou can now login with these credentials:")
print("  admin    / admin123")
print("  manager  / manager123")
print("  analyst  / analyst123")
print("  viewer   / viewer123")
