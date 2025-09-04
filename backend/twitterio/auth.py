"""
TwitterAPI.io Authentication Module
Handles Twitter account login using the twitterapi.io user_login_v2 endpoint
"""

import logging
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
    
    def login(self, credentials: LoginCredentials) -> LoginSession:
        """
        Login to Twitter account using twitterapi.io user_login_v2 endpoint
        
        According to the API docs:
        POST /twitter/user_login_v2
        - Requires: username, email, password, totp_secret, proxy
        - Returns: login_cookie, status, msg
        
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
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/user_login_v2",
                data=data,
                proxy=credentials.proxy or self.proxy
            )
            
            if "login_cookie" not in response:
                raise TwitterAPIError("Login failed: No login_cookie received")
            
            # Create session object
            session = LoginSession(
                login_cookie=response["login_cookie"],
                status=response.get("status", "success"),
                message=response.get("msg"),
                username=credentials.username
            )
            
            # Store current session
            self._current_session = session
            
            logger.info(f"Successfully authenticated Twitter account: {credentials.username}")
            return session
            
        except TwitterAPIError as e:
            logger.error(f"Login failed for {credentials.username}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise TwitterAPIError(f"Login failed: {str(e)}")
    
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
