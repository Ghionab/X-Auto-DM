"""
TwitterAPI.io Tweet Module
Handles creating, deleting, liking, and retweeting tweets using twitterapi.io endpoints
"""

import logging
from typing import Optional, Dict, Any, List
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
class TweetResult:
    """Result of tweet operations"""
    tweet_id: Optional[str] = None
    status: str = "unknown"
    message: Optional[str] = None

@dataclass 
class ActionResult:
    """Result of tweet actions (like, retweet, etc.)"""
    status: str
    message: Optional[str] = None

class TwitterTweetClient:
    """Twitter Tweet client using twitterapi.io"""
    
    def __init__(self, login_cookie: str, proxy: Optional[str] = None):
        """
        Initialize Tweet client with authentication
        
        Args:
            login_cookie: Login cookie from authentication
            proxy: Optional proxy URL
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
    
    def create_tweet(self, tweet_text: str,
                    reply_to_tweet_id: Optional[str] = None,
                    attachment_url: Optional[str] = None,
                    community_id: Optional[str] = None,
                    is_note_tweet: bool = False,
                    media_ids: Optional[List[str]] = None) -> TweetResult:
        """
        Create a tweet using twitterapi.io create_tweet_v2 endpoint
        
        According to the API docs:
        POST /twitter/create_tweet_v2
        - Requires: login_cookies, tweet_text, proxy
        - Optional: reply_to_tweet_id, attachment_url, community_id, is_note_tweet, media_ids
        - Returns: tweet_id, status, msg
        
        Args:
            tweet_text: Tweet content
            reply_to_tweet_id: Optional tweet ID to reply to
            attachment_url: Optional URL to attach
            community_id: Optional community ID for community tweets
            is_note_tweet: Whether this is a note tweet (long form)
            media_ids: Optional list of media IDs to attach
            
        Returns:
            TweetResult: Result with tweet ID and status
            
        Raises:
            TwitterAPIError: If tweet creation fails
        """
        if not tweet_text or not tweet_text.strip():
            raise TwitterAPIError("Tweet text is required")
        
        data = {
            "tweet_text": tweet_text.strip(),
            "reply_to_tweet_id": reply_to_tweet_id or "",
            "attachment_url": attachment_url or "",
            "community_id": community_id or "",
            "is_note_tweet": is_note_tweet,
            "media_ids": media_ids or []
        }
        
        logger.info(f"Creating tweet: {tweet_text[:50]}...")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/create_tweet_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = TweetResult(
                tweet_id=response.get("tweet_id"),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully created tweet, ID: {result.tweet_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to create tweet: {e}")
            raise
    
    def delete_tweet(self, tweet_id: str) -> ActionResult:
        """
        Delete a tweet using twitterapi.io delete_tweet_v2 endpoint
        
        According to the API docs:
        POST /twitter/delete_tweet_v2
        - Requires: login_cookies, tweet_id, proxy
        - Returns: status, msg
        
        Args:
            tweet_id: ID of tweet to delete
            
        Returns:
            ActionResult: Deletion result
        """
        if not tweet_id:
            raise TwitterAPIError("Tweet ID is required")
        
        data = {"tweet_id": tweet_id}
        
        logger.info(f"Deleting tweet: {tweet_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/delete_tweet_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully deleted tweet: {tweet_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to delete tweet {tweet_id}: {e}")
            raise
    
    def like_tweet(self, tweet_id: str) -> ActionResult:
        """
        Like a tweet using twitterapi.io like_tweet_v2 endpoint
        
        According to the API docs:
        POST /twitter/like_tweet_v2
        - Requires: login_cookies, tweet_id, proxy
        - Returns: status, msg
        
        Args:
            tweet_id: ID of tweet to like
            
        Returns:
            ActionResult: Like result
        """
        if not tweet_id:
            raise TwitterAPIError("Tweet ID is required")
        
        data = {"tweet_id": tweet_id}
        
        logger.info(f"Liking tweet: {tweet_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/like_tweet_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully liked tweet: {tweet_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to like tweet {tweet_id}: {e}")
            raise
    
    def unlike_tweet(self, tweet_id: str) -> ActionResult:
        """
        Unlike a tweet using twitterapi.io unlike_tweet_v2 endpoint
        
        According to the API docs:
        POST /twitter/unlike_tweet_v2
        - Requires: login_cookies, tweet_id, proxy
        - Returns: status, msg
        
        Args:
            tweet_id: ID of tweet to unlike
            
        Returns:
            ActionResult: Unlike result
        """
        if not tweet_id:
            raise TwitterAPIError("Tweet ID is required")
        
        data = {"tweet_id": tweet_id}
        
        logger.info(f"Unliking tweet: {tweet_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/unlike_tweet_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully unliked tweet: {tweet_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to unlike tweet {tweet_id}: {e}")
            raise
    
    def retweet_tweet(self, tweet_id: str) -> ActionResult:
        """
        Retweet a tweet using twitterapi.io retweet_tweet_v2 endpoint
        
        According to the API docs:
        POST /twitter/retweet_tweet_v2
        - Requires: login_cookies, tweet_id, proxy
        - Returns: status, msg
        
        Args:
            tweet_id: ID of tweet to retweet
            
        Returns:
            ActionResult: Retweet result
        """
        if not tweet_id:
            raise TwitterAPIError("Tweet ID is required")
        
        data = {"tweet_id": tweet_id}
        
        logger.info(f"Retweeting tweet: {tweet_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/retweet_tweet_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully retweeted tweet: {tweet_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to retweet tweet {tweet_id}: {e}")
            raise


# Convenience functions
def create_tweet(login_cookie: str, tweet_text: str,
                reply_to_tweet_id: Optional[str] = None,
                attachment_url: Optional[str] = None,
                community_id: Optional[str] = None,
                is_note_tweet: bool = False,
                media_ids: Optional[List[str]] = None,
                proxy: Optional[str] = None) -> TweetResult:
    """
    Convenience function to create a tweet
    
    Args:
        login_cookie: Login cookie from authentication
        tweet_text: Tweet content
        reply_to_tweet_id: Optional tweet ID to reply to
        attachment_url: Optional URL to attach
        community_id: Optional community ID
        is_note_tweet: Whether this is a note tweet
        media_ids: Optional media IDs
        proxy: Optional proxy URL
        
    Returns:
        TweetResult: Tweet creation result
    """
    tweet_client = TwitterTweetClient(login_cookie=login_cookie, proxy=proxy)
    return tweet_client.create_tweet(
        tweet_text, reply_to_tweet_id, attachment_url, 
        community_id, is_note_tweet, media_ids
    )

def delete_tweet(login_cookie: str, tweet_id: str, proxy: Optional[str] = None) -> ActionResult:
    """Convenience function to delete a tweet"""
    tweet_client = TwitterTweetClient(login_cookie=login_cookie, proxy=proxy)
    return tweet_client.delete_tweet(tweet_id)

def like_tweet(login_cookie: str, tweet_id: str, proxy: Optional[str] = None) -> ActionResult:
    """Convenience function to like a tweet"""
    tweet_client = TwitterTweetClient(login_cookie=login_cookie, proxy=proxy)
    return tweet_client.like_tweet(tweet_id)

def unlike_tweet(login_cookie: str, tweet_id: str, proxy: Optional[str] = None) -> ActionResult:
    """Convenience function to unlike a tweet"""
    tweet_client = TwitterTweetClient(login_cookie=login_cookie, proxy=proxy)
    return tweet_client.unlike_tweet(tweet_id)

def retweet_tweet(login_cookie: str, tweet_id: str, proxy: Optional[str] = None) -> ActionResult:
    """Convenience function to retweet a tweet"""
    tweet_client = TwitterTweetClient(login_cookie=login_cookie, proxy=proxy)
    return tweet_client.retweet_tweet(tweet_id)
