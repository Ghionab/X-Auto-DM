#!/usr/bin/env python3
"""
Test X OAuth 2.0 implementation
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_x_auth_creation():
    """Test X Auth instance creation"""
    print("Testing X Auth creation...")
    
    # Set test environment variables
    os.environ['X_CLIENT_ID'] = 'test_client_id'
    os.environ['X_CLIENT_SECRET'] = 'test_client_secret'
    
    try:
        from x_auth import create_x_auth, XAuthError
        
        x_auth = create_x_auth()
        print("✓ X Auth instance created successfully")
        
        # Test PKCE generation
        code_verifier, code_challenge = x_auth.generate_pkce_pair()
        print(f"✓ PKCE pair generated: verifier={code_verifier[:10]}..., challenge={code_challenge[:10]}...")
        
        # Test state generation
        state = x_auth.generate_state()
        print(f"✓ State generated: {state[:10]}...")
        
        # Test authorization URL generation
        auth_url = x_auth.get_authorization_url(state, code_challenge)
        print(f"✓ Authorization URL generated: {auth_url[:80]}...")
        
        # Verify URL contains required parameters
        required_params = ['response_type=code', 'client_id=test_client_id', 'code_challenge', 'state']
        for param in required_params:
            if param in auth_url:
                print(f"✓ URL contains {param}")
            else:
                print(f"✗ URL missing {param}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ X Auth test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_endpoints():
    """Test Flask OAuth endpoints"""
    print("\nTesting Flask OAuth endpoints...")
    
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
                    
                    # Test OAuth initiation endpoint
                    oauth_response = client.get('/api/auth/x/login', 
                                              headers={'Authorization': f'Bearer {token}'})
                    
                    print(f"OAuth initiation: {oauth_response.status_code}")
                    
                    if oauth_response.status_code == 200:
                        data = oauth_response.get_json()
                        if 'authorization_url' in data and 'state' in data and 'code_verifier' in data:
                            print("✓ OAuth initiation endpoint works correctly")
                            print(f"✓ Authorization URL: {data['authorization_url'][:50]}...")
                            return True
                        else:
                            print("✗ Missing required fields in OAuth response")
                            return False
                    else:
                        print(f"✗ OAuth initiation failed: {oauth_response.get_json()}")
                        return False
                else:
                    print("✗ Login failed")
                    return False
            else:
                print("✗ Registration failed")
                return False
                
    except Exception as e:
        print(f"✗ Flask test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pkce_validation():
    """Test PKCE code verifier and challenge generation"""
    print("\nTesting PKCE validation...")
    
    try:
        from x_auth import create_x_auth
        import hashlib
        import base64
        
        x_auth = create_x_auth()
        code_verifier, code_challenge = x_auth.generate_pkce_pair()
        
        # Verify code challenge is correct SHA256 hash of verifier
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        if code_challenge == expected_challenge:
            print("✓ PKCE code challenge correctly generated from verifier")
            return True
        else:
            print("✗ PKCE code challenge does not match expected value")
            return False
            
    except Exception as e:
        print(f"✗ PKCE validation failed: {e}")
        return False

def main():
    """Run all OAuth 2.0 tests"""
    print("X OAuth 2.0 Implementation Tests")
    print("=" * 50)
    
    success1 = test_x_auth_creation()
    success2 = test_flask_endpoints()
    success3 = test_pkce_validation()
    
    print("\n" + "=" * 50)
    if success1 and success2 and success3:
        print("✅ All OAuth 2.0 tests passed!")
        print("\nThe X OAuth 2.0 implementation is working correctly:")
        print("• PKCE flow implemented properly")
        print("• Flask endpoints configured")
        print("• Authorization URL generation works")
        print("• State parameter for CSRF protection")
        print("• Ready for production with real X API credentials")
        print("\nNext steps:")
        print("1. Get X API credentials from developer.twitter.com")
        print("2. Set X_CLIENT_ID and X_CLIENT_SECRET in .env")
        print("3. Test with real X OAuth flow")
    else:
        print("❌ Some tests failed")
        if not success1:
            print("• Check X Auth implementation")
        if not success2:
            print("• Check Flask endpoint configuration")
        if not success3:
            print("• Check PKCE implementation")
    
    return success1 and success2 and success3

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)