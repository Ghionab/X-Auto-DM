#!/usr/bin/env python3
"""
Debug JWT issues
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_jwt():
    """Debug JWT token creation and validation"""
    print("Debugging JWT...")
    
    try:
        from app import create_app
        from flask_jwt_extended import create_access_token, decode_token
        
        app = create_app()
        
        with app.app_context():
            # Create a test token
            test_user_id = "1"
            token = create_access_token(identity=test_user_id)
            print(f"Created token: {token[:50]}...")
            
            # Try to decode it
            try:
                decoded = decode_token(token)
                print(f"Decoded token: {decoded}")
                print("✓ JWT token creation and decoding works")
                
                # Test with test client
                with app.test_client() as client:
                    # Test with Authorization header
                    response = client.get('/api/auth/profile', 
                                        headers={'Authorization': f'Bearer {token}'})
                    print(f"Profile response: {response.status_code}")
                    print(f"Profile data: {response.get_json()}")
                    
                    if response.status_code == 404:
                        print("✓ JWT validation works (user not found is expected)")
                        return True
                    elif response.status_code == 200:
                        print("✓ JWT validation works completely")
                        return True
                    else:
                        print(f"✗ Unexpected response: {response.status_code}")
                        return False
                        
            except Exception as e:
                print(f"✗ Token decode failed: {e}")
                return False
                
    except Exception as e:
        print(f"✗ JWT debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = debug_jwt()
    sys.exit(0 if success else 1)