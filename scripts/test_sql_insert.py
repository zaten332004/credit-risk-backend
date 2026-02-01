"""
Test direct SQL execution
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

# Read the SQL file
with open("../docs/INSERT_SAMPLE_USERS_PER_ROLE.sql", 'r', encoding='utf-8') as f:
    content = f.read()

print("SQL Content:")
print("="*80)
print(content)
print("="*80)

# Execute each statement
statements = content.split('GO\n')

with engine.connect() as connection:
    transaction = connection.begin()
    for i, stmt in enumerate(statements):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--') and not stmt.startswith('PRINT'):
            print(f"\nStatement {i}:")
            print(stmt[:100])
            try:
                result = connection.execute(text(stmt))
                print(f"Rows affected: {result.rowcount}")
            except Exception as e:
                print(f"Error: {e}")
    
    # Verify
    print("\n\nVerifying inserted data...")
    verify_query = text("SELECT COUNT(*) as cnt FROM [User] WHERE username LIKE '%_demo'")
    result = connection.execute(verify_query)
    count = result.scalar()
    print(f"Users with '_demo' in username: {count}")
    
    transaction.rollback()  # Rollback to preserve original state for now
