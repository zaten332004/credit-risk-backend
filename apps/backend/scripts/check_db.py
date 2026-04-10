"""Quick MySQL connectivity and table check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


with engine.connect() as connection:
    tables = connection.execute(
        text(
            """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
            """
        )
    ).fetchall()

    print(f"Found {len(tables)} tables in database:")
    for table in tables:
        print(f"  - {table[0]}")

    print("\nUser table structure:")
    user_cols = connection.execute(
        text(
            """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'User'
            ORDER BY ORDINAL_POSITION
            """
        )
    ).fetchall()
    if user_cols:
        for col in user_cols:
            print(f"  {col[0]}: {col[1]} (Nullable: {col[2]})")
    else:
        print("  User table not found")
