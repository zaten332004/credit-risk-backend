"""Create chat tables via SQLAlchemy for MySQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect

from app.core.config import settings
from app.db.models import Base  # noqa: F401


def create_chat_tables() -> bool:
    print("=" * 60)
    print("Creating Chat Tables")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL, echo=True)
    inspector = inspect(engine)
    print(f"\nExisting tables: {inspector.get_table_names()}")

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"Error creating tables: {exc}")
        return False

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables after create_all: {tables}")

    for table_name in ("Chat_Session", "Chat_History"):
        if table_name in tables:
            print(f"\n{table_name} columns:")
            for col in inspector.get_columns(table_name):
                print(f"  - {col['name']}: {col['type']}")

    print("\nChat tables setup completed.")
    return True


if __name__ == "__main__":
    ok = create_chat_tables()
    raise SystemExit(0 if ok else 1)
