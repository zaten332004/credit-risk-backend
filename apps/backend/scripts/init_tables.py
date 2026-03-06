#!/usr/bin/env python3
"""
Script to create all database tables from SQLAlchemy models.
"""
import sys
sys.path.insert(0, '/'.join(__file__.split('/')[:-2]))

from app.db.session import Base, engine
from app.db.models import *

def init_db():
    """Create all tables."""
    try:
        print("🔨 Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        print("\nTables created:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
