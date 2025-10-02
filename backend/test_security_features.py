#!/usr/bin/env python3
"""
Test security features for manual account addition endpoints
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_security_features():
    """Test security features of the manual account addition endpoints"""
    
    print("🔒 Testing Security Features for Manual Account Addition")
    print("=" * 60)
    
    try:
        from app import create_app
        from models import db, User, TwitterAccount
        
        # Create temporary database for testing
        db_fd, db_path = tempfile.mkstemp()
        
        # Configure app for testing
        app = create_app('development')
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                
                # Create test user
                import time
                timestamp = str(int(time.time()))
                register_data = {
                    "email": f"security_test{timestamp}@example.com",
                    "username": f"securitytest{timestamp}",
                    "password": "TestPassword123!"
                }
                
                client.post('/api/auth/register', 
                           data=json.dumps(register_data),
                           content_type='application/json')
                
                login_data = {
                    "email": f"security_test{timestamp}@example.com",
                    "password": "TestPassword123!"
                }
                
                response = client.post('/api/auth/login',
                                     data=json.dumps(login_data),
                                     content_type='application/json')
                
                jwt_token = response.get_json()['access_token']
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Content-Type': 'application/json'
                }
                
                print("1. Testing authentication requirement...")
                # Test without JWT token
                response = client.post('/api/auth/twitter/validate-cookie',
                                     data=json.dumps({"login_cookie": "test"}),
                                     content_type='application/json')
                
                if response.status_code == 401:
                    print("✅ Authentication requirement enforced")
                else:
                    print(f"⚠️  Expected 401 for missing auth, got: {response.status_code}")
                
                print("2. Testing invalid JWT token...")
                invalid_headers = {
                    'Authorization': 'Bearer invalid_token_here',
                    'Content-Type': 'application/json'
                }
                
                response = client.post('/api/auth/twitter/validate-cookie',
                                     data=json.dumps({"login_cookie": "test"}),
                                     headers=invalid_headers)
                
                if response.status_code == 422:  # JWT decode error
                    print("✅ Invalid JWT token rejected")
                else:
                    print(f"⚠️  Expected 422 for invalid JWT, got: {response.status_code}")
                
                print("3. Testing malicious cookie injection...")
                malicious_cookies = [
                    '{"auth_token": "<script>alert(1)</script>"}',
                    '{"auth_token": "../../etc/passwd"}',
                    '{"auth_token": "DROP TABLE users;"}',
                    '{"auth_token": "' + 'A' * 10000 + '"}',  # Very long token
                ]
                
                for i, malicious_cookie in enumerate(malicious_cookies):
                    response = client.post('/api/auth/twitter/validate-cookie',
                                         data=json.dumps({"login_cookie": malicious_cookie}),
                                         headers=headers)
                    
                    if response.status_code == 400:
                        print(f"✅ Malicious cookie {i+1} rejected")
                    else:
                        print(f"⚠️  Malicious cookie {i+1} not properly rejected: {response.status_code}")
                
                print("4. Testing SQL injection attempts...")
                sql_injection_attempts = [
                    '{"auth_token": "test", "twid": "\\"u=1\\"; DROP TABLE users; --"}',
                    '{"auth_token": "test\\"; INSERT INTO users VALUES (1,\\"hacker\\"); --"}',
                ]
                
                for i, injection_attempt in enumerate(sql_injection_attempts):
                    response = client.post('/api/auth/twitter/add-manual',
                                         data=json.dumps({"login_cookie": injection_attempt}),
                                         headers=headers)
                    
                    # Should fail validation, not cause SQL injection
                    if response.status_code in [400, 500]:
                        print(f"✅ SQL injection attempt {i+1} blocked")
                    else:
                        print(f"⚠️  SQL injection attempt {i+1} response: {response.status_code}")
                
                print("5. Testing cookie encryption...")
                valid_cookie = json.dumps({
                    "auth_token": "test_auth_token_security_test",
                    "twid": "\"u=9876543210\"",
                    "ct0": "test_ct0_token"
                })
                
                response = client.post('/api/auth/twitter/add-manual',
                                     data=json.dumps({
                                         "login_cookie": valid_cookie,
                                         "account_name": "Security Test Account"
                                     }),
                                     headers=headers)
                
                if response.status_code == 201:
                    # Check that cookie is encrypted in database
                    user = User.query.filter_by(email=f"security_test{timestamp}@example.com").first()
                    account = TwitterAccount.query.filter_by(user_id=user.id).first()
                    
                    if account and account.login_cookie:
                        # Cookie should be encrypted (not plain text)
                        if valid_cookie not in account.login_cookie:
                            print("✅ Cookie properly encrypted in database")
                        else:
                            print("❌ Cookie stored in plain text!")
                    else:
                        print("⚠️  Account or cookie not found in database")
                else:
                    print(f"⚠️  Account creation failed: {response.status_code}")
                
                print("6. Testing input validation...")
                invalid_inputs = [
                    {},  # Empty data
                    {"login_cookie": ""},  # Empty cookie
                    {"login_cookie": None},  # Null cookie
                    {"login_cookie": 123},  # Non-string cookie
                    {"login_cookie": "a" * 100000},  # Extremely long cookie
                ]
                
                for i, invalid_input in enumerate(invalid_inputs):
                    response = client.post('/api/auth/twitter/validate-cookie',
                                         data=json.dumps(invalid_input),
                                         headers=headers)
                    
                    if response.status_code == 400:
                        print(f"✅ Invalid input {i+1} properly rejected")
                    else:
                        print(f"⚠️  Invalid input {i+1} not rejected: {response.status_code}")
                
                print("7. Testing error message information disclosure...")
                # Ensure error messages don't leak sensitive information
                response = client.post('/api/auth/twitter/validate-cookie',
                                     data=json.dumps({"login_cookie": "invalid"}),
                                     headers=headers)
                
                if response.status_code == 400:
                    error_msg = response.get_json().get('error', '')
                    sensitive_terms = ['password', 'secret', 'key', 'token', 'database', 'sql']
                    
                    if not any(term in error_msg.lower() for term in sensitive_terms):
                        print("✅ Error messages don't leak sensitive information")
                    else:
                        print(f"⚠️  Error message may leak sensitive info: {error_msg}")
                
                print("8. Testing user isolation...")
                # Create second user
                register_data2 = {
                    "email": f"security_test2_{timestamp}@example.com",
                    "username": f"securitytest2_{timestamp}",
                    "password": "TestPassword123!"
                }
                
                client.post('/api/auth/register', 
                           data=json.dumps(register_data2),
                           content_type='application/json')
                
                login_data2 = {
                    "email": f"security_test2_{timestamp}@example.com",
                    "password": "TestPassword123!"
                }
                
                response = client.post('/api/auth/login',
                                     data=json.dumps(login_data2),
                                     content_type='application/json')
                
                jwt_token2 = response.get_json()['access_token']
                headers2 = {
                    'Authorization': f'Bearer {jwt_token2}',
                    'Content-Type': 'application/json'
                }
                
                # User 2 should not see User 1's accounts
                response = client.get('/api/accounts', headers=headers2)
                if response.status_code == 200:
                    accounts = response.get_json().get('accounts', [])
                    if len(accounts) == 0:
                        print("✅ User isolation working - no cross-user account access")
                    else:
                        print(f"⚠️  User isolation issue - user 2 sees {len(accounts)} accounts")
        
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)
        
        print("\n" + "=" * 60)
        print("🎉 Security Feature Tests Complete!")
        
    except Exception as e:
        print(f"❌ Security test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_security_features()