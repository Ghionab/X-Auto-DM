#!/usr/bin/env python3
"""
Test script to verify cookie parsing with the new format
"""

import json
import base64
from services.manual_account_service import ManualAccountService

def test_cookie_parsing():
    """Test parsing the new cookie format"""
    
    # Your actual response JSON
    response_json = '''{"status": "success","message": "login success.","login_cookies": "eyJndWVzdF9pZF9tYXJrZXRpbmciOiAidjElM0ExNzU3MDkwOTE5MzE4MDM0MDAiLCAiZ3Vlc3RfaWRfYWRzIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgInBlcnNvbmFsaXphdGlvbl9pZCI6ICJcInYxX2tBSGlCeldXbHBVRm5UMUNSMm9QTUE9PVwiIiwgImd1ZXN0X2lkIjogInYxJTNBMTc1NzA5MDkxOTMxODAzNDAwIiwgIl9fY2ZfYm0iOiAiVFVlSXhvSUFaZzhNY0RqMy5pcUxrSzNVLnhuRHc2VmdkcElBSnZyTjhFZy0xNzU3MDkwOTIyLTEuMC4xLjEtbk9rR1FFNXJhNDlaTmRmOTFkdjFlZm9DXzIwOWo5ZEZEQ25jdWVRLkxYNTRnSGtBd1FVV2ZxS2o0QUJ4T1ZrbUxuTHMxeTQ2UjhWUVhRMlRMT3AwWDRDLnFLNHl4M2xqYUY0b0ZYWVUuVUEiLCAiYXR0IjogIjEteWhWQnJBTlVtQnhpZllENk1mYlE3QWdXcFEzOTlwbkJDS00zZWJ6aiIsICJfdHdpdHRlcl9zZXNzIjogIkJBaDdDU0lLWm14aGMyaEpRem9uUVdOMGFXOXVRMjl1ZEhKdmJHeGxjam82Um14aGMyZzZPa1pzWVhObyUyNTBBU0dGemFIc0FCam9LUUhWelpXUjdBRG9QWTNKbFlYUmxaRjloZEd3ckNKSzF4eHFaQVRvTVkzTnlabDlwJTI1MEFaQ0lsTjJSbFltTTVNRGMwTldFM05qWm1ZVE5oTlRreE5qQXlObVl5WW1abVpqazZCMmxrSWlVME1HVmklMjUwQVpqQmpNMlJpWWpkaU1EaGlNMkl3TUdRMVltSTBOV1kyTWpkaE53JTI1M0QlMjUzRC0tMmY2YjM3ZTNhNjExMzE0YWJkNzU5NTc2YTZkODUwNDBhNGY1ZjYzNSIsICJrZHQiOiAiemVvQk1Yd09XSG5aR0tEU3ROeEZTMzNKdm1ESG93RmJCdHZwaTZKMCIsICJ0d2lkIjogIlwidT0xOTM0NjA4NDgwMTc1ODgyMjQwXCIiLCAiY3QwIjogImQ1MDYyOTdiYmZhNWZlMmNjNTk2NDhmOGVmMmYwNTQ5IiwgImF1dGhfdG9rZW4iOiAiZGMxNDVjZDRmYTEzZDY1ZmMxYWIxODBkODNhOTQxMDdkOTUxYzdjNSJ9"}'''
    
    print("Testing cookie parsing with new format...")
    print(f"Input JSON: {response_json}")
    print()
    
    # Test validation
    service = ManualAccountService()
    is_valid, validation_data = service.validate_login_cookie(response_json)
    
    print(f"Validation result: {is_valid}")
    print(f"Validation data: {validation_data}")
    print()
    
    # Test account info extraction
    account_info = service.extract_account_info(response_json)
    print(f"Account info: {account_info}")
    print()
    
    # Let's also decode the base64 manually to see what's inside
    try:
        parsed = json.loads(response_json)
        login_cookies_b64 = parsed['login_cookies']
        decoded = base64.b64decode(login_cookies_b64).decode('utf-8')
        cookie_data = json.loads(decoded)
        
        print("Decoded cookie data:")
        for key, value in cookie_data.items():
            print(f"  {key}: {value}")
        print()
        
        # Check for required fields
        print("Required field check:")
        print(f"  auth_token: {'✓' if 'auth_token' in cookie_data else '✗'}")
        print(f"  twid: {'✓' if 'twid' in cookie_data else '✗'}")
        
    except Exception as e:
        print(f"Manual decode error: {e}")

if __name__ == "__main__":
    test_cookie_parsing()