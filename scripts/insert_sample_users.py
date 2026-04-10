"""Insert sample users for admin, manager, and risk analyst roles in MySQL."""

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import pwd_context
from app.db.session import SessionLocal
from app.db.models import RoleDB, UserDB


sample_users = [
    {
        "username": "admin",
        "email": "admin@creditrisk.com",
        "password": "Admin@123456",
        "full_name": "Administrator",
        "role_names": ["admin", "Admin"],
    },
    {
        "username": "manager",
        "email": "manager@creditrisk.com",
        "password": "Manager@123456",
        "full_name": "Portfolio Manager",
        "role_names": ["manager", "Manager"],
    },
    {
        "username": "risk_analyst",
        "email": "risk.analyst@creditrisk.com",
        "password": "RiskAnalyst@123456",
        "full_name": "Risk Analyst",
        "role_names": ["risk analyst", "Risk Analyst", "analyst", "Analyst"],
    },
]


db = SessionLocal()
try:
    for user in sample_users:
        role = db.query(RoleDB).filter(RoleDB.role_name.in_(user["role_names"])).first()
        if not role:
            print(f"Role not found for {user['username']}, skipping")
            continue
        existing = db.query(UserDB).filter((UserDB.username == user["username"]) | (UserDB.email == user["email"])).first()
        if existing:
            print(f"User '{user['username']}' already exists, skipping")
            continue
        db.add(
            UserDB(
                role_id=role.role_id,
                username=user["username"],
                email=user["email"],
                password_hash=pwd_context.hash(user["password"]),
                full_name=user["full_name"],
                status="approved",
                is_email_verified=True,
                created_at=datetime.utcnow(),
            )
        )
        print(f"Inserted {user['username']}")
    db.commit()
finally:
    db.close()
