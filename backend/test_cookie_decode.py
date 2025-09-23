#!/usr/bin/env python3
"""
Simple test to decode the cookie format
"""

import json
import base64

def test_cookie_decode():
    """Test decoding the cookie format"""
    
    # Your actual response JSON
    response_json = '''{"status": "success","message": "login success.","login_cookies": "eyJndWVzdF9pZF9tYXJrZXRpbmciOiAidjElM0ExNzU3MDkwOTE5MzE4MDM0MDAiLCAiZ3Vlc3RfaWRfYWRzIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgInBlcnNvbmFsaXphdGlvbl9pZCI6ICJcInYxX2tBSGlCeldXbHBVRm5UMUNSMm9QTUE9PVwiIiwgImd1ZXN0X2lkIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgIl9fY2ZfYm0iOiAiVFVlSXhvSUFaZzhNY0RqMy5pcUxrSzNVLnhuRHc2VmdkcElBSnZyTjhFZy0xNzU3MDkwOTIyLTEuMC4xLjEtbk9rR1FFNXJhNDlaTmRmOTFkdjFlZm9DXzIwOWo5ZEZEQ25jdWVRLkxYNTRnSGtBd1FVV2ZxS2o0QUJ4T1ZrbUxuTHMxeTQ2UjhWUVhRMlRMT3AwWDRDLnFLNHl4M2xqYUY0b0ZYWVUuVUEiLCAiYXR0IjogIjEteWhWQnJBTlVtQnhpZllENk1mYlE3QWdXcFEzOTlwbkJDS00zZWJ6aiIsICJfdHdpdHRlcl9zZXNzIjogIkJBaDdDU0lLWm14aGMyaEpRem9uUVdOMGFXOXVRMjl1ZEhKdmJHeGxjam82Um14aGMyZzZPa1pzWVhObyUyNTBBU0dGemFIc0FCam9LUUhWelpXUjdBRG9QWTNKbFlYUmxaRjloZEd3ckNKSzF4eHFaQVRvTVkzTnlabDlwJTI1MEFaQ0lsTjJSbFltTTVNRGMwTldFM05qWm1ZVE5oTlRreE5qQXlObVl5WW1abVpqazZCMmxrSWlVME1HVmklMjUwQVpqQmpNMlJpWWpkaU1EaGlNMkl3TUdRMVltSTBOV1kyTWpkaE53JTI1M0QlMjUzRC0tMmY2YjM3ZTNhNjExMzE0YWJkNzU5NTc2YTZkODUwNDBhNGY1ZjYzNSIsICJrZHQiOiAiemVvQk1Yd09XSG5aR0tEU3ROeEZTMzNKdm1ESG93RmJCdHZwaTZKMCIsICJ0d2lkIjogIlwidT0xOTM0NjA4NDgwMTc1ODgyMjQwXCIiLCAiY3QwIjogImQ1MDYyOTdiYmZhNWZlMmNjNTk2NDhmOGVmMmYwNTQ5IiwgImF1dGhfdG9rZW4iOiAiZGMxNDVjZDRmYTEzZDY1ZmMxYWIxODBkODNhOTQxMDdkOTUxYzdjNSJ9"}'''
    
    print("Testing cookie decoding...")
    print()
    
    try:
        # Parse the response JSON
        parsed = json.loads(response_json)
        print(f"Response status: {parsed.get('status')}")
        print(f"Response message: {parsed.get('message')}")
        print()
        
        # Extract and decode the login_cookies
        login_cookies_b64 = parsed['login_cookies']
        print(f"Base64 cookie length: {len(login_cookies_b64)}")
        
        # Decode base64
        decoded = base64.b64decode(login_cookies_b64).decode('utf-8')
        print(f"Decoded cookie: {decoded}")
        print()
        
        # Parse the decoded JSON
        cookie_data = json.loads(decoded)
        
        print("Cookie fields found:")
        for key, value in cookie_data.items():
            print(f"  {key}: {value}")
        print()
        
        # Check for required fields
        print("Field validation:")
        print(f"  auth_token: {'✓ FOUND' if 'auth_token' in cookie_data else '✗ MISSING'}")
        print(f"  twid: {'✓ FOUND' if 'twid' in cookie_data else '✗ MISSING'}")
        
        # Extract user ID from twid
        if 'twid' in cookie_data:
            twid = cookie_data['twid']
            print(f"  twid value: {twid}")
            
            # Extract user ID
            import re
            user_id_match = re.search(r'u=(\d+)', twid.strip('"'))
            if user_id_match:
                user_id = user_id_match.group(1)
                print(f"  extracted user_id: {user_id}")
            else:
                print("  could not extract user_id from twid")
        
        print()
        print("✓ Cookie format is valid and contains required fields!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cookie_decode()