"""
Insert sample users for the 4 roles in the current database
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

def insert_sample_users():
    """Insert sample users for each role"""
    
    # SQL to insert users for 4 roles: Admin, Manager, Analyst, Viewer
    sql = """
    INSERT INTO [User] (role_id, username, email, password, created_at)
    VALUES
      (1, 'admin_demo', 'admin.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (2, 'manager_demo', 'manager.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (3, 'analyst_demo', 'analyst.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
      (4, 'viewer_demo', 'viewer.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME());
    """
    
    with engine.connect() as connection:
        try:
            # Check if demo users already exist
            check_query = text("SELECT COUNT(*) as cnt FROM [User] WHERE username LIKE '%_demo'")
            result = connection.execute(check_query)
            existing_count = result.scalar()
            
            if existing_count > 0:
                print(f"⚠️  {existing_count} demo user(s) already exist. Skipping insertion.")
                return
            
            # Insert new users
            connection.execute(text(sql))
            connection.commit()
            
            print("✓ Successfully inserted 4 sample users (1 for each role)!")
            print()
            
            # Display inserted users
            verify_query = text("""
                SELECT u.user_id, r.role_name, u.username, u.email, FORMAT(u.created_at, 'yyyy-MM-dd HH:mm:ss') as created
                FROM [User] u
                INNER JOIN Role r ON u.role_id = r.role_id
                WHERE u.username LIKE '%_demo'
                ORDER BY u.role_id
            """)
            
            result = connection.execute(verify_query)
            users = result.fetchall()
            
            print("=" * 90)
            print("INSERTED SAMPLE USERS:")
            print("=" * 90)
            print(f"{'ID':<6} {'Role':<15} {'Username':<20} {'Email':<35} {'Created':<20}")
            print("-" * 90)
            
            for user in users:
                print(f"{user[0]:<6} {user[1]:<15} {user[2]:<20} {user[3]:<35} {user[4]:<20}")
            
            print("=" * 90)
            print()
            print("📋 LOGIN CREDENTIALS:")
            print("-" * 90)
            creds = [
                ("Admin", "admin_demo", "Admin@123456"),
                ("Manager", "manager_demo", "Manager@123456"),
                ("Analyst", "analyst_demo", "Analyst@123456"),
                ("Viewer", "viewer_demo", "Viewer@123456"),
            ]
            
            for role, user, pwd in creds:
                print(f"{role:<15} | Username: {user:<20} | Password: {pwd}")
            print("-" * 90)
            
        except Exception as e:
            connection.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    insert_sample_users()
