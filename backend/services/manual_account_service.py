"""
Manual Account Service for login cookie management
Handles manual addition of X accounts using login cookies
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from flask import current_app

from models import db, TwitterAccount, User
from services.cookie_encryption import CookieManager


class ManualAccountService:
    """
    Service for managing manual X account addition via login cookies
    """
    
    def __init__(self):
        """Initialize the manual account service"""
        self.logger = logging.getLogger(__name__)
        self.cookie_manager = CookieManager()
    
    def add_account_by_cookie(self, user_id: int, login_cookie: str, 
                            account_name: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a Twitter account using login cookie
        
        Args:
            user_id: ID of the user adding the account
            login_cookie: Raw login cookie string
            account_name: Optional account name override
            
        Returns:
            Tuple of (success, result_data)
            
        Raises:
            ValueError: If user_id is invalid or cookie is malformed
        """
        try:
            # Validate user exists
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Validate login cookie format and extract data
            is_valid, cookie_data = self.validate_login_cookie(login_cookie)
            if not is_valid:
                return False, {
                    'error': 'Invalid login cookie format',
                    'details': cookie_data.get('error', 'Cookie validation failed')
                }
            
            # Extract account information from cookie
            account_info = self.extract_account_info(login_cookie)
            if not account_info.get('username'):
                return False, {
                    'error': 'Unable to extract account information from cookie',
                    'details': 'Cookie does not contain valid user identification'
                }
            
            # Check if account already exists for this user
            existing_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                twitter_user_id=account_info.get('user_id')
            ).first()
            
            if existing_account:
                return False, {
                    'error': 'Account already connected',
                    'details': f"Account @{account_info['username']} is already connected to your profile"
                }
            
            # Encrypt and store the login cookie
            encrypted_cookie = self.cookie_manager.store_cookie(
                login_cookie, 
                expiration_hours=current_app.config.get('COOKIE_EXPIRATION_HOURS', 720)  # 30 days default
            )
            
            # Create new TwitterAccount record
            twitter_account = TwitterAccount(
                user_id=user_id,
                username=account_info['username'],
                screen_name=account_info['username'],
                name=account_name or account_info.get('display_name', account_info['username']),
                twitter_user_id=account_info.get('user_id'),
                login_cookie=encrypted_cookie,
                connection_status='connected',
                is_active=True
            )
            
            # Save to database
            db.session.add(twitter_account)
            db.session.commit()
            
            self.logger.info(f"Successfully added manual account @{account_info['username']} for user {user_id}")
            
            return True, {
                'account_id': twitter_account.id,
                'username': account_info['username'],
                'display_name': twitter_account.name,
                'user_id': account_info.get('user_id'),
                'connection_status': 'connected',
                'created_at': twitter_account.created_at.isoformat()
            }
            
        except ValueError as e:
            self.logger.error(f"Validation error in add_account_by_cookie: {str(e)}")
            return False, {'error': 'Validation error', 'details': str(e)}
        
        except Exception as e:
            self.logger.error(f"Error adding account by cookie: {str(e)}")
            db.session.rollback()
            return False, {
                'error': 'Failed to add account',
                'details': 'An unexpected error occurred while adding the account'
            }
    
    def validate_login_cookie(self, login_cookie: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate login cookie format and extract basic data
        
        Args:
            login_cookie: Raw login cookie string (can be response JSON or direct cookie)
            
        Returns:
            Tuple of (is_valid, validation_data)
        """
        try:
            if not login_cookie or not isinstance(login_cookie, str):
                return False, {'error': 'Cookie must be a non-empty string'}
            
            # Clean up the cookie string (remove extra whitespace, newlines)
            cleaned_cookie = login_cookie.strip()
            
            # Try to parse as JSON first
            try:
                parsed_data = json.loads(cleaned_cookie)
                
                # Check if this is a response format with login_cookies field
                if isinstance(parsed_data, dict) and 'login_cookies' in parsed_data:
                    # Extract the actual cookie data from login_cookies field
                    login_cookies_str = parsed_data['login_cookies']
                    
                    # Decode base64 if needed
                    import base64
                    try:
                        decoded_cookies = base64.b64decode(login_cookies_str).decode('utf-8')
                        cookie_data = json.loads(decoded_cookies)
                    except:
                        # If base64 decode fails, try direct JSON parse
                        cookie_data = json.loads(login_cookies_str)
                else:
                    # Direct cookie JSON format
                    cookie_data = parsed_data
                    
            except json.JSONDecodeError:
                # If not JSON, check if it's in key=value format
                if '=' in cleaned_cookie and ';' in cleaned_cookie:
                    cookie_data = self._parse_cookie_string(cleaned_cookie)
                else:
                    return False, {'error': 'Cookie must be in JSON format, response format with login_cookies field, or standard cookie format'}
            
            # Validate required fields for TwitterAPI.io
            required_fields = ['auth_token']
            missing_fields = []
            
            for field in required_fields:
                if field not in cookie_data or not cookie_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, {
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'required_fields': required_fields,
                    'found_fields': list(cookie_data.keys())
                }
            
            # Additional validation for auth_token format
            auth_token = cookie_data.get('auth_token', '')
            if len(auth_token) < 10:  # Basic length check
                return False, {'error': 'auth_token appears to be invalid (too short)'}
            
            # Check for user identification (twid or user_id)
            has_user_id = bool(cookie_data.get('twid') or cookie_data.get('user_id'))
            if not has_user_id:
                return False, {
                    'error': 'Cookie must contain user identification (twid or user_id field)',
                    'details': 'Unable to determine account owner from cookie data'
                }
            
            self.logger.info("Login cookie validation successful")
            
            return True, {
                'valid': True,
                'fields_found': list(cookie_data.keys()),
                'has_auth_token': bool(cookie_data.get('auth_token')),
                'has_user_id': has_user_id,
                'cookie_size': len(cleaned_cookie)
            }
            
        except Exception as e:
            self.logger.error(f"Cookie validation error: {str(e)}")
            return False, {'error': f'Cookie validation failed: {str(e)}'}
    
    def extract_account_info(self, login_cookie: str) -> Dict[str, str]:
        """
        Extract account information from login cookie
        
        Args:
            login_cookie: Raw login cookie string (can be response JSON or direct cookie)
            
        Returns:
            Dictionary with extracted account information
        """
        try:
            # Clean and parse cookie
            cleaned_cookie = login_cookie.strip()
            
            try:
                parsed_data = json.loads(cleaned_cookie)
                
                # Check if this is a response format with login_cookies field
                if isinstance(parsed_data, dict) and 'login_cookies' in parsed_data:
                    # Extract the actual cookie data from login_cookies field
                    login_cookies_str = parsed_data['login_cookies']
                    
                    # Decode base64 if needed
                    import base64
                    try:
                        decoded_cookies = base64.b64decode(login_cookies_str).decode('utf-8')
                        cookie_data = json.loads(decoded_cookies)
                    except:
                        # If base64 decode fails, try direct JSON parse
                        cookie_data = json.loads(login_cookies_str)
                else:
                    # Direct cookie JSON format
                    cookie_data = parsed_data
                    
            except json.JSONDecodeError:
                if '=' in cleaned_cookie and ';' in cleaned_cookie:
                    cookie_data = self._parse_cookie_string(cleaned_cookie)
                else:
                    return {}
            
            account_info = {}
            
            # Extract user ID from twid field
            twid = cookie_data.get('twid', '')
            if twid:
                # twid format is usually "u=1234567890" (quoted)
                user_id_match = re.search(r'u=(\d+)', twid.strip('"'))
                if user_id_match:
                    account_info['user_id'] = user_id_match.group(1)
            
            # Fallback to direct user_id field
            if not account_info.get('user_id') and cookie_data.get('user_id'):
                account_info['user_id'] = str(cookie_data['user_id'])
            
            # Extract username if available (not always present in cookies)
            if cookie_data.get('screen_name'):
                account_info['username'] = cookie_data['screen_name']
            elif cookie_data.get('username'):
                account_info['username'] = cookie_data['username']
            else:
                # Generate a placeholder username based on user_id
                if account_info.get('user_id'):
                    account_info['username'] = f"user_{account_info['user_id']}"
            
            # Extract display name if available
            if cookie_data.get('name'):
                account_info['display_name'] = cookie_data['name']
            elif cookie_data.get('display_name'):
                account_info['display_name'] = cookie_data['display_name']
            
            # Store auth token info (for validation)
            if cookie_data.get('auth_token'):
                account_info['has_auth_token'] = True
                account_info['auth_token_length'] = len(cookie_data['auth_token'])
            
            self.logger.info(f"Extracted account info for user_id: {account_info.get('user_id')}")
            
            return account_info
            
        except Exception as e:
            self.logger.error(f"Error extracting account info: {str(e)}")
            return {}
    
    def _parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        """
        Parse cookie string in key=value; format to dictionary
        
        Args:
            cookie_string: Cookie string in standard format
            
        Returns:
            Dictionary of cookie key-value pairs
        """
        cookie_dict = {}
        
        try:
            # Split by semicolon and parse each key=value pair
            pairs = cookie_string.split(';')
            
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    
                    cookie_dict[key] = value
            
            return cookie_dict
            
        except Exception as e:
            self.logger.error(f"Error parsing cookie string: {str(e)}")
            return {}
    
    def get_account_by_cookie(self, user_id: int, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get account information and validate cookie
        
        Args:
            user_id: User ID
            account_id: Twitter account ID
            
        Returns:
            Account information with cookie validation status
        """
        try:
            account = TwitterAccount.query.filter_by(
                id=account_id,
                user_id=user_id
            ).first()
            
            if not account:
                return None
            
            # Check cookie validity
            cookie_valid = False
            if account.login_cookie:
                cookie_valid = self.cookie_manager.is_cookie_valid(account.login_cookie)
            
            return {
                'id': account.id,
                'username': account.username,
                'display_name': account.name,
                'user_id': account.twitter_user_id,
                'connection_status': account.connection_status,
                'cookie_valid': cookie_valid,
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting account by cookie: {str(e)}")
            return None
    
    def refresh_account_cookie(self, user_id: int, account_id: int, 
                             new_cookie: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh account login cookie
        
        Args:
            user_id: User ID
            account_id: Twitter account ID
            new_cookie: New login cookie
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            account = TwitterAccount.query.filter_by(
                id=account_id,
                user_id=user_id
            ).first()
            
            if not account:
                return False, {'error': 'Account not found'}
            
            # Validate new cookie
            is_valid, validation_data = self.validate_login_cookie(new_cookie)
            if not is_valid:
                return False, {
                    'error': 'Invalid new cookie',
                    'details': validation_data.get('error')
                }
            
            # Encrypt and store new cookie
            encrypted_cookie = self.cookie_manager.store_cookie(
                new_cookie,
                expiration_hours=current_app.config.get('COOKIE_EXPIRATION_HOURS', 720)
            )
            
            # Update account
            account.login_cookie = encrypted_cookie
            account.connection_status = 'connected'
            account.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Successfully refreshed cookie for account {account_id}")
            
            return True, {
                'account_id': account.id,
                'username': account.username,
                'connection_status': 'connected',
                'updated_at': account.updated_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error refreshing account cookie: {str(e)}")
            db.session.rollback()
            return False, {'error': 'Failed to refresh cookie'}
    
    def validate_account_cookie_access(self, user_id: int, account_id: int) -> Tuple[bool, Optional[str]]:
        """
        Validate and retrieve decrypted cookie for API usage
        
        Args:
            user_id: User ID
            account_id: Twitter account ID
            
        Returns:
            Tuple of (success, decrypted_cookie)
        """
        try:
            account = TwitterAccount.query.filter_by(
                id=account_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not account or not account.login_cookie:
                return False, None
            
            # Decrypt and validate cookie
            decrypted_cookie = self.cookie_manager.retrieve_cookie(account.login_cookie)
            
            if not decrypted_cookie:
                # Mark account as having expired cookie
                account.connection_status = 'expired'
                db.session.commit()
                return False, None
            
            return True, decrypted_cookie
            
        except Exception as e:
            self.logger.error(f"Error validating account cookie access: {str(e)}")
            return False, None