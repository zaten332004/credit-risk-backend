"""
Check current database structure and data
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text, inspect
from app.db.session import engine

def check_database():
    """Check database structure and data"""
    
    with engine.connect() as connection:
        # 1. Get database info
        print("="*80)
        print("DATABASE INFORMATION")
        print("="*80)
        
        db_query = text("SELECT DB_NAME() as DatabaseName, @@VERSION as SQLVersion")
        result = connection.execute(db_query)
        row = result.fetchone()
        print(f"Database Name: {row[0]}")
        print(f"SQL Server Version: {row[1][:50]}...")
        print()
        
        # 2. Check tables
        print("="*80)
        print("TABLES IN DATABASE")
        print("="*80)
        
        tables_query = text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        result = connection.execute(tables_query)
        tables = result.fetchall()
        print(f"Total tables: {len(tables)}\n")
        for table in tables:
            print(f"  • {table[0]}")
        print()
        
        # 3. Check Role table
        print("="*80)
        print("ROLE TABLE")
        print("="*80)
        
        role_query = text("SELECT role_id, role_name, description FROM Role ORDER BY role_id")
        result = connection.execute(role_query)
        roles = result.fetchall()
        print(f"Total roles: {len(roles)}\n")
        for role in roles:
            print(f"  ID: {role[0]}, Name: {role[1]}, Desc: {role[2]}")
        print()
        
        # 4. Check User table structure
        print("="*80)
        print("USER TABLE STRUCTURE")
        print("="*80)
        
        columns_query = text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'User'
            ORDER BY ORDINAL_POSITION
        """)
        
        result = connection.execute(columns_query)
        columns = result.fetchall()
        print(f"Total columns: {len(columns)}\n")
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            default = f" DEFAULT: {col[3]}" if col[3] else ""
            print(f"  • {col[0]:<25} {col[1]:<20} {nullable}{default}")
        print()
        
        # 5. Check User table data
        print("="*80)
        print("USERS IN DATABASE")
        print("="*80)
        
        user_query = text("""
            SELECT 
                u.user_id, 
                u.role_id,
                r.role_name,
                u.username, 
                u.email,
                FORMAT(u.created_at, 'yyyy-MM-dd HH:mm:ss') as created_at
            FROM [User] u
            LEFT JOIN Role r ON u.role_id = r.role_id
            ORDER BY u.user_id
        """)
        
        result = connection.execute(user_query)
        users = result.fetchall()
        print(f"Total users: {len(users)}\n")
        
        if len(users) > 0:
            print(f"{'ID':<6} {'Role ID':<8} {'Role Name':<15} {'Username':<25} {'Email':<35}")
            print("-" * 90)
            for user in users:
                print(f"{user[0]:<6} {user[1]:<8} {user[2] or 'NULL':<15} {user[3]:<25} {user[4]:<35}")
        else:
            print("  ⚠️  No users found in database")
        
        print()
        
        # 6. Check User statistics
        print("="*80)
        print("USER STATISTICS BY ROLE")
        print("="*80)
        print()
        
        stats_query = text("""
            SELECT 
                r.role_name,
                COUNT(u.user_id) as total_users
            FROM Role r
            LEFT JOIN [User] u ON r.role_id = u.role_id
            GROUP BY r.role_name
            ORDER BY COUNT(u.user_id) DESC
        """)
        
        result = connection.execute(stats_query)
        stats = result.fetchall()
        
        for stat in stats:
            print(f"  {stat[0]:<15} : {stat[1]} user(s)")
        
        print()
        print("="*80)

if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
