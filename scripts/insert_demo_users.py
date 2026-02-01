"""
Direct insert of sample users using SQLAlchemy
"""
import sys
sys.path.insert(0, '../')

from datetime import datetime
from sqlalchemy import text
from app.db.session import engine

def insert_demo_users():
    """Insert sample users for each role"""
    
    sql = """
    INSERT INTO [User] (role_id, username, email, password, created_at)
    VALUES
      (1, 'admin_demo', 'admin.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (2, 'manager_demo', 'manager.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (3, 'officer_demo', 'officer.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (4, 'customer_demo', 'customer.demo@email.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (5, 'analyst_demo', 'analyst.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME());
    """
    
    with engine.connect() as connection:
        try:
            # First, check if users already exist
            check_query = text("SELECT COUNT(*) as cnt FROM [User] WHERE username LIKE '%_demo'")
            result = connection.execute(check_query)
            existing_count = result.scalar()
            
            if existing_count > 0:
                print(f"⚠️  {existing_count} demo users already exist. Skipping insertion.")
                return
            
            # Insert new users
            connection.execute(text(sql))
            connection.commit()
            
            print("✓ Successfully inserted 5 sample users (1 for each role)!")
            
            # Display inserted users
            verify_query = text("""
                SELECT u.user_id, r.role_name, u.username, u.email
                FROM [User] u
                INNER JOIN Role r ON u.role_id = r.role_id
                WHERE u.username LIKE '%_demo'
                ORDER BY u.role_id
            """)
            
            result = connection.execute(verify_query)
            users = result.fetchall()
            
            print("\n" + "="*80)
            print("INSERTED USERS:")
            print("="*80)
            print(f"{'ID':<6} {'Role':<15} {'Username':<20} {'Email':<35}")
            print("-"*80)
            
            for user in users:
                print(f"{user[0]:<6} {user[1]:<15} {user[2]:<20} {user[3]:<35}")
            
            print("="*80)
            print("\n📋 LOGIN CREDENTIALS:")
            print("-"*80)
            creds = [
                ("Admin", "admin_demo", "Admin@123456"),
                ("Manager", "manager_demo", "Manager@123456"),
                ("Officer", "officer_demo", "Officer@123456"),
                ("Customer", "customer_demo", "Customer@123456"),
                ("Analyst", "analyst_demo", "Analyst@123456"),
            ]
            
            for role, user, pwd in creds:
                print(f"{role:<15} | Username: {user:<20} | Password: {pwd}")
            print("-"*80)
            
        except Exception as e:
            connection.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    insert_demo_users()
