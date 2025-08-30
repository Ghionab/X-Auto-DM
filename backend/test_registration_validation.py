#!/usr/bin/env python3
"""
Test script for registration API endpoint validation
Tests all validation requirements for task 1.3
"""

import requests
import json
import sys
import time

# Test configuration
BASE_URL = "http://localhost:5000"
REGISTER_URL = f"{BASE_URL}/api/auth/register"

def test_registration_validation():
    """Test all registration validation scenarios"""
    
    print("🧪 Testing Registration API Validation")
    print("=" * 50)
    
    # Test cases for validation
    test_cases = [
        # Valid registration
        {
            "name": "Valid Registration",
            "data": {
                "email": "test@example.com",
                "username": "testuser123",
                "password": "TestPass123!"
            },
            "expected_status": 201,
            "should_pass": True
        },
        
        # Email format validation
        {
            "name": "Invalid Email Format - Missing @",
            "data": {
                "email": "testexample.com",
                "username": "testuser124",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Invalid email format"
        },
        {
            "name": "Invalid Email Format - Missing Domain",
            "data": {
                "email": "test@",
                "username": "testuser125",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Invalid email format"
        },
        {
            "name": "Invalid Email Format - Missing TLD",
            "data": {
                "email": "test@example",
                "username": "testuser126",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Invalid email format"
        },
        
        # Username validation
        {
            "name": "Username Too Short",
            "data": {
                "email": "test2@example.com",
                "username": "ab",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Username must be at least 3 characters long"
        },
        {
            "name": "Username Too Long",
            "data": {
                "email": "test3@example.com",
                "username": "a" * 31,  # 31 characters
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Username must be less than 30 characters"
        },
        {
            "name": "Username Invalid Characters",
            "data": {
                "email": "test4@example.com",
                "username": "test-user!",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Username can only contain letters, numbers, and underscores"
        },
        
        # Password strength validation
        {
            "name": "Password Too Short",
            "data": {
                "email": "test5@example.com",
                "username": "testuser127",
                "password": "Test1!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "at least 8 characters"
        },
        {
            "name": "Password Missing Uppercase",
            "data": {
                "email": "test6@example.com",
                "username": "testuser128",
                "password": "testpass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "one uppercase letter"
        },
        {
            "name": "Password Missing Lowercase",
            "data": {
                "email": "test7@example.com",
                "username": "testuser129",
                "password": "TESTPASS123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "one lowercase letter"
        },
        {
            "name": "Password Missing Number",
            "data": {
                "email": "test8@example.com",
                "username": "testuser130",
                "password": "TestPassword!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "one number"
        },
        {
            "name": "Password Missing Special Character",
            "data": {
                "email": "test9@example.com",
                "username": "testuser131",
                "password": "TestPass123"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "one special character"
        },
        
        # Required fields validation
        {
            "name": "Missing Email",
            "data": {
                "username": "testuser132",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "email is required"
        },
        {
            "name": "Missing Username",
            "data": {
                "email": "test10@example.com",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "username is required"
        },
        {
            "name": "Missing Password",
            "data": {
                "email": "test11@example.com",
                "username": "testuser133"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "password is required"
        },
        
        # Uniqueness validation (will test after first user is created)
        {
            "name": "Duplicate Email",
            "data": {
                "email": "test@example.com",  # Same as first test
                "username": "testuser134",
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Email address is already registered"
        },
        {
            "name": "Duplicate Username",
            "data": {
                "email": "test12@example.com",
                "username": "testuser123",  # Same as first test
                "password": "TestPass123!"
            },
            "expected_status": 400,
            "should_pass": False,
            "expected_error": "Username is already taken"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        
        try:
            response = requests.post(
                REGISTER_URL,
                json=test_case['data'],
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Check status code
            if response.status_code != test_case['expected_status']:
                print(f"   ❌ FAIL: Expected status {test_case['expected_status']}, got {response.status_code}")
                print(f"   Response: {response.text}")
                failed += 1
                continue
            
            response_data = response.json()
            
            if test_case['should_pass']:
                if 'message' in response_data and 'User registered successfully' in response_data['message']:
                    print(f"   ✅ PASS: User registered successfully")
                    passed += 1
                else:
                    print(f"   ❌ FAIL: Expected success message, got: {response_data}")
                    failed += 1
            else:
                if 'error' in response_data and test_case['expected_error'] in response_data['error']:
                    print(f"   ✅ PASS: Correct validation error: {response_data['error']}")
                    passed += 1
                else:
                    print(f"   ❌ FAIL: Expected error containing '{test_case['expected_error']}', got: {response_data}")
                    failed += 1
                    
        except requests.exceptions.RequestException as e:
            print(f"   ❌ FAIL: Request failed: {e}")
            failed += 1
        except json.JSONDecodeError as e:
            print(f"   ❌ FAIL: Invalid JSON response: {e}")
            print(f"   Response text: {response.text}")
            failed += 1
        except Exception as e:
            print(f"   ❌ FAIL: Unexpected error: {e}")
            failed += 1
        
        # Small delay between requests to avoid rate limiting
        time.sleep(0.1)
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the validation implementation.")
        return False

def check_server_health():
    """Check if the Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Make sure the Flask server is running on http://localhost:5000")
        return False

if __name__ == "__main__":
    print("🚀 Registration Validation Test Suite")
    print("=" * 50)
    
    # Check server health first
    if not check_server_health():
        sys.exit(1)
    
    # Run validation tests
    success = test_registration_validation()
    
    if success:
        print("\n✅ All registration validation requirements are implemented correctly!")
        sys.exit(0)
    else:
        print("\n❌ Registration validation needs fixes.")
        sys.exit(1)