"""
TwitterAPI.io Authentication Module
Handles Twitter account login using the twitterapi.io user_login_v2 endpoint
"""

import logging
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    from ..twitterapi_core import get_core_client, TwitterAPIError
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from twitterapi_core import get_core_client, TwitterAPIError

logger = logging.getLogger(__name__)

@dataclass
class LoginCredentials:
    """Twitter login credentials"""
    username: str
    email: str
    password: str
    totp_secret: str  # Required for 2FA
    proxy: Optional[str] = None

@dataclass
class LoginRequest:
    """Twitter login request (alias for LoginCredentials)"""
    username: str
    email: str
    password: str
    totp_secret: str  # Required for 2FA
    proxy: Optional[str] = None

@dataclass
class LoginSession:
    """Twitter login session"""
    login_cookie: str
    status: str
    message: Optional[str] = None
    username: Optional[str] = None

@dataclass
class LoginResult:
    """Twitter login result (alias for LoginSession)"""
    login_cookie: str
    status: str
    message: Optional[str] = None
    username: Optional[str] = None

class TwitterAuthClient:
    """Twitter authentication client using twitterapi.io"""
    
    def __init__(self, proxy: Optional[str] = None):
        """
        Initialize authentication client
        
        Args:
            proxy: Optional proxy URL (uses default if not provided)
        """
        self.core_client = get_core_client()
        self.proxy = proxy
        self._current_session: Optional[LoginSession] = None
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter sensitive data from logs to prevent exposure of credentials
        
        Args:
            data: Dictionary that may contain sensitive data
            
        Returns:
            Dict[str, Any]: Filtered dictionary with sensitive data masked
        """
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = {
            'password', 'totp_secret', 'login_cookie', 'login_cookies', 
            'auth_token', 'access_token', 'refresh_token', 'api_key',
            'secret', 'token', 'credential'
        }
        
        filtered = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                if isinstance(value, str) and len(value) > 10:
                    filtered[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    filtered[key] = "[FILTERED]"
            else:
                filtered[key] = value
        
        return filtered
    
    def login(self, credentials: LoginCredentials) -> LoginSession:
        """
        Login to Twitter account using twitterapi.io user_login_v2 endpoint
        
        According to the API docs:
        POST /twitter/user_login_v2
        - Requires: username, email, password, totp_secret, proxy
        - Returns: login_cookies (or login_cookie), status, message
        
        Args:
            credentials: Twitter login credentials
            
        Returns:
            LoginSession: Session with login_cookie for subsequent requests
            
        Raises:
            TwitterAPIError: If login fails
        """
        if not credentials.username or not credentials.email or not credentials.password:
            raise TwitterAPIError("Username, email, and password are required")
        
        if not credentials.totp_secret:
            raise TwitterAPIError("TOTP secret is required for authentication")
        
        data = {
            "user_name": credentials.username,
            "email": credentials.email,
            "password": credentials.password,
            "totp_secret": credentials.totp_secret
        }
        
        logger.info(f"Attempting login for Twitter account: {credentials.username}")
        logger.info(f"Login request data: username={credentials.username}, email={credentials.email}")
        logger.debug(f"Request payload keys: {list(data.keys())}")
        
        # Log filtered request data for debugging (without sensitive info)
        filtered_data = self._filter_sensitive_data(data)
        logger.debug(f"Filtered request payload: {filtered_data}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/user_login_v2",
                data=data,
                proxy=credentials.proxy or self.proxy
            )
            
            logger.info(f"Login response received for {credentials.username}")
            logger.debug(f"Response keys: {list(response.keys()) if response else 'None'}")
            logger.debug(f"Response status: {response.get('status') if response else 'None'}")
            
            # Log filtered response for debugging (without sensitive info)
            if response:
                filtered_response = self._filter_sensitive_data(response)
                logger.debug(f"Filtered response data: {filtered_response}")
            
            # Parse login response to extract cookie
            login_cookie = self._parse_login_response(response)
            
            # Create session object
            session = LoginSession(
                login_cookie=login_cookie,
                status=response.get("status", "success"),
                message=response.get("msg") or response.get("message"),
                username=credentials.username
            )
            
            # Store current session
            self._current_session = session
            
            logger.info(f"Successfully authenticated Twitter account: {credentials.username}")
            logger.info(f"Session status: {session.status}, message: {session.message}")
            logger.debug(f"Login cookie length: {len(login_cookie) if login_cookie else 0} characters")
            return session
            
        except TwitterAPIError as e:
            logger.error(f"TwitterAPI error during login for {credentials.username}: {e}")
            if hasattr(e, 'response_data') and e.response_data:
                logger.error(f"Error response data: {e.response_data}")
            if hasattr(e, 'status_code') and e.status_code:
                logger.error(f"HTTP status code: {e.status_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login for {credentials.username}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise TwitterAPIError(f"Login failed: {str(e)}")
    
    def _parse_login_response(self, response: Dict[str, Any]) -> str:
        """
        Parse login response to extract the correct login cookie field
        
        The TwitterAPI.io API may return either 'login_cookie' or 'login_cookies'
        depending on the API version or configuration. This method handles both cases.
        
        Args:
            response: API response dictionary
            
        Returns:
            str: Login cookie string
            
        Raises:
            TwitterAPIError: If no valid login cookie field is found
        """
        if not response:
            logger.error("Empty or None response received")
            raise TwitterAPIError("Login failed: Empty response received")
        
        # Check for login_cookies (plural) first as this appears to be the current format
        if "login_cookies" in response:
            login_cookie = response["login_cookies"]
            logger.debug("Found 'login_cookies' field in response")
            if login_cookie:
                return login_cookie
            else:
                logger.warning("'login_cookies' field is empty")
        
        # Check for login_cookie (singular) as fallback
        if "login_cookie" in response:
            login_cookie = response["login_cookie"]
            logger.debug("Found 'login_cookie' field in response")
            if login_cookie:
                return login_cookie
            else:
                logger.warning("'login_cookie' field is empty")
        
        # If neither field is found or both are empty
        logger.error(f"No valid login cookie found in response")
        logger.error(f"Available response fields: {list(response.keys())}")
        
        # Log filtered response for debugging
        filtered_response = self._filter_sensitive_data(response) if hasattr(self, '_filter_sensitive_data') else response
        logger.error(f"Response content (filtered): {filtered_response}")
        
        # Check if response indicates an error
        status = response.get("status", "unknown")
        message = response.get("msg") or response.get("message", "No error message provided")
        
        if status != "success":
            logger.error(f"Login failed with status: {status}, message: {message}")
            raise TwitterAPIError(f"Login failed: {message}")
        
        raise TwitterAPIError("Login failed: No login cookie received in response")
    
    def get_current_session(self) -> Optional[LoginSession]:
        """
        Get the current active session
        
        Returns:
            Optional[LoginSession]: Current session if authenticated
        """
        return self._current_session
    
    def logout(self) -> None:
        """
        Clear current session
        Note: twitterapi.io doesn't have an explicit logout endpoint,
        so we just clear the local session data
        """
        if self._current_session:
            logger.info(f"Logging out Twitter account: {self._current_session.username}")
            self._current_session = None
        else:
            logger.warning("No active session to logout")
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated
        
        Returns:
            bool: True if there's an active session
        """
        return self._current_session is not None
    
    def get_login_cookie(self) -> str:
        """
        Get login cookie for authenticated requests
        
        Returns:
            str: Login cookie
            
        Raises:
            TwitterAPIError: If not authenticated
        """
        if not self._current_session:
            raise TwitterAPIError("Not authenticated. Please login first.")
        
        return self._current_session.login_cookie


