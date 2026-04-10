"""Delete a user registration record from the MySQL User table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine

USERNAME = "zaten"


with engine.connect() as connection:
    connection.execute(text("DELETE FROM `User` WHERE username = :username"), {"username": USERNAME})
    connection.commit()

    remaining = connection.execute(
        text("SELECT COUNT(*) FROM `User` WHERE username = :username"),
        {"username": USERNAME},
    ).scalar()
    print(f"Remaining '{USERNAME}' records: {remaining}")
