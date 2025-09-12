#!/usr/bin/env python3
"""
Test DM sending with real cookie from database
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging
from app import create_app
from models import db, TwitterAccount
from twitterio.dm import send_direct_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_real_dm():
    """Test DM with real cookie from database"""
    
    app = create_app()
    
    with app.app_context():
        # Get the first Twitter account
        account = TwitterAccount.query.first()
        
        if not account:
            logger.error("No Twitter accounts found in database")
            return False
        
        if not account.login_cookie:
            logger.error(f"Account {account.username} has no login cookie")
            return False
        
        logger.info(f"Testing DM with account: {account.username}")
        logger.info(f"Cookie length: {len(account.login_cookie)}")
        logger.info(f"Using proxy: {os.getenv('DEFAULT_PROXY')}")
        
        try:
            result = send_direct_message(
                login_cookie=account.login_cookie,
                user_id="1934608480175882240",  # Test user ID
                text="Test message - proxy fix verification"
            )
            
            logger.info("✅ DM send successful!")
            logger.info(f"Result: {result}")
            return True
            
        except Exception as e:
            logger.error(f"❌ DM send failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = test_real_dm()
    if success:
        print("\n🎉 COMPLETE SUCCESS! Both proxy and cookie issues are resolved!")
    else:
        print("\n❌ Still having issues with DM sending.")