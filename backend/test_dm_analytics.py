#!/usr/bin/env python3
"""
Test script for DM Analytics and Logging functionality
Tests the comprehensive logging, analytics, and retry logic
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_dm_analytics_service():
    """Test the DMAnalyticsService functionality"""
    print("=" * 60)
    print("Testing DM Analytics Service")
    print("=" * 60)
    
    try:
        from services.dm_analytics_service import DMAnalyticsService, RetryHandler
        
        # Initialize analytics service
        analytics_service = DMAnalyticsService()
        print("✓ DMAnalyticsService initialized successfully")
        
        # Test error categorization
        test_errors = [
            "Authentication failed - invalid login cookies",
            "Rate limit exceeded - too many requests",
            "User not found or account is private",
            "Connection timeout after 30 seconds",
            "Internal server error - 500"
        ]
        
        print("\nTesting error categorization:")
        for error in test_errors:
            category = analytics_service._categorize_error(error)
            print(f"  '{error[:40]}...' -> {category}")
        
        # Test sensitive data filtering
        test_data = {
            'login_cookies': 'sensitive_cookie_data',
            'user_id': '12345',
            'password': 'secret_password',
            'text': 'Hello world',
            'api_key': 'secret_key'
        }
        
        filtered_data = analytics_service._filter_sensitive_data(test_data)
        print(f"\nSensitive data filtering:")
        print(f"  Original keys: {list(test_data.keys())}")
        print(f"  Filtered data: {filtered_data}")
        
        # Test proxy credential filtering
        proxy_url = "http://user123:pass456@192.168.1.1:8080"
        filtered_proxy = analytics_service._filter_proxy_credentials(proxy_url)
        print(f"\nProxy filtering:")
        print(f"  Original: {proxy_url}")
        print(f"  Filtered: {filtered_proxy}")
        
        print("✓ DMAnalyticsService tests completed successfully")
        
    except Exception as e:
        print(f"✗ DMAnalyticsService test failed: {str(e)}")
        return False
    
    return True

def test_retry_handler():
    """Test the RetryHandler functionality"""
    print("\n" + "=" * 60)
    print("Testing Retry Handler")
    print("=" * 60)
    
    try:
        from services.dm_analytics_service import RetryHandler
        import requests
        
        # Initialize retry handler
        retry_handler = RetryHandler(max_retries=2, base_delay=0.1)
        print("✓ RetryHandler initialized successfully")
        
        # Test successful execution (no retries needed)
        def success_function():
            return "success"
        
        result = retry_handler.execute_with_retry(success_function)
        print(f"✓ Successful execution: {result}")
        
        # Test function that fails then succeeds
        attempt_count = 0
        def fail_then_succeed():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise requests.exceptions.ConnectionError("Simulated connection error")
            return "success after retry"
        
        attempt_count = 0  # Reset counter
        result = retry_handler.execute_with_retry(fail_then_succeed)
        print(f"✓ Retry success: {result} (attempts: {attempt_count})")
        
        # Test non-retryable error
        def non_retryable_error():
            raise ValueError("Invalid parameter - should not retry")
        
        try:
            retry_handler.execute_with_retry(non_retryable_error)
            print("✗ Non-retryable error test failed - should have raised exception")
        except ValueError:
            print("✓ Non-retryable error handled correctly")
        
        # Test max retries exceeded
        def always_fail():
            raise requests.exceptions.ConnectionError("Always fails")
        
        try:
            retry_handler.execute_with_retry(always_fail)
            print("✗ Max retries test failed - should have raised exception")
        except requests.exceptions.ConnectionError:
            print("✓ Max retries exceeded handled correctly")
        
        print("✓ RetryHandler tests completed successfully")
        
    except Exception as e:
        print(f"✗ RetryHandler test failed: {str(e)}")
        return False
    
    return True

def test_twitter_api_client_integration():
    """Test TwitterAPIClient integration with analytics"""
    print("\n" + "=" * 60)
    print("Testing TwitterAPIClient Analytics Integration")
    print("=" * 60)
    
    try:
        # Check if we can import and initialize the client
        from services.twitter_api_client import TwitterAPIClient
        
        # Use a dummy API key for testing
        client = TwitterAPIClient(api_key="test_api_key_12345")
        print("✓ TwitterAPIClient initialized with analytics integration")
        
        # Test analytics service integration
        if hasattr(client, 'analytics_service'):
            print("✓ Analytics service properly integrated")
        else:
            print("✗ Analytics service not found in client")
            return False
        
        # Test retry handler integration
        if hasattr(client, 'retry_handler'):
            print("✓ Retry handler properly integrated")
        else:
            print("✗ Retry handler not found in client")
            return False
        
        # Test analytics methods
        analytics_methods = ['get_dm_analytics', 'get_error_trends', 'get_performance_summary']
        for method in analytics_methods:
            if hasattr(client, method):
                print(f"✓ Method {method} available")
            else:
                print(f"✗ Method {method} not found")
                return False
        
        print("✓ TwitterAPIClient analytics integration tests completed successfully")
        
    except Exception as e:
        print(f"✗ TwitterAPIClient integration test failed: {str(e)}")
        return False
    
    return True

def test_database_models():
    """Test that database models are properly set up"""
    print("\n" + "=" * 60)
    print("Testing Database Models")
    print("=" * 60)
    
    try:
        from models import APICallLog, DirectMessage, Campaign, TwitterAccount
        
        # Check APICallLog model
        print("✓ APICallLog model imported successfully")
        
        # Check required fields exist
        required_fields = [
            'endpoint', 'method', 'status_code', 'response_time_ms',
            'success', 'error_message', 'error_category', 'retry_count'
        ]
        
        for field in required_fields:
            if hasattr(APICallLog, field):
                print(f"✓ APICallLog.{field} field exists")
            else:
                print(f"✗ APICallLog.{field} field missing")
                return False
        
        # Check DirectMessage model
        print("✓ DirectMessage model imported successfully")
        
        # Check Campaign model
        print("✓ Campaign model imported successfully")
        
        # Check TwitterAccount model
        print("✓ TwitterAccount model imported successfully")
        
        print("✓ Database models tests completed successfully")
        
    except Exception as e:
        print(f"✗ Database models test failed: {str(e)}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("DM Analytics and Logging Test Suite")
    print("=" * 60)
    
    tests = [
        ("DM Analytics Service", test_dm_analytics_service),
        ("Retry Handler", test_retry_handler),
        ("TwitterAPIClient Integration", test_twitter_api_client_integration),
        ("Database Models", test_database_models)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} tests...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test suite failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<40} {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! DM Analytics and Logging implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)