"""
Create tables from SQLAlchemy models.
Command: python -m app.db.init_db
"""

from app.db.session import Base, engine
from app.db import models  # noqa: F401


def init_db():
    """
    Create all tables based on SQLAlchemy models.
    Note: this does not create the database schema itself.
    For MySQL, create `CreditRiskDB` first or import Database_MySQL_V1.sql.
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init_db()
