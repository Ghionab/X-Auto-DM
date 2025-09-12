#!/usr/bin/env python3
"""
Test script for manual account addition API endpoints
"""

import requests
import json
import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Test the manual account addition endpoints"""
    
    print("🧪 Testing Manual Account Addition API Endpoints")
    print("=" * 50)
    
    # Test data
    test_cookie = json.dumps({
        "auth_token": "test_auth_token_1234567890abcdef",
        "twid": "\"u=1234567890\"",
        "ct0": "test_ct0_token",
        "guest_id": "v1%3A123456789",
        "_twitter_sess": "test_session_token"
    })
    
    # First, we need to register and login to get a JWT token
    print("\n1. Registering test user...")
    register_data = {
        "email": "test@example.com",
        "username": "testuser123",
        "password": "TestPassword123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ User registered successfully")
        elif response.status_code == 400 and "already registered" in response.text:
            print("ℹ️  User already exists, continuing...")
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask server. Make sure it's running on localhost:5000")
        return
    
    print("\n2. Logging in to get JWT token...")
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return
    
    login_result = response.json()
    jwt_token = login_result['access_token']
    print("✅ Login successful, JWT token obtained")
    
    # Set up headers with JWT token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    print("\n3. Testing cookie validation endpoint...")
    validate_data = {
        "login_cookie": test_cookie
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/twitter/validate-cookie", 
                           json=validate_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Cookie validation successful")
        print(f"   Valid: {result['valid']}")
        print(f"   Account Info: {result.get('account_info', {})}")
    else:
        print(f"❌ Cookie validation failed: {response.status_code} - {response.text}")
        return
    
    print("\n4. Testing manual account addition endpoint...")
    add_account_data = {
        "login_cookie": test_cookie,
        "account_name": "Test Account"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/twitter/add-manual", 
                           json=add_account_data, headers=headers)
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Manual account addition successful")
        print(f"   Account ID: {result['account']['account_id']}")
        print(f"   Username: {result['account']['username']}")
        print(f"   Connection Status: {result['account']['connection_status']}")
    else:
        print(f"❌ Manual account addition failed: {response.status_code} - {response.text}")
        return
    
    print("\n5. Testing duplicate account addition (should fail)...")
    response = requests.post(f"{BASE_URL}/api/auth/twitter/add-manual", 
                           json=add_account_data, headers=headers)
    
    if response.status_code == 400:
        result = response.json()
        print("✅ Duplicate account prevention working")
        print(f"   Error: {result['error']}")
    else:
        print(f"⚠️  Expected 400 error for duplicate account, got: {response.status_code}")
    
    print("\n6. Testing invalid cookie validation...")
    invalid_cookie_data = {
        "login_cookie": "invalid_cookie_format"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/twitter/validate-cookie", 
                           json=invalid_cookie_data, headers=headers)
    
    if response.status_code == 400:
        result = response.json()
        print("✅ Invalid cookie rejection working")
        print(f"   Error: {result['error']}")
    else:
        print(f"⚠️  Expected 400 error for invalid cookie, got: {response.status_code}")
    
    print("\n7. Testing rate limiting...")
    print("   Making multiple rapid requests to test rate limiting...")
    
    for i in range(12):  # Exceed the 10 per minute limit
        response = requests.post(f"{BASE_URL}/api/auth/twitter/validate-cookie", 
                               json=validate_data, headers=headers)
        if response.status_code == 429:
            print(f"✅ Rate limiting activated after {i+1} requests")
            break
    else:
        print("⚠️  Rate limiting not triggered (may need more requests)")
    
    print("\n" + "=" * 50)
    print("🎉 Manual Account Addition API Endpoint Tests Complete!")

if __name__ == "__main__":
    test_endpoints()