"""
Script to execute SQL commands directly
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

def execute_sql_file(filepath):
    """Execute SQL commands directly"""
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by GO statement for SQL Server
    statements = sql_content.split('GO\n')
    
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        print(f"Executing: {statement[:60]}...")
                        connection.execute(text(statement))
                    except Exception as e:
                        print(f"Error executing statement: {e}")
                        raise
            transaction.commit()
            print("✓ All statements executed successfully!")
        except Exception as e:
            transaction.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    import os
    filepath = os.path.join(os.path.dirname(__file__), "../docs/INSERT_SAMPLE_USERS_PER_ROLE.sql")
    print("Executing SQL script...")
    execute_sql_file(filepath)
    print("✓ Script execution completed!")
