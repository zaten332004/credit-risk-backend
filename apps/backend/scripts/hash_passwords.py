"""Generate password hashes for users"""
from passlib.context import CryptContext
from app.db.session import SessionLocal
from app.db.models import UserDB

pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')

# Password mappings
passwords = {
    'admin_system': 'hashed_pwd_123',
    'manager_portfolio': 'manager123',
    'manager_credit': 'manager123',
    'officer_nguyen': 'officer123',
    'officer_tran': 'officer123',
    'analyst_risk': 'analyst123',
}

db = SessionLocal()
try:
    for username, pwd in passwords.items():
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if user:
            hashed_pwd = pwd_context.hash(pwd)
            user.password = hashed_pwd
            print(f'✅ Updated {username}: {hashed_pwd[:30]}...')
        else:
            print(f'❌ User {username} not found')
    
    db.commit()
    print('\n✅ All passwords updated!')
finally:
    db.close()
