"""List columns for all tables in the configured MySQL schema."""

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

    for table in tables:
        table_name = table[0]
        cols = connection.execute(
            text(
                """
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION
                """
            ),
            {"table_name": table_name},
        ).fetchall()

        print(f"\n{table_name}:")
        for col_name, data_type, column_key, extra in cols:
            marks = []
            if column_key == "PRI":
                marks.append("PK")
            if "auto_increment" in (extra or ""):
                marks.append("AUTO_INCREMENT")
            suffix = f" ({', '.join(marks)})" if marks else ""
            print(f"  {col_name}: {data_type}{suffix}")
