"""
Check existing users in database for login testing
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc://sa:12345@DESKTOP-7EPLMS3\\SQLEXPRESS/CreditRiskDB"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_all_users():
    """Get all users from database"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT u.user_id, u.username, u.email, u.full_name, u.status, r.role_name, u.password
            FROM [User] u
            LEFT JOIN [Role] r ON u.role_id = r.role_id
            ORDER BY u.created_at DESC
        """)
        result = db.execute(query)
        users = result.fetchall()
        return users
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("📋 EXISTING USERS IN DATABASE")
    print("=" * 80)
    
    users = get_all_users()
    
    if not users:
        print("❌ No users found in database")
    else:
        print(f"\n✅ Found {len(users)} user(s):\n")
        
        for i, user in enumerate(users, 1):
            user_id, username, email, full_name, status, role, password_hash = user
            print(f"{i}. User ID: {user_id}")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Full Name: {full_name or 'N/A'}")
            print(f"   Status: {status or 'N/A'}")
            print(f"   Role: {role or 'N/A'}")
            print(f"   Password Hash: {password_hash[:30]}..." if password_hash else "   Password: Not set")
            print()
    
    print("=" * 80)
    print("\n💡 To login, use:")
    print("   POST /api/v1/auth/login")
    print("   Body: { 'username': '<username or email>', 'password': '<password>' }")
    print("\n   Or use Swagger UI: http://localhost:8000/docs")
    print("=" * 80)
