#!/usr/bin/env python3
"""
Test script to verify enhanced API response logging
This will help debug Twitter authentication issues
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific loggers to INFO level to see all details
logging.getLogger('twitterapi_core').setLevel(logging.INFO)
logging.getLogger('twitterio.auth').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.WARNING)  # Reduce requests noise
logging.getLogger('urllib3').setLevel(logging.WARNING)   # Reduce urllib3 noise

def test_api_logging():
    """Test the enhanced API logging functionality"""
    print("=" * 80)
    print("TESTING ENHANCED API LOGGING")
    print("=" * 80)
    
    try:
        from twitterio.auth import TwitterAuthClient, LoginCredentials
        from twitterapi_core import TwitterAPIError
        
        print("✓ Imported TwitterAPI modules successfully")
        
        # Create auth client
        auth_client = TwitterAuthClient()
        print("✓ Created TwitterAuthClient")
        
        # Test with dummy credentials to see the API response
        # This will fail but we'll see the full API response
        dummy_credentials = LoginCredentials(
            username="test_user",
            email="test@example.com", 
            password="test_password",
            totp_secret="123456"
        )
        
        print("\n" + "=" * 60)
        print("ATTEMPTING LOGIN WITH DUMMY CREDENTIALS")
        print("(This will fail but show full API response)")
        print("=" * 60)
        
        try:
            session = auth_client.login(dummy_credentials)
            print("✗ Unexpected success - this should have failed")
        except TwitterAPIError as e:
            print(f"\n✓ Expected TwitterAPI error occurred: {e}")
            if hasattr(e, 'status_code'):
                print(f"✓ Status code: {e.status_code}")
            if hasattr(e, 'response_data'):
                print(f"✓ Response data available: {e.response_data is not None}")
        except Exception as e:
            print(f"✗ Unexpected error type: {type(e).__name__}: {e}")
        
        print("\n" + "=" * 60)
        print("TESTING API CONNECTION")
        print("=" * 60)
        
        # Test API connection
        try:
            from twitterapi_core import get_core_client
            core_client = get_core_client()
            
            print("Testing API connection...")
            is_connected = core_client.test_connection()
            print(f"API Connection test result: {is_connected}")
            
        except Exception as e:
            print(f"Connection test error: {e}")
        
        print("\n" + "=" * 60)
        print("LOGGING TEST COMPLETE")
        print("=" * 60)
        print("If you see detailed API request/response logs above,")
        print("the enhanced logging is working correctly!")
        print("You should see:")
        print("- API Request details (method, URL, headers, data)")
        print("- API Response details (status, headers, body)")
        print("- Error details with full response data")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure all TwitterAPI modules are properly installed")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_real_credentials():
    """Test with real credentials if provided via environment variables"""
    print("\n" + "=" * 80)
    print("TESTING WITH REAL CREDENTIALS (if provided)")
    print("=" * 80)
    
    # Check for real credentials in environment
    username = os.getenv('TEST_TWITTER_USERNAME')
    email = os.getenv('TEST_TWITTER_EMAIL')
    password = os.getenv('TEST_TWITTER_PASSWORD')
    totp_secret = os.getenv('TEST_TWITTER_TOTP')
    
    if not all([username, email, password, totp_secret]):
        print("No real credentials provided via environment variables.")
        print("To test with real credentials, set:")
        print("- TEST_TWITTER_USERNAME")
        print("- TEST_TWITTER_EMAIL") 
        print("- TEST_TWITTER_PASSWORD")
        print("- TEST_TWITTER_TOTP")
        return True
    
    try:
        from twitterio.auth import TwitterAuthClient, LoginCredentials
        
        auth_client = TwitterAuthClient()
        
        real_credentials = LoginCredentials(
            username=username,
            email=email,
            password=password,
            totp_secret=totp_secret
        )
        
        print(f"Attempting login with real credentials for: {username}")
        print("(Check the logs above for detailed API request/response)")
        
        try:
            session = auth_client.login(real_credentials)
            print(f"✓ Successfully authenticated: {username}")
            print(f"✓ Login cookie received: {session.login_cookie[:20]}...")
            print(f"✓ Session status: {session.status}")
            print(f"✓ Session message: {session.message}")
            return True
            
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            print("Check the detailed API logs above to see what went wrong")
            return False
            
    except Exception as e:
        print(f"✗ Error testing real credentials: {e}")
        return False

def main():
    """Run all logging tests"""
    print("Enhanced API Logging Test Suite")
    print("This will help debug Twitter authentication issues")
    
    # Test basic logging functionality
    success1 = test_api_logging()
    
    # Test with real credentials if available
    success2 = test_with_real_credentials()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if success1 and success2:
        print("✅ All tests completed successfully!")
        print("Enhanced logging is working - you should see detailed API logs above.")
    else:
        print("❌ Some tests failed - check the output above for details.")
    
    print("\nTo use this enhanced logging in your app:")
    print("1. The logging is now automatically enabled in the TwitterAPI modules")
    print("2. Set logging level to INFO to see all API details")
    print("3. Check console output when making Twitter API calls")
    print("4. Look for 'API Request' and 'API Response' log entries")

if __name__ == "__main__":
    main()