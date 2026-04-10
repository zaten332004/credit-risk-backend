"""Dry-run test for executing the MySQL schema file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine

schema_path = Path(__file__).resolve().parents[1] / "docs" / "database" / "Database_MySQL_V1.sql"
content = schema_path.read_text(encoding="utf-8")

print("Schema preview:")
print("=" * 80)
print(content[:2000])
print("=" * 80)

with engine.connect() as connection:
    count = connection.execute(text("SELECT COUNT(*) FROM `User` WHERE username LIKE '%_demo'")).scalar()
    print(f"Users with '_demo' in username: {count}")
