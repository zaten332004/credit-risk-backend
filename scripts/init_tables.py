"""Create all database tables from SQLAlchemy models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import *  # noqa: F401,F403
from app.db.session import Base, engine


def init_db():
    """Create all tables."""
    try:
        print("Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully.")
        print("\nTables created:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
    except Exception as exc:
        print(f"Error creating tables: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
