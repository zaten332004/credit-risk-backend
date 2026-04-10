"""Generate password hashes for selected users."""

from passlib.context import CryptContext

from app.db.models import UserDB
from app.db.session import SessionLocal

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

passwords = {
    "admin_system": "hashed_pwd_123",
    "manager_portfolio": "manager123",
    "manager_credit": "manager123",
    "risk_analyst": "RiskAnalyst@123456",
}

db = SessionLocal()
try:
    for username, pwd in passwords.items():
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if user:
            hashed_pwd = pwd_context.hash(pwd)
            user.password_hash = hashed_pwd
            print(f"Updated {username}: {hashed_pwd[:30]}...")
        else:
            print(f"User {username} not found")

    db.commit()
    print("\nAll passwords updated!")
finally:
    db.close()
