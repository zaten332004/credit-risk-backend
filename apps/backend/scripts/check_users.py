"""Check existing users in the configured MySQL database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import text

from app.db.session import SessionLocal


def get_all_users():
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                SELECT u.user_id, u.username, u.email, u.full_name, u.status, r.role_name, u.password_hash
                FROM `User` u
                LEFT JOIN `Role` r ON u.role_id = r.role_id
                ORDER BY u.created_at DESC
                """
            )
        )
        return result.fetchall()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("EXISTING USERS IN DATABASE")
    print("=" * 80)

    users = get_all_users()
    if not users:
        print("No users found in database")
    else:
        print(f"\nFound {len(users)} user(s):\n")
        for idx, user in enumerate(users, start=1):
            user_id, username, email, full_name, status, role, password_hash = user
            print(f"{idx}. User ID: {user_id}")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Full Name: {full_name or 'N/A'}")
            print(f"   Status: {status or 'N/A'}")
            print(f"   Role: {role or 'N/A'}")
            print(f"   Password Hash: {password_hash[:30]}..." if password_hash else "   Password: Not set")
            print()

    print("=" * 80)
    print("\nTo login, use:")
    print("   POST /api/v1/auth/login")
    print("   Body: { 'username_or_email': '<username or email>', 'password': '<password>' }")
    print("\n   Or use Swagger UI: http://localhost:8000/docs")
    print("=" * 80)
