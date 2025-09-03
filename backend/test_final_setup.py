#!/usr/bin/env python3
"""
Final test to verify all fixes are working
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_jwt_endpoints():
    """Test that JWT endpoints work correctly"""
    print("Testing JWT endpoints...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Test registration
            import time
            unique_id = str(int(time.time()))
            reg_response = client.post('/api/auth/register', json={
                'email': f'test{unique_id}@example.com',
                'username': f'testuser{unique_id}',
                'password': 'TestPass123!'
            })
            
            print(f"Registration: {reg_response.status_code}")
            
            if reg_response.status_code == 201:
                # Test login
                login_response = client.post('/api/auth/login', json={
                    'email': f'test{unique_id}@example.com',
                    'password': 'TestPass123!'
                })
                
                print(f"Login: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    token = login_response.get_json()['access_token']
                    
                    # Test protected endpoint
                    profile_response = client.get('/api/auth/profile', 
                                                headers={'Authorization': f'Bearer {token}'})
                    
                    print(f"Profile (with token): {profile_response.status_code}")
                    
                    # Test without token (should get 401, not 422)
                    profile_no_token = client.get('/api/auth/profile')
                    print(f"Profile (no token): {profile_no_token.status_code}")
                    
                    if profile_response.status_code == 200 and profile_no_token.status_code == 401:
                        print("✓ JWT endpoints work correctly")
                        return True
                    else:
                        print("✗ JWT endpoints not working correctly")
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

def test_oauth_service():
    """Test OAuth service"""
    print("\nTesting OAuth service...")
    
    try:
        from app import create_app
        from services.x_oauth_service import XOAuthService
        
        app = create_app()
        with app.app_context():
            oauth_service = XOAuthService()
            
            # Test initiation
            success, result = oauth_service.initiate_oauth()
            
            if success:
                print("✓ OAuth initiation works")
                print(f"  Auth URL: {result.get('authorization_url', 'N/A')}")
                return True
            else:
                print(f"✗ OAuth initiation failed: {result}")
                return False
                
    except Exception as e:
        print(f"✗ OAuth test failed: {e}")
        return False

def test_x_login_endpoint():
    """Test X login endpoint"""
    print("\nTesting X login endpoint...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # First register and login to get token
            import time
            unique_id = str(int(time.time()) + 1)
            client.post('/api/auth/register', json={
                'email': f'test{unique_id}@example.com',
                'username': f'testuser{unique_id}',
                'password': 'TestPass123!'
            })
            
            login_response = client.post('/api/auth/login', json={
                'email': f'test{unique_id}@example.com',
                'password': 'TestPass123!'
            })
            
            if login_response.status_code == 200:
                token = login_response.get_json()['access_token']
                
                # Test X login endpoint (will fail due to invalid credentials, but should not give 422)
                x_login_response = client.post('/api/auth/x/login', 
                    json={
                        'username': 'test_user',
                        'email': 'test@example.com',
                        'password': 'test_pass'
                    },
                    headers={'Authorization': f'Bearer {token}'}
                )
                
                print(f"X login endpoint: {x_login_response.status_code}")
                
                # Should get 400 (bad request) not 422 (unprocessable entity)
                if x_login_response.status_code in [400, 401]:
                    print("✓ X login endpoint accessible")
                    return True
                elif x_login_response.status_code == 422:
                    print("✗ Still getting 422 errors")
                    return False
                else:
                    print(f"✓ X login endpoint works (status: {x_login_response.status_code})")
                    return True
            else:
                print("✗ Could not get auth token")
                return False
                
    except Exception as e:
        print(f"✗ X login test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Final Setup Verification")
    print("=" * 40)
    
    all_passed = True
    
    if not test_jwt_endpoints():
        all_passed = False
    
    if not test_oauth_service():
        all_passed = False
    
    if not test_x_login_endpoint():
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All tests passed! Setup is working correctly.")
        print("\nYou can now:")
        print("1. Start the Flask server: python app.py")
        print("2. Use the frontend to register/login")
        print("3. Connect X accounts using the new login form")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)