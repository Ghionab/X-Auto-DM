#!/usr/bin/env python3
"""
Debug Twitter Connection Issues
This script helps debug specific Twitter authentication problems
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
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

def debug_twitter_auth():
    """Debug Twitter authentication with your specific credentials"""
    print("=" * 80)
    print("TWITTER AUTHENTICATION DEBUG TOOL")
    print("=" * 80)
    print("This tool will show you EXACTLY what's happening with your Twitter login")
    print("including full API requests and responses.")
    print()
    
    # Get credentials from user input
    print("Please enter your Twitter credentials:")
    username = input("Twitter Username: ").strip()
    email = input("Twitter Email: ").strip()
    password = input("Twitter Password: ").strip()
    totp_secret = input("TOTP Secret (2FA): ").strip()
    
    if not all([username, email, password, totp_secret]):
        print("❌ All fields are required!")
        return False
    
    print("\n" + "=" * 80)
    print("ATTEMPTING TWITTER LOGIN")
    print("=" * 80)
    print("Watch the detailed logs below to see exactly what happens...")
    print()
    
    try:
        from twitterio.auth import TwitterAuthClient, LoginCredentials
        from twitterapi_core import TwitterAPIError
        
        # Create auth client
        auth_client = TwitterAuthClient()
        
        # Create credentials
        credentials = LoginCredentials(
            username=username,
            email=email,
            password=password,
            totp_secret=totp_secret
        )
        
        # Attempt login
        try:
            session = auth_client.login(credentials)
            
            print("\n" + "🎉" * 20)
            print("SUCCESS! Twitter authentication worked!")
            print("🎉" * 20)
            print(f"Username: {session.username}")
            print(f"Status: {session.status}")
            print(f"Message: {session.message}")
            print(f"Login Cookie: {session.login_cookie[:50]}...")
            print()
            print("You can now use this account for DM campaigns!")
            return True
            
        except TwitterAPIError as e:
            print("\n" + "❌" * 20)
            print("AUTHENTICATION FAILED")
            print("❌" * 20)
            print(f"Error: {e}")
            
            if hasattr(e, 'status_code'):
                print(f"HTTP Status: {e.status_code}")
            
            if hasattr(e, 'response_data') and e.response_data:
                print(f"API Response: {e.response_data}")
                
                # Analyze the specific error
                response = e.response_data
                if response.get('status') == 'error':
                    message = response.get('message', '')
                    
                    print("\n" + "🔍" * 20)
                    print("ERROR ANALYSIS")
                    print("🔍" * 20)
                    
                    if 'blocked' in message.lower():
                        print("❌ ACCOUNT BLOCKED/SUSPENDED")
                        print("Your Twitter account appears to be blocked or suspended.")
                        print("This could be due to:")
                        print("- Too many login attempts")
                        print("- Suspicious activity detection")
                        print("- Account temporarily locked")
                        print("- Using automation tools")
                        print()
                        print("SOLUTIONS:")
                        print("1. Wait 24-48 hours before trying again")
                        print("2. Try logging in from Twitter.com first")
                        print("3. Complete any security challenges on Twitter.com")
                        print("4. Use a different IP address/proxy")
                        
                    elif 'invalid' in message.lower() or 'wrong' in message.lower():
                        print("❌ INVALID CREDENTIALS")
                        print("One or more of your credentials is incorrect.")
                        print()
                        print("SOLUTIONS:")
                        print("1. Double-check your username, email, and password")
                        print("2. Verify your TOTP secret is correct")
                        print("3. Try logging in to Twitter.com manually first")
                        
                    elif 'totp' in message.lower() or '2fa' in message.lower():
                        print("❌ 2FA/TOTP ISSUE")
                        print("There's an issue with your 2FA setup.")
                        print()
                        print("SOLUTIONS:")
                        print("1. Verify your TOTP secret is correct")
                        print("2. Make sure your authenticator app is synced")
                        print("3. Try generating a new TOTP secret")
                        
                    elif 'rate' in message.lower() or 'limit' in message.lower():
                        print("❌ RATE LIMITED")
                        print("Too many requests have been made.")
                        print()
                        print("SOLUTIONS:")
                        print("1. Wait 15-30 minutes before trying again")
                        print("2. Use a different proxy/IP address")
                        
                    else:
                        print("❌ OTHER ERROR")
                        print("The error doesn't match common patterns.")
                        print(f"Full message: {message}")
                        print()
                        print("SOLUTIONS:")
                        print("1. Try again in a few minutes")
                        print("2. Check if your account is accessible on Twitter.com")
                        print("3. Contact support if the issue persists")
            
            return False
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_connection():
    """Test basic API connectivity"""
    print("\n" + "=" * 80)
    print("TESTING API CONNECTION")
    print("=" * 80)
    
    try:
        from twitterapi_core import get_core_client
        
        core_client = get_core_client()
        print("Testing connection to TwitterAPI.io...")
        
        is_connected = core_client.test_connection()
        
        if is_connected:
            print("✅ API connection successful!")
            print("Your API key is valid and the service is accessible.")
        else:
            print("❌ API connection failed!")
            print("Check your API key and internet connection.")
            
        return is_connected
        
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def main():
    """Main debug function"""
    print("Twitter Authentication Debug Tool")
    print("This tool will help you debug connection issues with detailed logging.")
    print()
    
    # Test API connection first
    if not test_api_connection():
        print("❌ Cannot proceed - API connection failed")
        return
    
    # Debug authentication
    success = debug_twitter_auth()
    
    print("\n" + "=" * 80)
    print("DEBUG SESSION COMPLETE")
    print("=" * 80)
    
    if success:
        print("✅ Your Twitter authentication is working!")
    else:
        print("❌ Twitter authentication failed - check the analysis above")
        print()
        print("GENERAL TIPS:")
        print("1. Make sure your Twitter account is not suspended")
        print("2. Try logging in to Twitter.com manually first")
        print("3. Wait some time between login attempts")
        print("4. Use different proxies if available")
        print("5. Check if your 2FA is properly configured")

if __name__ == "__main__":
    main()