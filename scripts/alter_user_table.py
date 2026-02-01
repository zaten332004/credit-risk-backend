"""
Execute ALTER TABLE USER script to add missing columns
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text, inspect
from app.db.session import engine

def execute_alter_table():
    """Execute the ALTER TABLE script"""
    
    with engine.connect() as connection:
        try:
            transaction = connection.begin()
            
            # List of columns to add with their definitions
            columns_to_add = [
                ('phone', 'NVARCHAR(20) NULL'),
                ('full_name', 'NVARCHAR(100) NULL'),
                ('user_type', 'NVARCHAR(20) NULL'),
                ('status', "NVARCHAR(20) NULL DEFAULT 'pending'"),
                ('verification_token', 'NVARCHAR(255) NULL'),
                ('verification_sent_at', 'DATETIME2(7) NULL'),
                ('is_email_verified', 'BIT DEFAULT 0'),
                ('approved_by', 'BIGINT NULL'),
                ('approved_at', 'DATETIME2(7) NULL'),
                ('rejection_reason', 'NVARCHAR(500) NULL'),
                ('updated_at', 'DATETIME2(7) NULL'),
            ]
            
            print("=" * 80)
            print("ALTERING USER TABLE - ADDING MISSING COLUMNS")
            print("=" * 80)
            print()
            
            # Get current columns
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns('User')]
            
            print("Current columns in User table:")
            for col in existing_columns:
                print(f"  • {col}")
            print()
            
            # Add missing columns
            added_count = 0
            skipped_count = 0
            
            for col_name, col_def in columns_to_add:
                if col_name not in existing_columns:
                    sql = f"ALTER TABLE [User] ADD {col_name} {col_def}"
                    try:
                        connection.execute(text(sql))
                        print(f"✓ Added column: {col_name}")
                        added_count += 1
                    except Exception as e:
                        print(f"❌ Error adding {col_name}: {e}")
                else:
                    print(f"⚠️  Column {col_name} already exists")
                    skipped_count += 1
            
            transaction.commit()
            
            print()
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Columns added: {added_count}")
            print(f"Columns skipped (already exist): {skipped_count}")
            print()
            
            # Display final structure
            print("=" * 80)
            print("FINAL USER TABLE STRUCTURE")
            print("=" * 80)
            print()
            
            columns_query = text("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'User'
                ORDER BY ORDINAL_POSITION
            """)
            
            result = connection.execute(columns_query)
            columns = result.fetchall()
            
            print(f"{'Column Name':<25} {'Data Type':<20} {'Nullable':<12} {'Default':<30}")
            print("-" * 87)
            
            for col in columns:
                col_name = col[0]
                data_type = col[1]
                nullable = col[2]
                default = col[3] if col[3] else ""
                print(f"{col_name:<25} {data_type:<20} {nullable:<12} {str(default):<30}")
            
            print()
            print("=" * 80)
            print("✓ ALTER TABLE operation completed successfully!")
            print("=" * 80)
            
        except Exception as e:
            transaction.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    execute_alter_table()
