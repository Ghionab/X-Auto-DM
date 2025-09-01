"""
Cookie Encryption Service for secure storage of login cookies
Provides encryption/decryption and expiration management
"""

import os
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CookieEncryption:
    """
    Handles encryption and decryption of login cookies for secure storage
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize cookie encryption service
        
        Args:
            encryption_key: Optional encryption key, will use env var if not provided
        """
        self.logger = logging.getLogger(__name__)
        
        # Get encryption key from parameter or environment
        key = encryption_key or os.getenv('COOKIE_ENCRYPTION_KEY')
        
        if not key:
            raise ValueError("COOKIE_ENCRYPTION_KEY environment variable is required")
        
        # Generate Fernet key from the provided key
        self.cipher_suite = self._create_cipher_suite(key)
    
    def _create_cipher_suite(self, key: str) -> Fernet:
        """
        Create Fernet cipher suite from string key
        
        Args:
            key: String key for encryption
            
        Returns:
            Fernet cipher suite
        """
        # Use PBKDF2 to derive a proper key from the string
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'twitterapi_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        
        # Derive key and create Fernet instance
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)
    
    def encrypt_cookie(self, cookie: str, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Encrypt login cookie for secure storage
        
        Args:
            cookie: Login cookie string to encrypt
            expires_at: Optional expiration datetime
            
        Returns:
            Dictionary with encrypted cookie and metadata
            
        Raises:
            ValueError: If cookie is empty or invalid
            Exception: If encryption fails
        """
        if not cookie or not isinstance(cookie, str):
            raise ValueError("Cookie must be a non-empty string")
        
        try:
            # Create cookie data with metadata
            cookie_data = {
                'cookie': cookie,
                'encrypted_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
            # Convert to JSON string and encrypt
            import json
            cookie_json = json.dumps(cookie_data)
            encrypted_cookie = self.cipher_suite.encrypt(cookie_json.encode())
            
            self.logger.info("Cookie encrypted successfully")
            
            return {
                'encrypted_cookie': base64.urlsafe_b64encode(encrypted_cookie).decode(),
                'encrypted_at': datetime.utcnow(),
                'expires_at': expires_at
            }
            
        except Exception as e:
            self.logger.error(f"Cookie encryption failed: {str(e)}")
            raise Exception(f"Failed to encrypt cookie: {str(e)}")
    
    def decrypt_cookie(self, encrypted_cookie: str) -> Dict[str, Any]:
        """
        Decrypt stored login cookie
        
        Args:
            encrypted_cookie: Base64 encoded encrypted cookie
            
        Returns:
            Dictionary with decrypted cookie and metadata
            
        Raises:
            ValueError: If encrypted_cookie is invalid
            Exception: If decryption fails
        """
        if not encrypted_cookie or not isinstance(encrypted_cookie, str):
            raise ValueError("Encrypted cookie must be a non-empty string")
        
        try:
            # Decode from base64 and decrypt
            encrypted_data = base64.urlsafe_b64decode(encrypted_cookie.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            
            # Parse JSON data
            import json
            cookie_data = json.loads(decrypted_data.decode())
            
            # Parse datetime strings back to datetime objects
            encrypted_at = datetime.fromisoformat(cookie_data['encrypted_at'])
            expires_at = None
            if cookie_data.get('expires_at'):
                expires_at = datetime.fromisoformat(cookie_data['expires_at'])
            
            self.logger.info("Cookie decrypted successfully")
            
            return {
                'cookie': cookie_data['cookie'],
                'encrypted_at': encrypted_at,
                'expires_at': expires_at,
                'is_expired': self._is_expired(expires_at)
            }
            
        except Exception as e:
            self.logger.error(f"Cookie decryption failed: {str(e)}")
            raise Exception(f"Failed to decrypt cookie: {str(e)}")
    
    def _is_expired(self, expires_at: Optional[datetime]) -> bool:
        """
        Check if cookie has expired
        
        Args:
            expires_at: Expiration datetime
            
        Returns:
            True if expired, False otherwise
        """
        if not expires_at:
            return False
        
        return datetime.utcnow() > expires_at
    
    def validate_cookie_expiration(self, encrypted_cookie: str) -> Dict[str, Any]:
        """
        Validate cookie expiration without full decryption
        
        Args:
            encrypted_cookie: Encrypted cookie to validate
            
        Returns:
            Validation result with expiration status
        """
        try:
            cookie_data = self.decrypt_cookie(encrypted_cookie)
            
            return {
                'valid': True,
                'is_expired': cookie_data['is_expired'],
                'expires_at': cookie_data['expires_at'],
                'encrypted_at': cookie_data['encrypted_at']
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def create_expiration_datetime(self, hours: int = 24) -> datetime:
        """
        Create expiration datetime for new cookies
        
        Args:
            hours: Hours from now for expiration (default 24)
            
        Returns:
            Expiration datetime
        """
        return datetime.utcnow() + timedelta(hours=hours)
    
    def refresh_cookie_expiration(self, encrypted_cookie: str, hours: int = 24) -> Dict[str, Any]:
        """
        Refresh cookie expiration time
        
        Args:
            encrypted_cookie: Current encrypted cookie
            hours: New expiration hours from now
            
        Returns:
            New encrypted cookie with updated expiration
        """
        try:
            # Decrypt current cookie
            cookie_data = self.decrypt_cookie(encrypted_cookie)
            
            # Re-encrypt with new expiration
            new_expires_at = self.create_expiration_datetime(hours)
            return self.encrypt_cookie(cookie_data['cookie'], new_expires_at)
            
        except Exception as e:
            self.logger.error(f"Cookie refresh failed: {str(e)}")
            raise Exception(f"Failed to refresh cookie: {str(e)}")
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a new encryption key for configuration
        
        Returns:
            Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()


class CookieManager:
    """
    High-level cookie management combining encryption and storage operations
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize cookie manager
        
        Args:
            encryption_key: Optional encryption key
        """
        self.encryption = CookieEncryption(encryption_key)
        self.logger = logging.getLogger(__name__)
    
    def store_cookie(self, cookie: str, expiration_hours: int = 24) -> str:
        """
        Store cookie with encryption and expiration
        
        Args:
            cookie: Raw login cookie
            expiration_hours: Hours until expiration
            
        Returns:
            Encrypted cookie string for database storage
        """
        expires_at = self.encryption.create_expiration_datetime(expiration_hours)
        encrypted_data = self.encryption.encrypt_cookie(cookie, expires_at)
        return encrypted_data['encrypted_cookie']
    
    def retrieve_cookie(self, encrypted_cookie: str) -> Optional[str]:
        """
        Retrieve and validate cookie
        
        Args:
            encrypted_cookie: Encrypted cookie from database
            
        Returns:
            Raw cookie if valid and not expired, None otherwise
        """
        try:
            cookie_data = self.encryption.decrypt_cookie(encrypted_cookie)
            
            if cookie_data['is_expired']:
                self.logger.warning("Cookie has expired")
                return None
            
            return cookie_data['cookie']
            
        except Exception as e:
            self.logger.error(f"Cookie retrieval failed: {str(e)}")
            return None
    
    def is_cookie_valid(self, encrypted_cookie: str) -> bool:
        """
        Check if cookie is valid and not expired
        
        Args:
            encrypted_cookie: Encrypted cookie to check
            
        Returns:
            True if valid and not expired
        """
        validation = self.encryption.validate_cookie_expiration(encrypted_cookie)
        return validation.get('valid', False) and not validation.get('is_expired', True)