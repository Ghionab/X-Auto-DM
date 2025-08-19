#!/usr/bin/env python3
"""
Test X login functionality
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_x_login_endpoint():
    """Test X login endpoint with proper error handling"""
    print("Testing X login endpoint...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # First register and login to get token
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
                    
                    # Test X login endpoint with missing TOTP
                    x_login_response = client.post('/api/auth/x/login', 
                        json={
                            'username': 'test_user',
                            'email': 'test@example.com',
                            'password': 'test_pass'
                            # Missing totp_secret
                        },
                        headers={'Authorization': f'Bearer {token}'}
                    )
                    
                    print(f"X login (no TOTP): {x_login_response.status_code}")
                    print(f"Response: {x_login_response.get_json()}")
                    
                    # Test X login endpoint with TOTP
                    x_login_response2 = client.post('/api/auth/x/login', 
                        json={
                            'username': 'test_user',
                            'email': 'test@example.com',
                            'password': 'test_pass',
                            'totp_secret': 'invalid_totp'
                        },
                        headers={'Authorization': f'Bearer {token}'}
                    )
                    
                    print(f"X login (with TOTP): {x_login_response2.status_code}")
                    print(f"Response: {x_login_response2.get_json()}")
                    
                    if x_login_response.status_code == 400 and x_login_response2.status_code == 400:
                        print("✓ X login endpoint works correctly (returns 400 for invalid credentials)")
                        return True
                    else:
                        print("✗ Unexpected response codes")
                        return False
                else:
                    print("✗ Login failed")
                    return False
            else:
                print("✗ Registration failed")
                return False
                
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run X login test"""
    print("X Login Endpoint Test")
    print("=" * 30)
    
    if test_x_login_endpoint():
        print("\n✅ X login endpoint is working correctly!")
        print("\nTo connect a real X account:")
        print("1. Go to your X account settings")
        print("2. Enable 2FA and get your TOTP secret")
        print("3. Use the login form with your real credentials")
    else:
        print("\n❌ X login endpoint test failed")
    
    return True

if __name__ == '__main__':
    main()