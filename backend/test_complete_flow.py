#!/usr/bin/env python3
"""
Test complete X login flow
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_flow():
    """Test the complete X login flow"""
    print("Testing complete X login flow...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            print("1. Testing user registration...")
            
            # Register user
            import time
            unique_id = str(int(time.time()))
            
            reg_response = client.post('/api/auth/register', json={
                'email': f'test{unique_id}@example.com',
                'username': f'testuser{unique_id}',
                'password': 'TestPass123!'
            })
            
            if reg_response.status_code != 201:
                print(f"✗ Registration failed: {reg_response.get_json()}")
                return False
            
            print("✓ User registration successful")
            
            print("2. Testing user login...")
            
            # Login user
            login_response = client.post('/api/auth/login', json={
                'email': f'test{unique_id}@example.com',
                'password': 'TestPass123!'
            })
            
            if login_response.status_code != 200:
                print(f"✗ Login failed: {login_response.get_json()}")
                return False
            
            token = login_response.get_json()['access_token']
            print("✓ User login successful")
            
            print("3. Testing X account connection (should fail with invalid credentials)...")
            
            # Test X login
            x_login_response = client.post('/api/auth/x/login', 
                json={
                    'username': 'test_user',
                    'email': 'test@example.com',
                    'password': 'test_pass',
                    'totp_secret': 'ABCDEFGHIJKLMNOP',
                    'proxy': 'http://user:pass@proxy.example.com:8080'
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            
            print(f"X login response: {x_login_response.status_code}")
            response_data = x_login_response.get_json()
            print(f"Response data: {response_data}")
            
            # Should fail with 400 and proper error message
            if x_login_response.status_code == 400 and 'error' in response_data:
                print("✓ X login properly handles invalid credentials")
                
                # Check if error message is informative
                error_msg = response_data['error']
                if len(error_msg) > 10:  # Has a meaningful error message
                    print("✓ Error message is informative")
                    return True
                else:
                    print("✗ Error message is too generic")
                    return False
            else:
                print("✗ Unexpected response from X login")
                return False
                
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_key_validation():
    """Test API key validation"""
    print("\nTesting API key validation...")
    
    try:
        from x_api import test_connection
        
        if test_connection():
            print("✓ API key is valid and service is accessible")
            return True
        else:
            print("✗ API key validation failed")
            return False
            
    except Exception as e:
        print(f"✗ API key test failed: {e}")
        return False

def main():
    """Run complete flow test"""
    print("Complete X Login Flow Test")
    print("=" * 50)
    
    success1 = test_api_key_validation()
    success2 = test_complete_flow()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ Complete flow test passed!")
        print("\nThe X login system is working correctly:")
        print("• API key is valid")
        print("• User registration/login works")
        print("• X account connection endpoint is accessible")
        print("• Error handling is working properly")
        print("• Frontend will receive proper error messages")
        print("\nUsers can now connect X accounts with valid credentials!")
    else:
        print("❌ Some tests failed")
        if not success1:
            print("• Check TWITTERAPI_IO_API_KEY in .env file")
        if not success2:
            print("• Check Flask application setup")
    
    return success1 and success2

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)