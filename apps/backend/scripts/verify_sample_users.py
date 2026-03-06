"""
Script to verify inserted sample users
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

def verify_users():
    """Verify inserted sample users"""
    
    with engine.connect() as connection:
        query = text("""
            SELECT u.user_id, r.role_name, u.username, u.email
            FROM [User] u
            INNER JOIN Role r ON u.role_id = r.role_id
            WHERE u.username LIKE '%_demo'
            ORDER BY u.role_id;
        """)
        
        result = connection.execute(query)
        users = result.fetchall()
        
        print("="*80)
        print("SAMPLE USERS INSERTED SUCCESSFULLY")
        print("="*80)
        print(f"{'ID':<6} {'Role':<15} {'Username':<20} {'Email':<35}")
        print("-"*80)
        
        for user in users:
            print(f"{user[0]:<6} {user[1]:<15} {user[2]:<20} {user[3]:<35}")
        
        print("="*80)
        print(f"Total users inserted: {len(users)}")
        print("="*80)
        
        print("\n📋 LOGIN CREDENTIALS:")
        print("-"*80)
        credentials = [
            ("Admin", "admin_demo", "Admin@123456"),
            ("Manager", "manager_demo", "Manager@123456"),
            ("Officer", "officer_demo", "Officer@123456"),
            ("Customer", "customer_demo", "Customer@123456"),
            ("Analyst", "analyst_demo", "Analyst@123456"),
        ]
        
        for role, username, password in credentials:
            print(f"{role:<15} | Username: {username:<20} | Password: {password}")
        
        print("-"*80)

if __name__ == "__main__":
    verify_users()
