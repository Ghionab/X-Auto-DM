#!/usr/bin/env python3
"""
Direct test of registration without running server
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_registration_direct():
    """Test registration directly through Flask app"""
    print("Testing registration directly...")
    
    try:
        from app import create_app
        from models import db, User
        
        app = create_app()
        
        with app.test_client() as client:
            # Test registration
            response = client.post('/api/auth/register', json={
                'email': 'test@example.com',
                'username': 'testuser',
                'password': 'TestPass123!'
            })
            
            print(f"Registration response: {response.status_code}")
            print(f"Response data: {response.get_json()}")
            
            if response.status_code == 201:
                print("✓ Registration works!")
                
                # Test login
                login_response = client.post('/api/auth/login', json={
                    'email': 'test@example.com',
                    'password': 'TestPass123!'
                })
                
                print(f"Login response: {login_response.status_code}")
                print(f"Login data: {login_response.get_json()}")
                
                if login_response.status_code == 200:
                    print("✓ Login works!")
                    return True
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

if __name__ == '__main__':
    success = test_registration_direct()
    sys.exit(0 if success else 1)