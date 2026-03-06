#!/usr/bin/env python3
"""Quick registration test"""
import requests
import json

BASE = "http://localhost:8000/api/v1"

# Register analyst
print("\n1️⃣  REGISTERING ANALYST...")
data = {
    "username": "testanalyst",
    "email": "testanalyst@gmail.com",
    "password": "password123",
    "full_name": "Test Analyst",
    "registration_type": "analyst"
}

r = requests.post(f"{BASE}/auth/register/signup", json=data)
print(f"Status: {r.status_code}")

resp = r.json()
print(f"\n📧 Email: {resp.get('email')}")
print(f"🔐 Verification Token: {resp.get('verification_token')}")
print(f"🔗 Verification Link: {resp.get('verification_link')}")
print(f"📝 Message: {resp.get('message')}")

# Verify email
if resp.get('verification_token'):
    print("\n2️⃣  VERIFYING EMAIL...")
    token = resp['verification_token']
    r = requests.get(f"{BASE}/auth/register/verify-email?token={token}")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
