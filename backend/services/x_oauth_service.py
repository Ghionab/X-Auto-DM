import os
import hmac
import hashlib
import base64
import urllib.parse
import time
import secrets
import requests
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from flask import current_app
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class XOAuthService:
    """Service for handling X (Twitter) authentication using twitterapi.io login endpoint"""
    
    def __init__(self):
        self.api_key = os.environ.get('TWITTER_API_KEY') or current_app.config.get('TWITTER_API_KEY')
        self.api_secret = os.environ.get('TWITTER_API_SECRET') or current_app.config.get('TWITTER_API_SECRET')
        self.base_url = current_app.config.get('TWITTER_API_BASE_URL', 'https://api.twitter.com')
        self.callback_url = os.environ.get('X_OAUTH_CALLBACK_URL', 'http://localhost:3000/auth/x/callback')
        
        # Make sure we have required credentials
        if not self.api_key or not self.api_secret:
            logger.error("Missing Twitter API credentials. Please set TWITTER_API_KEY and TWITTER_API_SECRET")
            raise ValueError("Missing Twitter API credentials")
        
        # Encryption key for token storage
        encryption_key = os.environ.get('TOKEN_ENCRYPTION_KEY')
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key.encode())
        else:
            # Generate a key for development (should be set in production)
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning("Using generated encryption key. Set TOKEN_ENCRYPTION_KEY in production!")
    
    def _generate_nonce(self) -> str:
        """Generate a unique nonce for OAuth requests"""
        return secrets.token_urlsafe(32)
    
    def _generate_timestamp(self) -> str:
        """Generate current timestamp for OAuth requests"""
        return str(int(time.time()))
    
    def _percent_encode(self, string: str) -> str:
        """Percent encode string according to OAuth spec"""
        return urllib.parse.quote(str(string), safe='')
    
    def _generate_signature_base_string(self, method: str, url: str, parameters: Dict[str, str]) -> str:
        """Generate the signature base string for OAuth"""
        # Sort parameters
        sorted_params = sorted(parameters.items())
        
        # Create parameter string
        param_string = '&'.join([f"{self._percent_encode(k)}={self._percent_encode(v)}" 
                                for k, v in sorted_params])
        
        # Create signature base string
        base_string = f"{method.upper()}&{self._percent_encode(url)}&{self._percent_encode(param_string)}"
        return base_string
    
    def _generate_signature(self, base_string: str, token_secret: str = "") -> str:
        """Generate OAuth signature using HMAC-SHA1"""
        signing_key = f"{self._percent_encode(self.api_secret)}&{self._percent_encode(token_secret)}"
        
        signature = hmac.new(
            signing_key.encode(),
            base_string.encode(),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def _create_oauth_header(self, method: str, url: str, oauth_params: Dict[str, str], 
                           token_secret: str = "") -> str:
        """Create OAuth authorization header"""
        # Generate signature
        base_string = self._generate_signature_base_string(method, url, oauth_params)
        signature = self._generate_signature(base_string, token_secret)
        oauth_params['oauth_signature'] = signature
        
        # Create header
        header_params = []
        for key in sorted(oauth_params.keys()):
            if key.startswith('oauth_'):
                header_params.append(f'{self._percent_encode(key)}="{self._percent_encode(oauth_params[key])}"')
        
        return f"OAuth {', '.join(header_params)}"
    
    def initiate_oauth(self) -> Tuple[bool, Dict]:
        """
        Step 1: Initiate login flow - return a custom login URL
        Since twitterapi.io requires username/password, we'll create a custom flow
        """
        try:
            if not self.api_key:
                return False, {"error": "Twitter API key not configured"}
            
            # Generate a state parameter for security
            state = self._generate_nonce()
            
            # Create a custom login URL that will show a form for Twitter credentials
            # This will redirect to our frontend login form
            auth_url = f"{self.callback_url}?action=login&state={state}"
            
            return True, {
                'oauth_token': state,  # Use state as token for consistency
                'oauth_token_secret': state,  # Use same state
                'authorization_url': auth_url
            }
                
        except Exception as e:
            logger.error(f"Unexpected error in OAuth initiation: {str(e)}")
            return False, {"error": "Unexpected error during OAuth initiation"}
    
    def login_with_credentials(self, username: str, email: str, password: str, 
                              totp_secret: str = "", proxy: str = "") -> Tuple[bool, Dict]:
        """
        Login to Twitter using twitterapi.io login endpoint
        """
        try:
            # Import the new clean API
            from x_api import connect_twitter_api_account, TwitterAPIError
            
            # Use the clean API function
            login_cookie = connect_twitter_api_account(
                username=username,
                email=email,
                password=password,
                totp_secret=totp_secret,
                proxy=proxy
            )
            
            return True, {
                'access_token': login_cookie,
                'access_token_secret': username,  # Use username as identifier
                'user_id': username,  # Use username as ID for now
                'screen_name': username,
                'login_cookie': login_cookie
            }
                
        except TwitterAPIError as e:
            logger.error(f"Twitter API error: {str(e)}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in login: {str(e)}")
            return False, {"error": f"Unexpected error: {str(e)}"}

    def complete_oauth(self, oauth_token: str, oauth_verifier: str, oauth_token_secret: str) -> Tuple[bool, Dict]:
        """Complete OAuth flow by exchanging request token for access token"""
        try:
            # Exchange the request token for an access token
            access_token_url = f"{self.base_url}/oauth/access_token"
            
            oauth_params = {
                'oauth_consumer_key': self.api_key,
                'oauth_token': oauth_token,
                'oauth_verifier': oauth_verifier,
                'oauth_signature_method': 'HMAC-SHA1',
                'oauth_timestamp': self._generate_timestamp(),
                'oauth_nonce': self._generate_nonce(),
                'oauth_version': '1.0'
            }
            
            # Generate the signature
            base_string = self._generate_signature_base_string('POST', access_token_url, oauth_params)
            oauth_params['oauth_signature'] = self._generate_signature(base_string, oauth_token_secret)
            
            # Make the request
            headers = {
                'Authorization': self._create_oauth_header('POST', access_token_url, oauth_params, oauth_token_secret),
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(access_token_url, headers=headers, data={})
            
            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.text}")
                return False, {'error': 'Failed to get access token from Twitter'}
            
            # Parse the response
            response_data = dict(urllib.parse.parse_qsl(response.text))
            
            return True, {
                'access_token': response_data.get('oauth_token'),
                'access_token_secret': response_data.get('oauth_token_secret'),
                'user_id': response_data.get('user_id'),
                'screen_name': response_data.get('screen_name')
            }
            
        except Exception as e:
            logger.error(f"Error completing OAuth: {str(e)}")
            return False, {'error': str(e)}
    
    def handle_callback(self, oauth_token: str, oauth_verifier: str, 
                       oauth_token_secret: str) -> Tuple[bool, Dict]:
        """
        Step 2: Handle callback - this is now just a wrapper for the login
        """
        try:
            # For our simplified flow, oauth_verifier contains the login_cookie
            if not oauth_verifier:
                return False, {"error": "Missing login cookie"}
            
            return True, {
                'access_token': oauth_verifier,
                'access_token_secret': oauth_token_secret,
                'user_id': oauth_token_secret,  # Use token secret as user ID
                'screen_name': oauth_token_secret
            }
                
        except Exception as e:
            logger.error(f"Unexpected error in OAuth callback: {str(e)}")
            return False, {"error": "Unexpected error during OAuth callback"}
    
    def encrypt_tokens(self, access_token: str, access_token_secret: str) -> Tuple[str, str]:
        """
        Encrypt OAuth tokens for secure storage
        """
        try:
            encrypted_token = self.cipher_suite.encrypt(access_token.encode()).decode()
            encrypted_secret = self.cipher_suite.encrypt(access_token_secret.encode()).decode()
            return encrypted_token, encrypted_secret
        except Exception as e:
            logger.error(f"Token encryption error: {str(e)}")
            raise
    
    def decrypt_tokens(self, encrypted_token: str, encrypted_secret: str) -> Tuple[str, str]:
        """
        Decrypt OAuth tokens for API usage
        """
        try:
            access_token = self.cipher_suite.decrypt(encrypted_token.encode()).decode()
            access_token_secret = self.cipher_suite.decrypt(encrypted_secret.encode()).decode()
            return access_token, access_token_secret
        except Exception as e:
            logger.error(f"Token decryption error: {str(e)}")
            raise
    
    def verify_credentials(self, access_token: str, access_token_secret: str) -> Tuple[bool, Dict]:
        """
        Verify credentials using twitterapi.io
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Use twitterapi.io endpoint to get user info
            # We'll use the access_token as the auth token to get user details
            verify_url = f"{self.base_url}/v2/user_by_username/{access_token_secret}"  # Using secret as username
            
            response = requests.get(verify_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    user_data = data['data']
                    return True, {
                        'user_id': user_data.get('id'),
                        'screen_name': user_data.get('username'),
                        'name': user_data.get('name'),
                        'followers_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                        'following_count': user_data.get('public_metrics', {}).get('following_count', 0),
                        'verified': user_data.get('verified', False),
                        'profile_image_url': user_data.get('profile_image_url')
                    }
                else:
                    return False, {"error": "Invalid user data"}
            else:
                logger.error(f"Credentials verification failed: {response.status_code} - {response.text}")
                return False, {"error": "Invalid credentials"}
                
        except requests.RequestException as e:
            logger.error(f"Credentials verification error: {str(e)}")
            return False, {"error": "Network error during verification"}
        except Exception as e:
            logger.error(f"Unexpected error in credentials verification: {str(e)}")
            return False, {"error": "Unexpected error during verification"}
    
    def make_authenticated_request(self, method: str, endpoint: str, access_token: str, 
                                 access_token_secret: str, params: Dict = None, 
                                 data: Dict = None) -> Tuple[bool, Dict]:
        """
        Make an authenticated API request using OAuth tokens
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            # OAuth parameters
            oauth_params = {
                'oauth_consumer_key': self.api_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'HMAC-SHA1',
                'oauth_timestamp': self._generate_timestamp(),
                'oauth_token': access_token,
                'oauth_version': '1.0'
            }
            
            # Add query parameters to OAuth params for signature generation
            all_params = oauth_params.copy()
            if params:
                all_params.update(params)
            
            # Create authorization header
            auth_header = self._create_oauth_header(method, url, all_params, access_token_secret)
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'application/json' if data else 'application/x-www-form-urlencoded'
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                if data:
                    response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, params=params, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            if response.status_code in [200, 201]:
                try:
                    return True, response.json()
                except ValueError:
                    return True, {"response": response.text}
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return False, {"error": response.text, "status_code": response.status_code}
                
        except requests.RequestException as e:
            logger.error(f"Authenticated request error: {str(e)}")
            return False, {"error": "Network error during API request"}
        except Exception as e:
            logger.error(f"Unexpected error in authenticated request: {str(e)}")
            return False, {"error": "Unexpected error during API request"}