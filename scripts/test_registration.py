#!/usr/bin/env python3
"""Test registration API"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Test 1: Register analyst
print("=" * 60)
print("TEST 1: Register Analyst")
print("=" * 60)

analyst_data = {
    "username": "analyst_test123",
    "email": "analyst@test.com",
    "password": "password123",
    "full_name": "Test Analyst",
    "phone": "123456789",
    "registration_type": "analyst"
}

response = requests.post(f"{BASE_URL}/auth/register/signup", json=analyst_data)
print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

if response.status_code == 201:
    analyst_response = response.json()
    analyst_token = analyst_response.get("verification_token")
    analyst_link = analyst_response.get("verification_link")
    
    print(f"\n✓ Registration successful!")
    print(f"✓ Verification Token: {analyst_token}")
    print(f"✓ Verification Link: {analyst_link}")
    
    # Test 2: Verify email
    print("\n" + "=" * 60)
    print("TEST 2: Verify Analyst Email")
    print("=" * 60)
    
    verify_url = f"{BASE_URL}/auth/register/verify-email?token={analyst_token}"
    response = requests.get(verify_url)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Test 3: Register manager
print("\n" + "=" * 60)
print("TEST 3: Register Manager")
print("=" * 60)

manager_data = {
    "username": "manager_test123",
    "email": "manager@test.com",
    "password": "password123",
    "full_name": "Test Manager",
    "phone": "987654321",
    "registration_type": "manager"
}

response = requests.post(f"{BASE_URL}/auth/register/signup", json=manager_data)
print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

if response.status_code == 201:
    manager_response = response.json()
    manager_token = manager_response.get("verification_token")
    manager_link = manager_response.get("verification_link")
    
    print(f"\n✓ Registration successful!")
    print(f"✓ Verification Token: {manager_token}")
    print(f"✓ Verification Link: {manager_link}")
    
    # Verify manager email
    print("\n" + "=" * 60)
    print("TEST 4: Verify Manager Email")
    print("=" * 60)
    
    verify_url = f"{BASE_URL}/auth/register/verify-email?token={manager_token}"
    response = requests.get(verify_url)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Test 5: Login as admin to check pending registrations
print("\n" + "=" * 60)
print("TEST 5: Admin Login & Check Pending Registrations")
print("=" * 60)

login_data = {
    "username_or_email": "admin_system",
    "password": "hashed_pwd_123"
}

response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"Login Status: {response.status_code}")

if response.status_code == 200:
    token_response = response.json()
    admin_token = token_response.get("access_token")
    
    print(f"✓ Admin login successful!")
    print(f"✓ Token: {admin_token[:50]}...")
    
    # Get pending registrations
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/auth/register/pending", headers=headers)
    print(f"\nPending Registrations Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
