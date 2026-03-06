#!/usr/bin/env python
"""
Script tạo Chat_Session và Chat_History tables
Chạy: python scripts/create_chat_tables.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from app.db.models import Base, ChatSessionDB, ChatHistoryDB
from app.core.config import settings

def create_chat_tables():
    """Tạo Chat_Session và Chat_History tables"""
    
    print("=" * 60)
    print("🚀 Creating Chat Tables")
    print("=" * 60)
    
    # Connect to database
    engine = create_engine(
        settings.DATABASE_URL,
        echo=True  # Show SQL statements
    )
    
    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"\n📊 Existing tables: {existing_tables}")
    
    # Create tables
    print("\n⏳ Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Verify
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    
    print(f"\n📋 New tables: {new_tables}")
    
    # Check Chat_Session columns
    if 'Chat_Session' in new_tables:
        columns = inspector.get_columns('Chat_Session')
        print("\n📌 Chat_Session columns:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
    
    # Check Chat_History columns
    if 'Chat_History' in new_tables:
        columns = inspector.get_columns('Chat_History')
        print("\n📌 Chat_History columns:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
    
    print("\n" + "=" * 60)
    print("✅ Chat tables setup completed!")
    print("=" * 60)
    
    # Print SQL for reference
    print("\n📝 SQL Statements (for reference):")
    print("\nChat_Session table:")
    print("""
    CREATE TABLE Chat_Session (
        session_id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        session_name VARCHAR(255),
        initial_context TEXT,
        is_active BIT DEFAULT 1,
        created_at DATETIME DEFAULT GETDATE(),
        closed_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES [User](user_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
    """)
    
    print("\nChat_History table:")
    print("""
    CREATE TABLE Chat_History (
        message_id INT PRIMARY KEY IDENTITY(1,1),
        session_id INT NOT NULL,
        user_id INT NOT NULL,
        role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
        content TEXT,
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (session_id) REFERENCES Chat_Session(session_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        FOREIGN KEY (user_id) REFERENCES [User](user_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
    """)
    
    return True

def verify_indexes():
    """Verify and create indexes"""
    
    print("\n" + "=" * 60)
    print("🔍 Verifying Indexes")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    # Check indexes
    if 'Chat_Session' in inspector.get_table_names():
        indexes = inspector.get_indexes('Chat_Session')
        print("\n📌 Chat_Session indexes:")
        if not indexes:
            print("  (No indexes yet, will be created on first query)")
        else:
            for idx in indexes:
                print(f"  - {idx['name']}: {idx['column_names']}")
    
    if 'Chat_History' in inspector.get_table_names():
        indexes = inspector.get_indexes('Chat_History')
        print("\n📌 Chat_History indexes:")
        if not indexes:
            print("  (No indexes yet, will be created on first query)")
        else:
            for idx in indexes:
                print(f"  - {idx['name']}: {idx['column_names']}")

def show_next_steps():
    """Show next steps"""
    
    print("\n" + "=" * 60)
    print("📋 Next Steps")
    print("=" * 60)
    print("""
1. ✅ Database tables created

2. 🔑 Set Gemini API Key:
   Windows (PowerShell):
     $env:GEMINI_API_KEY = "your-api-key"
   
   Linux/Mac:
     export GEMINI_API_KEY="your-api-key"
   
   Or add to .env:
     GEMINI_API_KEY=your-api-key

3. 🚀 Start backend server:
   python -m uvicorn app.main:app --reload

4. 📡 Test API endpoints:
   - Open http://localhost:8000/docs
   - Test POST /api/v1/ai-chat/start

5. 📚 Read documentation:
   - docs/GEMINI_AI_CHATBOT_SETUP.md
   
6. 🧪 Run test examples:
   - python scripts/test_ai_chat.py

7. 🔗 Integrate with frontend:
   - See API documentation
   - Connect Flutter/Web frontend
    """)

if __name__ == "__main__":
    try:
        # Create tables
        if create_chat_tables():
            # Verify indexes
            verify_indexes()
            
            # Show next steps
            show_next_steps()
            
            print("\n✅ Setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Setup failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
