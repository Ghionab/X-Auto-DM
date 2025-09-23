"""
Test cookie encryption and decryption functionality
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_cookie_encryption_decryption():
    """Test that cookie encryption and decryption works correctly"""
    print("Testing cookie encryption and decryption...")
    
    # Set up environment variable for testing
    os.environ['COOKIE_ENCRYPTION_KEY'] = 'test-encryption-key-for-testing-only'
    
    from services.cookie_encryption import CookieManager
    
    # Test cookie
    test_cookie = "test_login_cookie_value_123456789"
    
    # Initialize cookie manager
    cookie_manager = CookieManager()
    
    # Test encryption
    encrypted_cookie = cookie_manager.store_cookie(test_cookie, expiration_hours=24)
    assert encrypted_cookie is not None
    assert encrypted_cookie != test_cookie  # Should be encrypted
    print("✓ Cookie encryption successful")
    
    # Test decryption
    decrypted_cookie = cookie_manager.retrieve_cookie(encrypted_cookie)
    assert decrypted_cookie == test_cookie
    print("✓ Cookie decryption successful")
    
    # Test validation
    is_valid = cookie_manager.is_cookie_valid(encrypted_cookie)
    assert is_valid == True
    print("✓ Cookie validation successful")
    
    print("✓ All cookie tests passed!")

if __name__ == "__main__":
    test_cookie_encryption_decryption()