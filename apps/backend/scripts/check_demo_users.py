"""Check demo users in MySQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


with engine.connect() as connection:
    users = connection.execute(
        text(
            """
            SELECT user_id, role_id, username, email
            FROM `User`
            ORDER BY user_id DESC
            """
        )
    ).fetchall()

    print("Last 10 users in database:")
    print("=" * 80)
    for user in users[:10]:
        print(f"ID: {user[0]}, Role: {user[1]}, Username: {user[2]}, Email: {user[3]}")

    print(f"\nTotal users: {len(users)}")

    demo_users = connection.execute(
        text(
            """
            SELECT user_id, role_id, username, email
            FROM `User`
            WHERE username LIKE '%_demo'
            """
        )
    ).fetchall()

    print(f"\nDemo users found: {len(demo_users)}")
    for user in demo_users:
        print(f"  {user[2]} ({user[3]})")
