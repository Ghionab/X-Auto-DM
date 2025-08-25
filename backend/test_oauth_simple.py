#!/usr/bin/env python3
"""
Simple test for X OAuth Integration - Basic functionality verification
"""

import os
import sys
from cryptography.fernet import Fernet

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_encryption_key_generation():
    """Test that we can generate a proper encryption key"""
    print("Testing encryption key generation...")
    
    # Generate a proper Fernet key
    key = Fernet.generate_key()
    print(f"Generated key: {key.decode()}")
    
    # Test encryption/decryption
    cipher_suite = Fernet(key)
    test_data = "test_oauth_token_12345"
    
    encrypted = cipher_suite.encrypt(test_data.encode())
    decrypted = cipher_suite.decrypt(encrypted).decode()
    
    assert decrypted == test_data
    print("✓ Encryption/decryption works correctly")

def test_oauth_service_basic():
    """Test basic OAuth service functionality"""
    print("\nTesting OAuth service basic functionality...")
    
    # Set up environment
    os.environ['TOKEN_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    os.environ['X_API_CONSUMER_KEY'] = 'test_consumer_key'
    os.environ['X_API_CONSUMER_SECRET'] = 'test_consumer_secret'
    
    try:
        from app import create_app
        from services.x_oauth_service import XOAuthService
        
        # Create Flask app context
        app = create_app('testing')
        with app.app_context():
            oauth_service = XOAuthService()
            print("✓ OAuth service initialized successfully")
            
            # Test nonce generation
            nonce1 = oauth_service._generate_nonce()
            nonce2 = oauth_service._generate_nonce()
            assert nonce1 != nonce2
            print("✓ Nonce generation works")
            
            # Test timestamp generation
            timestamp = oauth_service._generate_timestamp()
            assert len(timestamp) > 0
            print("✓ Timestamp generation works")
            
            # Test percent encoding
            encoded = oauth_service._percent_encode("hello world!")
            assert encoded == "hello%20world%21"
            print("✓ Percent encoding works")
        
    except Exception as e:
        print(f"✗ OAuth service test failed: {e}")
        return False
    
    return True

def test_token_storage_basic():
    """Test basic token storage functionality"""
    print("\nTesting token storage basic functionality...")
    
    # Set up environment
    os.environ['TOKEN_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    
    try:
        from services.token_storage_service import TokenStorageService
        
        token_storage = TokenStorageService()
        print("✓ Token storage service initialized successfully")
        
        # Test encryption/decryption
        original_token = "test_access_token_12345"
        encrypted = token_storage.encrypt_token(original_token)
        decrypted = token_storage.decrypt_token(encrypted)
        
        assert decrypted == original_token
        print("✓ Token encryption/decryption works")
        
    except Exception as e:
        print(f"✗ Token storage test failed: {e}")
        return False
    
    return True

def main():
    """Run all basic tests"""
    print("X OAuth Integration - Basic Functionality Tests")
    print("=" * 50)
    
    try:
        test_encryption_key_generation()
        
        if test_oauth_service_basic():
            print("✓ OAuth service tests passed")
        else:
            print("✗ OAuth service tests failed")
            return False
        
        if test_token_storage_basic():
            print("✓ Token storage tests passed")
        else:
            print("✗ Token storage tests failed")
            return False
        
        print("\n" + "=" * 50)
        print("✓ All basic functionality tests passed!")
        print("\nThe X OAuth integration is ready for use.")
        print("\nNext steps:")
        print("1. Set up proper environment variables:")
        print("   - X_API_CONSUMER_KEY")
        print("   - X_API_CONSUMER_SECRET") 
        print("   - TOKEN_ENCRYPTION_KEY")
        print("   - X_OAUTH_CALLBACK_URL")
        print("2. Test with real X API credentials")
        print("3. Test the complete OAuth flow in the frontend")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Tests failed with error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)