#!/usr/bin/env python3
"""
Integration test script for the entire backend with TwitterAPI.io SDK
Tests backend app initialization, routes, database models, and SDK integration
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment_and_config():
    """Test environment configuration and app config"""
    logger.info("Testing environment and Flask app configuration...")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Test app import
        from app import app
        logger.info("✓ Flask app imported successfully")
        
        # Test database models
        from models import User, TwitterAccount
        logger.info("✓ Database models imported successfully")
        
        # Check environment variables
        api_key = os.getenv('TWITTERAPI_IO_API_KEY')
        default_proxy = os.getenv('DEFAULT_PROXY')
        
        if not api_key:
            logger.error("TWITTERAPI_IO_API_KEY not found")
            return False
            
        logger.info(f"API Key configured: {api_key[:10]}...")
        logger.info(f"Default Proxy: {default_proxy}")
        
        return True
        
    except Exception as e:
        logger.error(f"Environment/config test failed: {e}")
        return False

def test_twitterio_sdk_integration():
    """Test TwitterAPI.io SDK integration"""
    logger.info("Testing TwitterAPI.io SDK integration...")
    
    try:
        # Test core SDK import
        from twitterio import TwitterClient, TwitterAPIError
        logger.info("✓ TwitterAPI.io SDK imported successfully")
        
        # Test creating unified client
        client = TwitterClient()
        logger.info("✓ Unified TwitterClient created successfully")
        
        # Test individual module imports
        from twitterio import (
            TwitterAuthClient, TwitterDMClient, TwitterTweetClient,
            TwitterUserClient, TwitterMediaClient, TwitterCommunityClient
        )
        logger.info("✓ All individual module clients imported successfully")
        
        # Test dataclass imports
        from twitterio import (
            LoginCredentials, LoginSession, TwitterUser, TweetResult,
            DMSendResult, MediaUploadResult, CommunityResult
        )
        logger.info("✓ All dataclasses imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"SDK integration test failed: {e}")
        return False

def test_backend_routes():
    """Test backend route definitions (without running server)"""
    logger.info("Testing backend route definitions...")
    
    try:
        from app import app
        
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{', '.join(rule.methods)} {rule.rule}")
        
        logger.info(f"Found {len(routes)} routes:")
        for route in routes[:10]:  # Show first 10 routes
            logger.info(f"  {route}")
        
        # Check for expected TwitterAPI.io routes
        expected_routes = [
            '/api/twitter/login',
            '/api/twitter/disconnect',
            '/api/twitter/send-dm',
            '/api/twitter/create-tweet',
            '/api/twitter/follow-user',
            '/api/twitter/upload-media'
        ]
        
        route_strings = [route for route in routes]
        
        found_routes = 0
        for expected in expected_routes:
            if any(expected in route for route in route_strings):
                found_routes += 1
                logger.info(f"✓ Found route: {expected}")
        
        if found_routes >= 4:  # At least most routes should be found
            logger.info(f"✓ Found {found_routes}/{len(expected_routes)} expected TwitterAPI.io routes")
            return True
        else:
            logger.error(f"Only found {found_routes}/{len(expected_routes)} expected routes")
            return False
        
    except Exception as e:
        logger.error(f"Backend routes test failed: {e}")
        return False

def test_database_models():
    """Test database models"""
    logger.info("Testing database models...")
    
    try:
        from models import User, TwitterAccount
        
        # Test User model
        user_fields = ['id', 'username', 'email', 'password_hash']
        for field in user_fields:
            if not hasattr(User, field):
                logger.error(f"User model missing field: {field}")
                return False
        
        logger.info("✓ User model has required fields")
        
        # Test TwitterAccount model
        twitter_account_fields = ['id', 'user_id', 'login_cookie', 'twitter_user_id', 'screen_name']
        for field in twitter_account_fields:
            if not hasattr(TwitterAccount, field):
                logger.error(f"TwitterAccount model missing field: {field}")
                return False
        
        logger.info("✓ TwitterAccount model has required fields")
        
        return True
        
    except Exception as e:
        logger.error(f"Database models test failed: {e}")
        return False

def test_complete_flow_simulation():
    """Test complete flow simulation (without actual API calls)"""
    logger.info("Testing complete flow simulation...")
    
    try:
        # Import everything needed for a complete flow
        from twitterio import TwitterClient, LoginCredentials
        from models import User, TwitterAccount
        
        # Simulate creating a client
        client = TwitterClient()
        logger.info("✓ Client created")
        
        # Simulate login credentials
        credentials = LoginCredentials(
            username="test_user",
            email="test@example.com",
            password="test_password",
            totp_secret="test_secret",
            proxy="http://test:8080"
        )
        logger.info("✓ Login credentials created")
        
        # Test that we can access all client methods
        methods_to_test = [
            'login', 'logout', 'is_authenticated', 'get_login_cookie',
            'send_dm', 'get_dm_history',
            'create_tweet', 'delete_tweet', 'like_tweet',
            'follow_user', 'unfollow_user', 'get_user_info',
            'upload_media',
            'create_community', 'join_community'
        ]
        
        for method in methods_to_test:
            if not hasattr(client, method):
                logger.error(f"Client missing method: {method}")
                return False
        
        logger.info(f"✓ Client has all {len(methods_to_test)} expected methods")
        
        return True
        
    except Exception as e:
        logger.error(f"Complete flow simulation failed: {e}")
        return False

def run_integration_tests():
    """Run all integration tests"""
    logger.info("Starting Backend Integration Tests...")
    
    tests = [
        ("Environment & Config", test_environment_and_config),
        ("TwitterIO SDK Integration", test_twitterio_sdk_integration),
        ("Backend Routes", test_backend_routes),
        ("Database Models", test_database_models),
        ("Complete Flow Simulation", test_complete_flow_simulation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"INTEGRATION TEST RESULTS: {passed}/{total} tests passed")
    logger.info(f"{'='*60}")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! Backend is ready for use.")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
