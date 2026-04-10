"""Verify sample users inserted into MySQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


with engine.connect() as connection:
    rows = connection.execute(
        text(
            """
            SELECT u.user_id, u.username, u.email, r.role_name, u.status
            FROM `User` u
            LEFT JOIN `Role` r ON u.role_id = r.role_id
            ORDER BY u.user_id DESC
            """
        )
    ).fetchall()

print("\nSample Users in Database:")
print("=" * 80)
print(f"{'ID':<4} | {'Username':<20} | {'Email':<35} | {'Role':<18} | {'Status':<10}")
print("-" * 80)
for row in rows:
    print(f"{row[0]:<4} | {row[1]:<20} | {row[2]:<35} | {(row[3] or ''):<18} | {(row[4] or ''):<10}")
print("=" * 80)
