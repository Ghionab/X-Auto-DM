import os
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from flask import current_app

from models import db, XOAuthTokens, TwitterAccount, User

logger = logging.getLogger(__name__)

class TokenStorageService:
    """Service for secure token storage and retrieval"""
    
    def __init__(self):
        # Get encryption key from environment
        encryption_key = os.environ.get('TOKEN_ENCRYPTION_KEY')
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key.encode())
        else:
            # Generate a key for development (should be set in production)
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning("Using generated encryption key. Set TOKEN_ENCRYPTION_KEY in production!")
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        try:
            return self.cipher_suite.encrypt(token.encode()).decode()
        except Exception as e:
            logger.error(f"Token encryption error: {str(e)}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for usage"""
        try:
            return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            logger.error(f"Token decryption error: {str(e)}")
            raise
    
    def store_oauth_tokens(self, user_id: int, access_token: str, access_token_secret: str,
                          twitter_user_id: str, screen_name: str, 
                          twitter_account_id: Optional[int] = None) -> Tuple[bool, Dict]:
        """
        Store OAuth tokens securely in the database
        """
        try:
            # Encrypt tokens
            encrypted_token = self.encrypt_token(access_token)
            encrypted_secret = self.encrypt_token(access_token_secret)
            
            # Check if tokens already exist for this user and Twitter account
            existing_tokens = XOAuthTokens.query.filter_by(
                user_id=user_id,
                twitter_user_id=twitter_user_id,
                is_active=True
            ).first()
            
            if existing_tokens:
                # Update existing tokens
                existing_tokens.access_token_encrypted = encrypted_token
                existing_tokens.access_token_secret_encrypted = encrypted_secret
                existing_tokens.screen_name = screen_name
                existing_tokens.twitter_account_id = twitter_account_id
                existing_tokens.created_at = datetime.utcnow()
                oauth_tokens = existing_tokens
            else:
                # Create new token record
                oauth_tokens = XOAuthTokens(
                    user_id=user_id,
                    twitter_account_id=twitter_account_id,
                    access_token_encrypted=encrypted_token,
                    access_token_secret_encrypted=encrypted_secret,
                    twitter_user_id=twitter_user_id,
                    screen_name=screen_name,
                    is_active=True
                )
                db.session.add(oauth_tokens)
            
            db.session.commit()
            
            logger.info(f"OAuth tokens stored for user {user_id}, Twitter user {screen_name}")
            
            return True, {
                'token_id': oauth_tokens.id,
                'twitter_user_id': twitter_user_id,
                'screen_name': screen_name,
                'message': 'Tokens stored successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing OAuth tokens: {str(e)}")
            return False, {'error': 'Failed to store tokens'}
    
    def get_oauth_tokens(self, user_id: int, twitter_account_id: Optional[int] = None,
                        twitter_user_id: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Retrieve and decrypt OAuth tokens for a user
        """
        try:
            query = XOAuthTokens.query.filter_by(user_id=user_id, is_active=True)
            
            if twitter_account_id:
                query = query.filter_by(twitter_account_id=twitter_account_id)
            elif twitter_user_id:
                query = query.filter_by(twitter_user_id=twitter_user_id)
            
            oauth_tokens = query.first()
            
            if not oauth_tokens:
                return False, {'error': 'No active tokens found'}
            
            # Decrypt tokens
            access_token = self.decrypt_token(oauth_tokens.access_token_encrypted)
            access_token_secret = self.decrypt_token(oauth_tokens.access_token_secret_encrypted)
            
            return True, {
                'access_token': access_token,
                'access_token_secret': access_token_secret,
                'twitter_user_id': oauth_tokens.twitter_user_id,
                'screen_name': oauth_tokens.screen_name,
                'token_id': oauth_tokens.id
            }
            
        except Exception as e:
            logger.error(f"Error retrieving OAuth tokens: {str(e)}")
            return False, {'error': 'Failed to retrieve tokens'}
    
    def revoke_oauth_tokens(self, user_id: int, twitter_account_id: Optional[int] = None,
                           token_id: Optional[int] = None) -> Tuple[bool, Dict]:
        """
        Revoke (deactivate) OAuth tokens
        """
        try:
            query = XOAuthTokens.query.filter_by(user_id=user_id, is_active=True)
            
            if token_id:
                query = query.filter_by(id=token_id)
            elif twitter_account_id:
                query = query.filter_by(twitter_account_id=twitter_account_id)
            
            tokens = query.all()
            
            if not tokens:
                return False, {'error': 'No active tokens found'}
            
            # Deactivate tokens
            for token in tokens:
                token.is_active = False
            
            db.session.commit()
            
            logger.info(f"OAuth tokens revoked for user {user_id}")
            
            return True, {'message': f'Revoked {len(tokens)} token(s)'}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error revoking OAuth tokens: {str(e)}")
            return False, {'error': 'Failed to revoke tokens'}
    
    def update_twitter_account_connection(self, user_id: int, twitter_account_id: int,
                                        oauth_tokens_id: int, connection_status: str = 'connected') -> Tuple[bool, Dict]:
        """
        Update TwitterAccount with OAuth token reference and connection status
        """
        try:
            twitter_account = TwitterAccount.query.filter_by(
                id=twitter_account_id,
                user_id=user_id
            ).first()
            
            if not twitter_account:
                return False, {'error': 'Twitter account not found'}
            
            twitter_account.oauth_tokens_id = oauth_tokens_id
            twitter_account.connection_status = connection_status
            twitter_account.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Twitter account {twitter_account_id} connection updated to {connection_status}")
            
            return True, {
                'twitter_account_id': twitter_account_id,
                'connection_status': connection_status,
                'message': 'Connection status updated'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating Twitter account connection: {str(e)}")
            return False, {'error': 'Failed to update connection status'}
    
    def create_or_update_twitter_account(self, user_id: int, user_data: Dict,
                                       oauth_tokens_id: int) -> Tuple[bool, Dict]:
        """
        Create or update TwitterAccount with OAuth connection
        """
        try:
            # Check if account already exists
            existing_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                username=user_data['screen_name']
            ).first()
            
            if existing_account:
                # Update existing account
                existing_account.display_name = user_data.get('name', '')
                existing_account.followers_count = user_data.get('followers_count', 0)
                existing_account.following_count = user_data.get('following_count', 0)
                existing_account.is_verified = user_data.get('verified', False)
                existing_account.profile_image_url = user_data.get('profile_image_url', '')
                existing_account.oauth_tokens_id = oauth_tokens_id
                existing_account.connection_status = 'connected'
                existing_account.updated_at = datetime.utcnow()
                twitter_account = existing_account
            else:
                # Create new account
                twitter_account = TwitterAccount(
                    user_id=user_id,
                    username=user_data['screen_name'],
                    display_name=user_data.get('name', ''),
                    followers_count=user_data.get('followers_count', 0),
                    following_count=user_data.get('following_count', 0),
                    is_verified=user_data.get('verified', False),
                    profile_image_url=user_data.get('profile_image_url', ''),
                    oauth_tokens_id=oauth_tokens_id,
                    connection_status='connected',
                    is_active=True
                )
                db.session.add(twitter_account)
            
            db.session.commit()
            
            logger.info(f"Twitter account created/updated for user {user_id}: {user_data['screen_name']}")
            
            return True, {
                'twitter_account': twitter_account.to_dict(),
                'message': 'Twitter account connected successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating/updating Twitter account: {str(e)}")
            return False, {'error': 'Failed to create/update Twitter account'}
    
    def get_user_connected_accounts(self, user_id: int) -> Tuple[bool, Dict]:
        """
        Get all connected Twitter accounts for a user
        """
        try:
            accounts = TwitterAccount.query.filter_by(
                user_id=user_id,
                is_active=True
            ).filter(
                TwitterAccount.connection_status == 'connected'
            ).all()
            
            return True, {
                'accounts': [account.to_dict() for account in accounts],
                'count': len(accounts)
            }
            
        except Exception as e:
            logger.error(f"Error getting connected accounts: {str(e)}")
            return False, {'error': 'Failed to get connected accounts'}
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a new encryption key for token storage
        This should be called once and the key stored securely
        """
        return Fernet.generate_key().decode()