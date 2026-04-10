"""Verify inserted sample users in MySQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def verify_users():
    with engine.connect() as connection:
        users = connection.execute(
            text(
                """
                SELECT u.user_id, r.role_name, u.username, u.email
                FROM `User` u
                INNER JOIN `Role` r ON u.role_id = r.role_id
                WHERE u.username LIKE '%_demo'
                ORDER BY u.role_id
                """
            )
        ).fetchall()

    print("=" * 80)
    print("SAMPLE USERS INSERTED SUCCESSFULLY")
    print("=" * 80)
    print(f"{'ID':<6} {'Role':<18} {'Username':<22} {'Email':<35}")
    print("-" * 80)
    for user in users:
        print(f"{user[0]:<6} {user[1]:<18} {user[2]:<22} {user[3]:<35}")
    print("=" * 80)
    print(f"Total users inserted: {len(users)}")


if __name__ == "__main__":
    verify_users()
