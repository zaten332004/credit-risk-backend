#!/usr/bin/env python3
"""Debug authentication"""
from app.core.security import authenticate_user_by_username_or_email, create_access_token

# Test login with correct password
print("Testing authentication...")
try:
    user_dict = authenticate_user_by_username_or_email("admin", "Admin123")
    print(f"User dict: {user_dict}")
    
    if user_dict:
        token = create_access_token({
            "sub": user_dict["email"],
            "role": user_dict.get("role", "viewer")
        })
        print(f"Token created: {token[:50]}...")
        print(f"User email: {user_dict['email']}")
        print(f"Role: {user_dict['role']}")
    else:
        print("Authentication failed - user not found or password incorrect")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
