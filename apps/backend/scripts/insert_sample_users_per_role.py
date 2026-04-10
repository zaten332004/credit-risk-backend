"""Insert one sample user for each active MySQL role."""

import sys
from datetime import datetime
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import UserDB
from app.db.session import SQLALCHEMY_DATABASE_URL

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def insert_sample_users():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    session = sessionmaker(bind=engine)()

    sample_users = [
        {
            "role_id": 1,
            "username": "admin_demo",
            "email": "admin.demo@creditbank.com",
            "password": "Admin@123456",
            "full_name": "Admin Demo",
            "phone": "+84901234567",
            "status": "verified",
            "is_email_verified": True,
        },
        {
            "role_id": 2,
            "username": "manager_demo",
            "email": "manager.demo@creditbank.com",
            "password": "Manager@123456",
            "full_name": "Manager Demo",
            "phone": "+84902234567",
            "status": "verified",
            "is_email_verified": True,
        },
        {
            "role_id": 3,
            "username": "risk_analyst_demo",
            "email": "risk.analyst.demo@creditbank.com",
            "password": "RiskAnalyst@123456",
            "full_name": "Risk Analyst Demo",
            "phone": "+84903234567",
            "status": "verified",
            "is_email_verified": True,
        },
    ]

    try:
        inserted_count = 0
        for user_data in sample_users:
            existing_user = session.query(UserDB).filter_by(username=user_data["username"]).first()
            if existing_user:
                print(f"User '{user_data['username']}' already exists, skipping...")
                continue

            session.add(
                UserDB(
                    role_id=user_data["role_id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    full_name=user_data["full_name"],
                    phone=user_data["phone"],
                    status=user_data["status"],
                    is_email_verified=user_data["is_email_verified"],
                    created_at=datetime.utcnow(),
                )
            )
            inserted_count += 1
            print(f"Added user: {user_data['username']} (role_id={user_data['role_id']})")

        session.commit()
        print(f"\nSuccessfully inserted {inserted_count} sample users.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    insert_sample_users()
