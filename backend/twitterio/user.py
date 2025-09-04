"""
TwitterAPI.io User Module
Handles user-related operations like follow/unfollow using twitterapi.io endpoints
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
class ActionResult:
    """Result of user actions (follow, unfollow, etc.)"""
    status: str
    message: Optional[str] = None

@dataclass
class TwitterUser:
    """Twitter user data structure"""
    id: str
    username: str
    name: str
    profile_picture: Optional[str] = None
    description: Optional[str] = None
    followers: int = 0
    following: int = 0
    can_dm: bool = False
    verified: bool = False
    created_at: Optional[str] = None

class TwitterUserClient:
    """Twitter User client using twitterapi.io"""
    
    def __init__(self, login_cookie: Optional[str] = None, proxy: Optional[str] = None):
        """
        Initialize User client
        
        Args:
            login_cookie: Login cookie from authentication (required for actions)
            proxy: Optional proxy URL
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
    
    def follow_user(self, user_id: str) -> ActionResult:
        """
        Follow a user using twitterapi.io follow_user_v2 endpoint
        
        According to the API docs:
        POST /twitter/follow_user_v2
        - Requires: login_cookies, user_id, proxy
        - Returns: status, msg
        
        Args:
            user_id: ID of user to follow
            
        Returns:
            ActionResult: Follow result
            
        Raises:
            TwitterAPIError: If follow fails or not authenticated
        """
        if not self.login_cookie:
            raise TwitterAPIError("Authentication required. Please login first.")
        
        if not user_id:
            raise TwitterAPIError("User ID is required")
        
        data = {"user_id": user_id}
        
        logger.info(f"Following user: {user_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/follow_user_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully followed user: {user_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to follow user {user_id}: {e}")
            raise
    
    def unfollow_user(self, user_id: str) -> ActionResult:
        """
        Unfollow a user using twitterapi.io unfollow_user_v2 endpoint
        
        According to the API docs:
        POST /twitter/unfollow_user_v2
        - Requires: login_cookies, user_id, proxy
        - Returns: status, msg
        
        Args:
            user_id: ID of user to unfollow
            
        Returns:
            ActionResult: Unfollow result
            
        Raises:
            TwitterAPIError: If unfollow fails or not authenticated
        """
        if not self.login_cookie:
            raise TwitterAPIError("Authentication required. Please login first.")
        
        if not user_id:
            raise TwitterAPIError("User ID is required")
        
        data = {"user_id": user_id}
        
        logger.info(f"Unfollowing user: {user_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/unfollow_user_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = ActionResult(
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully unfollowed user: {user_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to unfollow user {user_id}: {e}")
            raise
    
    def get_user_info(self, username: str) -> TwitterUser:
        """
        Get user information by username using twitterapi.io user info endpoint
        
        According to the API docs:
        GET /twitter/user/info
        - Requires: userName (query param)
        - Returns: data object with user info
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            TwitterUser: User information
            
        Raises:
            TwitterAPIError: If user lookup fails
        """
        if not username:
            raise TwitterAPIError("Username is required")
        
        params = {"userName": username}
        
        logger.info(f"Getting user info for: {username}")
        
        try:
            response = self.core_client.make_request(
                method="GET",
                endpoint="/twitter/user/info",
                params=params,
                proxy=self.proxy
            )
            
            user_data = response.get("data", {})
            if not user_data:
                raise TwitterAPIError(f"User not found: {username}")
            
            user = TwitterUser(
                id=user_data.get("id", ""),
                username=user_data.get("userName", username),
                name=user_data.get("name", ""),
                profile_picture=user_data.get("profilePicture", ""),
                description=user_data.get("description", ""),
                followers=user_data.get("followers", 0),
                following=user_data.get("following", 0),
                can_dm=user_data.get("canDm", False),
                verified=user_data.get("isBlueVerified", False),
                created_at=user_data.get("createdAt")
            )
            
            logger.info(f"Successfully retrieved user info for: {username}")
            return user
            
        except TwitterAPIError as e:
            logger.error(f"Failed to get user info for {username}: {e}")
            raise
    
    def search_users(self, keyword: str, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for users by keyword
        
        Args:
            keyword: Search keyword
            cursor: Optional pagination cursor
            
        Returns:
            Dict: Search results with users and pagination info
        """
        if not keyword:
            raise TwitterAPIError("Search keyword is required")
        
        params = {"keyword": keyword}
        if cursor:
            params["cursor"] = cursor
        
        logger.info(f"Searching users with keyword: {keyword}")
        
        try:
            response = self.core_client.make_request(
                method="GET",
                endpoint="/twitter/user/search",
                params=params,
                proxy=self.proxy
            )
            
            logger.info(f"User search completed for keyword: {keyword}")
            return response
            
        except TwitterAPIError as e:
            logger.error(f"Failed to search users with keyword {keyword}: {e}")
            raise


# Convenience functions
def follow_user(login_cookie: str, user_id: str, proxy: Optional[str] = None) -> ActionResult:
    """
    Convenience function to follow a user
    
    Args:
        login_cookie: Login cookie from authentication
        user_id: ID of user to follow
        proxy: Optional proxy URL
        
    Returns:
        ActionResult: Follow result
    """
    user_client = TwitterUserClient(login_cookie=login_cookie, proxy=proxy)
    return user_client.follow_user(user_id)

def unfollow_user(login_cookie: str, user_id: str, proxy: Optional[str] = None) -> ActionResult:
    """
    Convenience function to unfollow a user
    
    Args:
        login_cookie: Login cookie from authentication
        user_id: ID of user to unfollow
        proxy: Optional proxy URL
        
    Returns:
        ActionResult: Unfollow result
    """
    user_client = TwitterUserClient(login_cookie=login_cookie, proxy=proxy)
    return user_client.unfollow_user(user_id)

def get_user_info(username: str, proxy: Optional[str] = None) -> TwitterUser:
    """
    Convenience function to get user information
    
    Args:
        username: Twitter username
        proxy: Optional proxy URL
        
    Returns:
        TwitterUser: User information
    """
    user_client = TwitterUserClient(proxy=proxy)
    return user_client.get_user_info(username)

def search_users(keyword: str, cursor: Optional[str] = None, proxy: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to search users
    
    Args:
        keyword: Search keyword
        cursor: Optional pagination cursor
        proxy: Optional proxy URL
        
    Returns:
        Dict: Search results
    """
    user_client = TwitterUserClient(proxy=proxy)
    return user_client.search_users(keyword, cursor)
