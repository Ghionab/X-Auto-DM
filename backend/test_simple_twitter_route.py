#!/usr/bin/env python3
"""
Simple test to verify the Twitter login route is working
"""

import sys
import os
import json
import requests

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_simple_route():
    """Test the Twitter login route directly"""
    
    try:
        # Start the Flask app in test mode
        from app import create_app
        from models import db, User
        from flask_jwt_extended import create_access_token
        
        app = create_app('testing')
        
        with app.app_context():
            # Create test user
            test_user = User(
                email='test@example.com',
                username='testuser'
            )
            test_user.set_password('TestPassword123!')
            
            db.session.add(test_user)
            db.session.commit()
            
            # Create JWT token
            access_token = create_access_token(identity=str(test_user.id))
            
            # Test with app test client
            with app.test_client() as client:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Test empty JSON
                response = client.post('/api/auth/twitter/login', 
                                     headers=headers,
                                     json={})
                
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.get_json()}")
                
                # Check if we get the new error format
                data = response.get_json()
                if 'success' in data:
                    print("✅ New enhanced error handling is working!")
                    return True
                else:
                    print("❌ Still using old error format")
                    return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_simple_route()
    if not success:
        sys.exit(1)