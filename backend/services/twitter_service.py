import requests
import time
import random
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class TwitterService:
    """Service for interacting with Twitter API via twitterapi.io"""
    
    def __init__(self):
        self.api_key = current_app.config['TWITTER_API_KEY']
        self.base_url = current_app.config['TWITTER_API_BASE_URL']
        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent.random
        })
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None, 
                     retries: int = 3) -> Tuple[bool, Dict]:
        """
        Make authenticated request to Twitter API with rate limiting and anti-bot measures
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(retries):
            try:
                # Add random delay to avoid bot detection
                delay = random.uniform(
                    current_app.config['MIN_DELAY_BETWEEN_REQUESTS'],
                    current_app.config['MAX_DELAY_BETWEEN_REQUESTS']
                )
                time.sleep(delay)
                
                # Randomize user agent
                self.session.headers.update({'User-Agent': self.user_agent.random})
                
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, params=params)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, params=params)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = int(response.headers.get('X-RateLimit-Reset', 900))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    return False, {"error": response.text, "status_code": response.status_code}
                    
            except requests.RequestException as e:
                logger.error(f"Request exception (attempt {attempt + 1}): {str(e)}")
                if attempt == retries - 1:
                    return False, {"error": str(e)}
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False, {"error": "Max retries exceeded"}
    
    def get_user_profile(self, username: str) -> Tuple[bool, Dict]:
        """Get user profile information by username"""
        success, data = self._make_request('GET', f'/v1/users/by/username/{username}')
        
        if success and 'data' in data:
            user_data = data['data']
            return True, {
                'id': user_data.get('id'),
                'username': user_data.get('username'),
                'name': user_data.get('name'),
                'bio': user_data.get('description', ''),
                'followers_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                'following_count': user_data.get('public_metrics', {}).get('following_count', 0),
                'tweet_count': user_data.get('public_metrics', {}).get('tweet_count', 0),
                'verified': user_data.get('verified', False),
                'profile_image_url': user_data.get('profile_image_url', ''),
                'created_at': user_data.get('created_at')
            }
        
        return False, data
    
    def get_user_followers(self, username: str, max_results: int = 100, 
                          pagination_token: str = None) -> Tuple[bool, Dict]:
        """Get followers of a user"""
        # First get user ID
        success, user_data = self.get_user_profile(username)
        if not success:
            return False, user_data
        
        user_id = user_data['id']
        params = {
            'max_results': min(max_results, 1000),  # API limit
            'user.fields': 'description,public_metrics,profile_image_url,verified,created_at'
        }
        
        if pagination_token:
            params['pagination_token'] = pagination_token
        
        success, data = self._make_request('GET', f'/v2/users/{user_id}/followers', params=params)
        
        if success and 'data' in data:
            followers = []
            for follower in data['data']:
                followers.append({
                    'id': follower.get('id'),
                    'username': follower.get('username'),
                    'name': follower.get('name'),
                    'bio': follower.get('description', ''),
                    'followers_count': follower.get('public_metrics', {}).get('followers_count', 0),
                    'following_count': follower.get('public_metrics', {}).get('following_count', 0),
                    'verified': follower.get('verified', False),
                    'profile_image_url': follower.get('profile_image_url', ''),
                    'created_at': follower.get('created_at')
                })
            
            return True, {
                'followers': followers,
                'meta': data.get('meta', {}),
                'next_token': data.get('meta', {}).get('next_token')
            }
        
        return False, data
    
    def send_direct_message(self, recipient_username: str, message: str, 
                           sender_account_tokens: Dict = None) -> Tuple[bool, Dict]:
        """Send a direct message to a user"""
        # This would require user authentication tokens for the sender account
        # For demo purposes, we'll simulate the API call
        
        # First get recipient user ID
        success, user_data = self.get_user_profile(recipient_username)
        if not success:
            return False, user_data
        
        recipient_id = user_data['id']
        
        # Simulate DM sending (in real implementation, you'd need proper OAuth tokens)
        dm_data = {
            'dm_conversation_id': f"dm_{recipient_id}_{int(time.time())}",
            'type': 'MessageCreate',
            'message_create': {
                'target': {
                    'recipient_id': recipient_id
                },
                'message_data': {
                    'text': message
                }
            }
        }
        
        # For now, we'll simulate success (replace with actual API call when you have OAuth)
        logger.info(f"Simulating DM send to {recipient_username}: {message[:50]}...")
        
        return True, {
            'message_id': f"dm_{int(time.time())}_{random.randint(1000, 9999)}",
            'recipient_id': recipient_id,
            'text': message,
            'created_at': datetime.utcnow().isoformat()
        }
    
    def get_direct_messages(self, account_tokens: Dict = None) -> Tuple[bool, Dict]:
        """Get direct messages for an account"""
        # This would require user authentication tokens
        # For demo purposes, we'll return empty list
        return True, {'messages': []}
    
    def like_tweet(self, tweet_id: str, account_tokens: Dict = None) -> Tuple[bool, Dict]:
        """Like a tweet (for warmup activities)"""
        # Simulate liking a tweet
        logger.info(f"Simulating like for tweet {tweet_id}")
        return True, {'liked': True, 'tweet_id': tweet_id}
    
    def retweet(self, tweet_id: str, account_tokens: Dict = None) -> Tuple[bool, Dict]:
        """Retweet a tweet (for warmup activities)"""
        # Simulate retweeting
        logger.info(f"Simulating retweet for tweet {tweet_id}")
        return True, {'retweeted': True, 'tweet_id': tweet_id}
    
    def reply_to_tweet(self, tweet_id: str, reply_text: str, 
                      account_tokens: Dict = None) -> Tuple[bool, Dict]:
        """Reply to a tweet (for warmup activities)"""
        # Simulate replying to a tweet
        logger.info(f"Simulating reply to tweet {tweet_id}: {reply_text[:50]}...")
        return True, {
            'reply_id': f"reply_{int(time.time())}_{random.randint(1000, 9999)}",
            'tweet_id': tweet_id,
            'text': reply_text
        }
    
    def get_trending_tweets(self, limit: int = 50) -> Tuple[bool, Dict]:
        """Get trending tweets for warmup interaction"""
        success, data = self._make_request('GET', '/v2/tweets/search/recent', {
            'query': 'lang:en -is:retweet',
            'max_results': min(limit, 100),
            'tweet.fields': 'public_metrics,created_at,author_id',
            'expansions': 'author_id',
            'user.fields': 'username,name'
        })
        
        if success and 'data' in data:
            tweets = []
            users = {user['id']: user for user in data.get('includes', {}).get('users', [])}
            
            for tweet in data['data']:
                author = users.get(tweet.get('author_id'), {})
                tweets.append({
                    'id': tweet.get('id'),
                    'text': tweet.get('text'),
                    'author_id': tweet.get('author_id'),
                    'author_username': author.get('username'),
                    'author_name': author.get('name'),
                    'public_metrics': tweet.get('public_metrics', {}),
                    'created_at': tweet.get('created_at')
                })
            
            return True, {'tweets': tweets}
        
        return False, data
    
    def search_users(self, query: str, limit: int = 50) -> Tuple[bool, Dict]:
        """Search for users by query"""
        # Note: This endpoint might not be available in all Twitter API tiers
        params = {
            'q': query,
            'result_type': 'users',
            'count': min(limit, 100)
        }
        
        success, data = self._make_request('GET', '/v1/users/search', params=params)
        
        if success:
            return True, data
        
        return False, data
    
    def validate_account_credentials(self, account_tokens: Dict) -> Tuple[bool, Dict]:
        """Validate Twitter account credentials"""
        # This would verify the provided OAuth tokens
        # For demo purposes, we'll return success
        return True, {'valid': True, 'username': 'demo_account'}
    
    def get_account_limits(self) -> Dict:
        """Get current API rate limits and usage"""
        # Return current rate limit status
        return {
            'dm_limit': 1000,
            'dm_used': 0,
            'follower_limit': 15,
            'follower_used': 0,
            'search_limit': 300,
            'search_used': 0,
            'reset_time': (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        }

# Anti-bot detection utilities
class AntiBot:
    """Utilities for avoiding bot detection"""
    
    @staticmethod
    def random_delay(min_seconds: float = 1.0, max_seconds: float = 5.0):
        """Add random delay between requests"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def human_like_typing_delay(text: str) -> float:
        """Calculate human-like typing delay based on text length"""
        base_delay = 0.05  # Base delay per character
        random_factor = random.uniform(0.8, 1.2)
        return len(text) * base_delay * random_factor
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent string"""
        ua = UserAgent()
        return ua.random
    
    @staticmethod
    def should_take_break() -> bool:
        """Determine if we should take a longer break (simulate human behavior)"""
        return random.random() < 0.1  # 10% chance of taking a break
    
    @staticmethod
    def get_break_duration() -> int:
        """Get random break duration in seconds"""
        return random.randint(300, 1800)  # 5-30 minutes
