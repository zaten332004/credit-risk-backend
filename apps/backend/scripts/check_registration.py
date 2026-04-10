"""Inspect registration-related rows in the MySQL User table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine

USERNAME = "zaten"
EMAIL = "nhutpham0303@gmail.com"


with engine.connect() as connection:
    rows = connection.execute(
        text(
            """
            SELECT user_id, username, email, status, user_type, is_email_verified
            FROM `User`
            ORDER BY created_at DESC
            """
        )
    ).fetchall()
    print("All User registrations:")
    for row in rows:
        print(f"  ID={row[0]}, Username={row[1]}, Email={row[2]}, Status={row[3]}, Type={row[4]}, Verified={row[5]}")

    row = connection.execute(
        text(
            """
            SELECT user_id, username, email, status
            FROM `User`
            WHERE username = :username OR email = :email
            """
        ),
        {"username": USERNAME, "email": EMAIL},
    ).fetchone()
    print("\nLookup result:")
    print(row if row else "  NOT FOUND")
