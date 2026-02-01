"""
Check if users already exist
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

with engine.connect() as connection:
    # Check all demo users
    query = text("""
        SELECT user_id, role_id, username, email
        FROM [User]
        ORDER BY user_id DESC
    """)
    
    result = connection.execute(query)
    users = result.fetchall()
    
    print("Last 10 users in database:")
    print("="*80)
    for user in users[:10]:
        print(f"ID: {user[0]}, Role: {user[1]}, Username: {user[2]}, Email: {user[3]}")
    
    print(f"\nTotal users: {len(users)}")
    
    # Check demo users specifically
    demo_query = text("""
        SELECT user_id, role_id, username, email
        FROM [User]
        WHERE username LIKE '%_demo'
    """)
    
    demo_result = connection.execute(demo_query)
    demo_users = demo_result.fetchall()
    
    print(f"\nDemo users found: {len(demo_users)}")
    for user in demo_users:
        print(f"  {user[2]} ({user[3]})")
