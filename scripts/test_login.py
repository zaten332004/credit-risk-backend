"""Test login"""
from app.core.security import authenticate_user_by_username_or_email

result = authenticate_user_by_username_or_email('admin_system', 'hashed_pwd_123')
if result:
    print('✅ Login successful!')
    print(f'  Username: {result["username"]}')
    print(f'  Email: {result["email"]}')
    print(f'  Role: {result["role"]}')
else:
    print('❌ Login failed')
