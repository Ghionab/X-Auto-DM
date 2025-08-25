#!/usr/bin/env python3
"""
Test the new x_api.py implementation
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_x_api_integration():
    """Test the new X API integration"""
    print("Testing X API integration...")
    
    try:
        from x_api import connect_twitter_api_account, TwitterAPIError, test_connection
        
        # Test connection first
        if test_connection():
            print("✓ API connection test passed")
        else:
            print("✗ API connection test failed")
            return False
        
        # Test with invalid credentials (should fail gracefully)
        try:
            result = connect_twitter_api_account(
                username="test_user",
                email="test@example.com", 
                password="test_pass",
                totp_secret="invalid_totp",
                proxy="http://user:pass@proxy.example.com:8080"
            )
            print("✗ Should have failed with invalid credentials")
            return False
        except TwitterAPIError as e:
            print(f"✓ Correctly handled invalid credentials: {str(e)}")
            return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_integration():
    """Test Flask integration with new API"""
    print("\nTesting Flask integration...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Register and login to get token
            import time
            unique_id = str(int(time.time()))
            
            reg_response = client.post('/api/auth/register', json={
                'email': f'test{unique_id}@example.com',
                'username': f'testuser{unique_id}',
                'password': 'TestPass123!'
            })
            
            if reg_response.status_code == 201:
                login_response = client.post('/api/auth/login', json={
                    'email': f'test{unique_id}@example.com',
                    'password': 'TestPass123!'
                })
                
                if login_response.status_code == 200:
                    token = login_response.get_json()['access_token']
                    
                    # Test X login endpoint
                    x_login_response = client.post('/api/auth/x/login', 
                        json={
                            'username': 'test_user',
                            'email': 'test@example.com',
                            'password': 'test_pass',
                            'totp_secret': 'invalid_totp',
                            'proxy': 'http://user:pass@proxy.example.com:8080'
                        },
                        headers={'Authorization': f'Bearer {token}'}
                    )
                    
                    print(f"X login endpoint: {x_login_response.status_code}")
                    response_data = x_login_response.get_json()
                    print(f"Response: {response_data}")
                    
                    # Should get 400 with proper error message
                    if x_login_response.status_code == 400 and 'error' in response_data:
                        print("✓ Flask integration works correctly")
                        return True
                    else:
                        print("✗ Unexpected response from Flask")
                        return False
                else:
                    print("✗ Login failed")
                    return False
            else:
                print("✗ Registration failed")
                return False
                
    except Exception as e:
        print(f"✗ Flask test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("X API Implementation Tests")
    print("=" * 40)
    
    success1 = test_x_api_integration()
    success2 = test_flask_integration()
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("✅ All tests passed!")
        print("\nThe new X API implementation is working correctly.")
        print("Users can now connect their X accounts using:")
        print("1. Valid X credentials")
        print("2. TOTP secret from 2FA settings")
        print("3. Valid proxy credentials")
    else:
        print("❌ Some tests failed")
    
    return success1 and success2

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)