#!/usr/bin/env python3
"""
Test script for X OAuth Integration
Tests the complete OAuth flow without requiring actual X API calls
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, XOAuthTokens, TwitterAccount
from services.x_oauth_service import XOAuthService
from services.token_storage_service import TokenStorageService

class TestXOAuthIntegration(unittest.TestCase):
    """Test X OAuth integration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create tables
        db.create_all()
        
        # Create test user
        self.test_user = User(
            email='test@example.com',
            username='testuser'
        )
        self.test_user.set_password('testpassword123!')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Get auth token
        response = self.client.post('/api/auth/login', 
                                  json={'email': 'test@example.com', 'password': 'testpassword123!'})
        self.auth_token = response.json['access_token']
        self.auth_headers = {'Authorization': f'Bearer {self.auth_token}'}
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_oauth_service_initialization(self):
        """Test OAuth service can be initialized"""
        oauth_service = XOAuthService()
        self.assertIsNotNone(oauth_service)
        self.assertIsNotNone(oauth_service.cipher_suite)
    
    @patch('services.x_oauth_service.requests.post')
    def test_oauth_initiation(self, mock_post):
        """Test OAuth flow initiation"""
        # Mock successful request token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'oauth_token=test_token&oauth_token_secret=test_secret&oauth_callback_confirmed=true'
        mock_post.return_value = mock_response
        
        oauth_service = XOAuthService()
        success, result = oauth_service.initiate_oauth()
        
        self.assertTrue(success)
        self.assertIn('oauth_token', result)
        self.assertIn('oauth_token_secret', result)
        self.assertIn('authorization_url', result)
        self.assertEqual(result['oauth_token'], 'test_token')
        self.assertEqual(result['oauth_token_secret'], 'test_secret')
    
    @patch('services.x_oauth_service.requests.post')
    def test_oauth_callback_handling(self, mock_post):
        """Test OAuth callback handling"""
        # Mock successful access token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'oauth_token=access_token&oauth_token_secret=access_secret&user_id=12345&screen_name=testuser'
        mock_post.return_value = mock_response
        
        oauth_service = XOAuthService()
        success, result = oauth_service.handle_callback(
            'request_token', 'verifier', 'request_secret'
        )
        
        self.assertTrue(success)
        self.assertEqual(result['access_token'], 'access_token')
        self.assertEqual(result['access_token_secret'], 'access_secret')
        self.assertEqual(result['user_id'], '12345')
        self.assertEqual(result['screen_name'], 'testuser')
    
    def test_token_encryption_decryption(self):
        """Test token encryption and decryption"""
        token_storage = TokenStorageService()
        
        original_token = 'test_access_token_12345'
        original_secret = 'test_access_secret_67890'
        
        # Test encryption
        encrypted_token = token_storage.encrypt_token(original_token)
        encrypted_secret = token_storage.encrypt_token(original_secret)
        
        self.assertNotEqual(encrypted_token, original_token)
        self.assertNotEqual(encrypted_secret, original_secret)
        
        # Test decryption
        decrypted_token = token_storage.decrypt_token(encrypted_token)
        decrypted_secret = token_storage.decrypt_token(encrypted_secret)
        
        self.assertEqual(decrypted_token, original_token)
        self.assertEqual(decrypted_secret, original_secret)
    
    def test_token_storage_and_retrieval(self):
        """Test storing and retrieving OAuth tokens"""
        token_storage = TokenStorageService()
        
        # Store tokens
        success, result = token_storage.store_oauth_tokens(
            user_id=self.test_user.id,
            access_token='test_access_token',
            access_token_secret='test_access_secret',
            twitter_user_id='12345',
            screen_name='testuser'
        )
        
        self.assertTrue(success)
        self.assertIn('token_id', result)
        
        # Retrieve tokens
        success, tokens = token_storage.get_oauth_tokens(
            user_id=self.test_user.id,
            twitter_user_id='12345'
        )
        
        self.assertTrue(success)
        self.assertEqual(tokens['access_token'], 'test_access_token')
        self.assertEqual(tokens['access_token_secret'], 'test_access_secret')
        self.assertEqual(tokens['twitter_user_id'], '12345')
        self.assertEqual(tokens['screen_name'], 'testuser')
    
    def test_twitter_account_creation(self):
        """Test Twitter account creation with OAuth tokens"""
        token_storage = TokenStorageService()
        
        # First store tokens
        success, token_result = token_storage.store_oauth_tokens(
            user_id=self.test_user.id,
            access_token='test_access_token',
            access_token_secret='test_access_secret',
            twitter_user_id='12345',
            screen_name='testuser'
        )
        self.assertTrue(success)
        
        # Create Twitter account
        user_data = {
            'screen_name': 'testuser',
            'name': 'Test User',
            'followers_count': 1000,
            'following_count': 500,
            'verified': False,
            'profile_image_url': 'https://example.com/avatar.jpg'
        }
        
        success, account_result = token_storage.create_or_update_twitter_account(
            user_id=self.test_user.id,
            user_data=user_data,
            oauth_tokens_id=token_result['token_id']
        )
        
        self.assertTrue(success)
        self.assertIn('twitter_account', account_result)
        
        account = account_result['twitter_account']
        self.assertEqual(account['username'], 'testuser')
        self.assertEqual(account['display_name'], 'Test User')
        self.assertEqual(account['connection_status'], 'connected')
    
    @patch('services.x_oauth_service.requests.post')
    def test_oauth_initiate_endpoint(self, mock_post):
        """Test OAuth initiation API endpoint"""
        # Mock successful request token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'oauth_token=test_token&oauth_token_secret=test_secret&oauth_callback_confirmed=true'
        mock_post.return_value = mock_response
        
        response = self.client.post('/api/auth/x/initiate', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('authorization_url', data)
        self.assertIn('oauth_token', data)
        self.assertIn('oauth_token_secret', data)
    
    @patch('services.x_oauth_service.requests.post')
    @patch('services.x_oauth_service.requests.get')
    def test_oauth_callback_endpoint(self, mock_get, mock_post):
        """Test OAuth callback API endpoint"""
        # Mock access token response
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.text = 'oauth_token=access_token&oauth_token_secret=access_secret&user_id=12345&screen_name=testuser'
        mock_post.return_value = mock_post_response
        
        # Mock credentials verification response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'id_str': '12345',
            'screen_name': 'testuser',
            'name': 'Test User',
            'followers_count': 1000,
            'friends_count': 500,
            'verified': False,
            'profile_image_url_https': 'https://example.com/avatar.jpg'
        }
        mock_get.return_value = mock_get_response
        
        callback_data = {
            'oauth_token': 'request_token',
            'oauth_verifier': 'verifier_code',
            'oauth_token_secret': 'request_secret'
        }
        
        response = self.client.post('/api/auth/x/callback', 
                                  json=callback_data, 
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('message', data)
        self.assertIn('twitter_account', data)
        self.assertIn('screen_name', data)
    
    def test_oauth_status_endpoint(self):
        """Test OAuth status API endpoint"""
        # First create a connected account
        token_storage = TokenStorageService()
        
        # Store tokens
        token_storage.store_oauth_tokens(
            user_id=self.test_user.id,
            access_token='test_access_token',
            access_token_secret='test_access_secret',
            twitter_user_id='12345',
            screen_name='testuser'
        )
        
        # Create Twitter account
        user_data = {
            'screen_name': 'testuser',
            'name': 'Test User',
            'followers_count': 1000,
            'following_count': 500,
            'verified': False,
            'profile_image_url': 'https://example.com/avatar.jpg'
        }
        
        token_storage.create_or_update_twitter_account(
            user_id=self.test_user.id,
            user_data=user_data,
            oauth_tokens_id=1
        )
        
        response = self.client.get('/api/auth/x/status', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('connected_accounts', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 1)
    
    def test_oauth_disconnect_endpoint(self):
        """Test OAuth disconnect API endpoint"""
        # First create a connected account
        token_storage = TokenStorageService()
        
        # Store tokens
        success, token_result = token_storage.store_oauth_tokens(
            user_id=self.test_user.id,
            access_token='test_access_token',
            access_token_secret='test_access_secret',
            twitter_user_id='12345',
            screen_name='testuser'
        )
        
        # Create Twitter account
        user_data = {
            'screen_name': 'testuser',
            'name': 'Test User',
            'followers_count': 1000,
            'following_count': 500,
            'verified': False,
            'profile_image_url': 'https://example.com/avatar.jpg'
        }
        
        success, account_result = token_storage.create_or_update_twitter_account(
            user_id=self.test_user.id,
            user_data=user_data,
            oauth_tokens_id=token_result['token_id']
        )
        
        twitter_account_id = account_result['twitter_account']['id']
        
        # Test disconnect
        response = self.client.post('/api/auth/x/disconnect', 
                                  json={'twitter_account_id': twitter_account_id},
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('message', data)
        
        # Verify account is disconnected
        account = TwitterAccount.query.get(twitter_account_id)
        self.assertEqual(account.connection_status, 'revoked')
        self.assertIsNone(account.oauth_tokens_id)

def run_oauth_tests():
    """Run OAuth integration tests"""
    print("Running X OAuth Integration Tests...")
    print("=" * 50)
    
    # Set test environment variables
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    os.environ['TOKEN_ENCRYPTION_KEY'] = test_key
    os.environ['X_API_CONSUMER_KEY'] = 'test_consumer_key'
    os.environ['X_API_CONSUMER_SECRET'] = 'test_consumer_secret'
    
    # Run tests
    unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == '__main__':
    run_oauth_tests()