# Convenience functions
def login_twitter_account(username: str, email: str, password: str, 
                         totp_secret: str, proxy: Optional[str] = None) -> LoginSession:
    """
    Convenience function to login to Twitter account
    
    Args:
        username: Twitter username
        email: Twitter email  
        password: Twitter password
        totp_secret: TOTP secret for 2FA
        proxy: Optional proxy URL
        
    Returns:
        LoginSession: Session with login_cookie
    """
    auth_client = TwitterAuthClient(proxy=proxy)
    credentials = LoginCredentials(
        username=username,
        email=email,
        password=password,
        totp_secret=totp_secret,
        proxy=proxy
    )
    
    return auth_client.login(credentials)

def authenticate_user(username: str, email: str, password: str, 
                     totp_secret: str, proxy: Optional[str] = None) -> LoginSession:
    """
    Convenience function to authenticate a user (alias for login_twitter_account)
    
    Args:
        username: Twitter username
        email: Twitter email  
        password: Twitter password
        totp_secret: TOTP secret for 2FA
        proxy: Optional proxy URL
        
    Returns:
        LoginSession: Session with login_cookie
    """
    return login_twitter_account(username, email, password, totp_secret, proxy)

def create_auth_client(proxy: Optional[str] = None) -> TwitterAuthClient:
    """
    Create a new authentication client
    
    Args:
        proxy: Optional proxy URL
        
    Returns:
        TwitterAuthClient: New authentication client
    """
    return TwitterAuthClient(proxy=proxy)
