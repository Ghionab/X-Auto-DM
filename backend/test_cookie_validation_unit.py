#!/usr/bin/env python3
"""
Unit test for cookie validation with the new format
"""

import json
import base64
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cookie_validation_logic():
    """Test the cookie validation logic without Flask dependencies"""
    
    # Your actual response JSON
    response_json = '''{"status": "success","message": "login success.","login_cookies": "eyJndWVzdF9pZF9tYXJrZXRpbmciOiAidjElM0ExNzU3MDkwOTE5MzE4MDM0MDAiLCAiZ3Vlc3RfaWRfYWRzIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgInBlcnNvbmFsaXphdGlvbl9pZCI6ICJcInYxX2tBSGlCeldXbHBVRm5UMUNSMm9QTUE9PVwiIiwgImd1ZXN0X2lkIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgIl9fY2ZfYm0iOiAiVFVlSXhvSUFaZzhNY0RqMy5pcUxrSzNVLnhuRHc2VmdkcElBSnZyTjhFZy0xNzU3MDkwOTIyLTEuMC4xLjEtbk9rR1FFNXJhNDlaTmRmOTFkdjFlZm9DXzIwOWo5ZEZEQ25jdWVRLkxYNTRnSGtBd1FVV2ZxS2o0QUJ4T1ZrbUxuTHMxeTQ2UjhWUVhRMlRMT3AwWDRDLnFLNHl4M2xqYUY0b0ZYWVUuVUEiLCAiYXR0IjogIjEteWhWQnJBTlVtQnhpZllENk1mYlE3QWdXcFEzOTlwbkJDS00zZWJ6aiIsICJfdHdpdHRlcl9zZXNzIjogIkJBaDdDU0lLWm14aGMyaEpRem9uUVdOMGFXOXVRMjl1ZEhKdmJHeGxjam82Um14aGMyZzZPa1pzWVhObyUyNTBBU0dGemFIc0FCam9LUUhWelpXUjdBRG9QWTNKbFlYUmxaRjloZEd3ckNKSzF4eHFaQVRvTVkzTnlabDlwJTI1MEFaQ0lsTjJSbFltTTVNRGMwTldFM05qWm1ZVE5oTlRreE5qQXlObVl5WW1abVpqazZCMmxrSWlVME1HVmklMjUwQVpqQmpNMlJpWWpkaU1EaGlNMkl3TUdRMVltSTBOV1kyTWpkaE53JTI1M0QlMjUzRC0tMmY2YjM3ZTNhNjExMzE0YWJkNzU5NTc2YTZkODUwNDBhNGY1ZjYzNSIsICJrZHQiOiAiemVvQk1Yd09XSG5aR0tEU3ROeEZTMzNKdm1ESG93RmJCdHZwaTZKMCIsICJ0d2lkIjogIlwidT0xOTM0NjA4NDgwMTc1ODgyMjQwXCIiLCAiY3QwIjogImQ1MDYyOTdiYmZhNWZlMmNjNTk2NDhmOGVmMmYwNTQ5IiwgImF1dGhfdG9rZW4iOiAiZGMxNDVjZDRmYTEzZDY1ZmMxYWIxODBkODNhOTQxMDdkOTUxYzdjNSJ9"}'''
    
    def validate_cookie_logic(login_cookie: str):
        """Replicate the validation logic"""
        try:
            if not login_cookie or not isinstance(login_cookie, str):
                return False, {'error': 'Cookie must be a non-empty string'}
            
            # Clean up the cookie string
            cleaned_cookie = login_cookie.strip()
            
            # Try to parse as JSON first
            try:
                parsed_data = json.loads(cleaned_cookie)
                
                # Check if this is a response format with login_cookies field
                if isinstance(parsed_data, dict) and 'login_cookies' in parsed_data:
                    # Extract the actual cookie data from login_cookies field
                    login_cookies_str = parsed_data['login_cookies']
                    
                    # Decode base64 if needed
                    try:
                        decoded_cookies = base64.b64decode(login_cookies_str).decode('utf-8')
                        cookie_data = json.loads(decoded_cookies)
                    except:
                        # If base64 decode fails, try direct JSON parse
                        cookie_data = json.loads(login_cookies_str)
                else:
                    # Direct cookie JSON format
                    cookie_data = parsed_data
                    
            except json.JSONDecodeError:
                return False, {'error': 'Invalid JSON format'}
            
            # Validate required fields for TwitterAPI.io
            required_fields = ['auth_token']
            missing_fields = []
            
            for field in required_fields:
                if field not in cookie_data or not cookie_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, {
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'required_fields': required_fields,
                    'found_fields': list(cookie_data.keys())
                }
            
            # Check for user identification (twid or user_id)
            has_user_id = bool(cookie_data.get('twid') or cookie_data.get('user_id'))
            if not has_user_id:
                return False, {
                    'error': 'Cookie must contain user identification (twid or user_id field)',
                    'details': 'Unable to determine account owner from cookie data'
                }
            
            return True, {
                'valid': True,
                'fields_found': list(cookie_data.keys()),
                'has_auth_token': bool(cookie_data.get('auth_token')),
                'has_user_id': has_user_id,
                'cookie_size': len(cleaned_cookie)
            }
            
        except Exception as e:
            return False, {'error': f'Cookie validation failed: {str(e)}'}
    
    print("Testing cookie validation logic...")
    print()
    
    # Test with response format
    is_valid, result = validate_cookie_logic(response_json)
    print(f"Response format validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")
    print(f"Result: {result}")
    print()
    
    # Test with direct cookie format (extract from response)
    parsed = json.loads(response_json)
    login_cookies_b64 = parsed['login_cookies']
    decoded = base64.b64decode(login_cookies_b64).decode('utf-8')
    
    is_valid_direct, result_direct = validate_cookie_logic(decoded)
    print(f"Direct cookie validation: {'✓ PASSED' if is_valid_direct else '✗ FAILED'}")
    print(f"Result: {result_direct}")
    print()
    
    # Test with invalid format
    is_valid_invalid, result_invalid = validate_cookie_logic('{"invalid": "data"}')
    print(f"Invalid format validation: {'✓ PASSED (correctly rejected)' if not is_valid_invalid else '✗ FAILED (should reject)'}")
    print(f"Result: {result_invalid}")
    
    return is_valid and is_valid_direct and not is_valid_invalid

if __name__ == "__main__":
    success = test_cookie_validation_logic()
    print(f"\nOverall test result: {'✓ ALL TESTS PASSED' if success else '✗ SOME TESTS FAILED'}")
    sys.exit(0 if success else 1)