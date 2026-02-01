"""
Script to insert sample users for each role (1 user per role)
"""
import sys
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, '../')

from app.db.models import UserDB, RoleDB
from app.db.session import SQLALCHEMY_DATABASE_URL

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def insert_sample_users():
    """Insert 1 sample user for each role"""
    
    # Create database connection
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Define sample users for each role
        sample_users = [
            {
                "role_id": 1,
                "username": "admin_demo",
                "email": "admin.demo@creditbank.com",
                "password": "Admin@123456",
                "full_name": "Quản Trị Viên Demo",
                "phone": "+84901234567",
                "status": "verified",
                "is_email_verified": True,
            },
            {
                "role_id": 2,
                "username": "manager_demo",
                "email": "manager.demo@creditbank.com",
                "password": "Manager@123456",
                "full_name": "Quản Lý Tín Dụng Demo",
                "phone": "+84902234567",
                "status": "verified",
                "is_email_verified": True,
            },
            {
                "role_id": 3,
                "username": "officer_demo",
                "email": "officer.demo@creditbank.com",
                "password": "Officer@123456",
                "full_name": "Nhân Viên Tín Dụng Demo",
                "phone": "+84903234567",
                "status": "verified",
                "is_email_verified": True,
            },
            {
                "role_id": 4,
                "username": "customer_demo",
                "email": "customer.demo@email.com",
                "password": "Customer@123456",
                "full_name": "Khách Hàng Demo",
                "phone": "+84904234567",
                "status": "verified",
                "is_email_verified": True,
            },
            {
                "role_id": 5,
                "username": "analyst_demo",
                "email": "analyst.demo@creditbank.com",
                "password": "Analyst@123456",
                "full_name": "Nhà Phân Tích Rủi Ro Demo",
                "phone": "+84905234567",
                "status": "verified",
                "is_email_verified": True,
            },
        ]
        
        # Insert users
        inserted_count = 0
        for user_data in sample_users:
            # Check if user already exists
            existing_user = session.query(UserDB).filter_by(
                username=user_data["username"]
            ).first()
            
            if existing_user:
                print(f"⚠️  User '{user_data['username']}' already exists, skipping...")
                continue
            
            # Hash password
            hashed_password = hash_password(user_data["password"])
            
            # Create user
            new_user = UserDB(
                role_id=user_data["role_id"],
                username=user_data["username"],
                email=user_data["email"],
                password=hashed_password,
                full_name=user_data["full_name"],
                phone=user_data["phone"],
                status=user_data["status"],
                is_email_verified=user_data["is_email_verified"],
                created_at=datetime.utcnow(),
            )
            
            session.add(new_user)
            inserted_count += 1
            print(f"✓ Added user: {user_data['full_name']} ({user_data['username']}) - Role ID: {user_data['role_id']}")
        
        # Commit changes
        session.commit()
        print(f"\n✓ Successfully inserted {inserted_count} sample users!")
        
        # Print summary
        print("\n" + "="*70)
        print("SAMPLE USERS CREDENTIALS:")
        print("="*70)
        for user_data in sample_users:
            role_names = {
                1: "Admin",
                2: "Manager",
                3: "Officer",
                4: "Customer",
                5: "Analyst"
            }
            print(f"\n{role_names[user_data['role_id']]}:")
            print(f"  Username: {user_data['username']}")
            print(f"  Password: {user_data['password']}")
            print(f"  Email: {user_data['email']}")
        print("\n" + "="*70)
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error inserting users: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    insert_sample_users()
