"""Test login endpoint directly"""
from app.api.routers.auth import login_for_access_token
from app.schemas.schemas import LoginRequest
import asyncio

async def test():
    try:
        request = LoginRequest(username_or_email="admin_system", password="hashed_pwd_123")
        result = await login_for_access_token(request)
        print(f"OK Success: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
