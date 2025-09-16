"""
TwitterAPI.io Client Integration Service
Provides high-level methods for interacting with TwitterAPI.io endpoints
with pagination support, rate limiting, and error handling.
"""

import logging
import time
from typing import Dict, List, Optional, Generator, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from twitterapi_core import get_core_client, TwitterAPIError

logger = logging.getLogger(__name__)

@dataclass
class TwitterUser:
    """Represents a Twitter user from API responses"""
    id: str
    username: str
    name: str
    profile_picture: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    can_dm: bool = True
    is_verified: bool = False
    verified_type: Optional[str] = None
    created_at: Optional[str] = None
    favourites_count: int = 0
    statuses_count: int = 0
    is_blue_verified: bool = False
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'TwitterUser':
        """Create TwitterUser from API response data"""
        return cls(
            id=data.get('id', ''),
            username=data.get('userName', ''),
            name=data.get('name', ''),
            profile_picture=data.get('profilePicture'),
            description=data.get('description'),
            location=data.get('location'),
            followers_count=data.get('followers', 0),
            following_count=data.get('following', 0),
            can_dm=data.get('canDm', True),
            is_verified=data.get('isBlueVerified', False),
            verified_type=data.get('verifiedType'),
            created_at=data.get('createdAt'),
            favourites_count=data.get('favouritesCount', 0),
            statuses_count=data.get('statusesCount', 0),
            is_blue_verified=data.get('isBlueVerified', False)
        )

@dataclass
class PaginationResult:
    """Represents paginated API response"""
    items: List[TwitterUser]
    has_next_page: bool
    next_cursor: Optional[str]
    total_fetched: int

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.call_times: List[datetime] = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        
        # Remove calls older than 1 minute
        cutoff = now - timedelta(minutes=1)
        self.call_times = [t for t in self.call_times if t > cutoff]
        
        # Check if we need to wait
        if len(self.call_times) >= self.calls_per_minute:
            oldest_call = min(self.call_times)
            wait_time = 60 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Record this call
        self.call_times.append(now)

class TwitterAPIClient:
    """High-level client for TwitterAPI.io with pagination and rate limiting"""
    
    def __init__(self, login_cookie: Optional[str] = None, proxy: Optional[str] = None):
        """
        Initialize the TwitterAPI client
        
        Args:
            login_cookie: Session cookie for authenticated requests
            proxy: Proxy URL (uses default if not provided)
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
        self.rate_limiter = RateLimiter(calls_per_minute=50)  # Conservative rate limit
        
        logger.info("TwitterAPI client initialized")
    
    def get_user_followers(self, username: str, max_followers: Optional[int] = None,
                          page_size: int = 200) -> Generator[PaginationResult, None, None]:
        """
        Get followers for a user with pagination support
        
        Args:
            username: Twitter username (without @)
            max_followers: Maximum number of followers to fetch (None for all)
            page_size: Number of followers per page (20-200, default 200)
            
        Yields:
            PaginationResult: Paginated results with followers data
            
        Raises:
            TwitterAPIError: If API request fails
            ValueError: If parameters are invalid
        """
        if not username:
            raise ValueError("Username is required")
        
        if page_size < 20 or page_size > 200:
            raise ValueError("Page size must be between 20 and 200")
        
        logger.info(f"Starting to fetch followers for user: {username}")
        
        cursor = ""
        total_fetched = 0
        
        while True:
            # Check rate limit
            self.rate_limiter.wait_if_needed()
            
            # Check if we've reached the max limit
            if max_followers and total_fetched >= max_followers:
                logger.info(f"Reached maximum followers limit: {max_followers}")
                break
            
            # Adjust page size if we're near the limit
            current_page_size = page_size
            if max_followers:
                remaining = max_followers - total_fetched
                current_page_size = min(page_size, remaining)
            
            try:
                logger.info(f"Fetching followers page (cursor: {cursor or 'first'}, page_size: {current_page_size})")
                
                params = {
                    'userName': username,
                    'pageSize': current_page_size
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                response = self.core_client.make_request(
                    method='GET',
                    endpoint='/twitter/user/followers',
                    params=params,
                    login_cookie=self.login_cookie,
                    proxy=self.proxy
                )
                
                # Parse response
                followers_data = response.get('followers', [])
                followers = [TwitterUser.from_api_response(user) for user in followers_data]
                
                # Check for pagination info
                has_next_page = response.get('has_next_page', False)
                next_cursor = response.get('next_cursor')
                
                total_fetched += len(followers)
                
                # If we have a max limit and exceeded it, trim the followers list
                if max_followers and total_fetched > max_followers:
                    excess = total_fetched - max_followers
                    followers = followers[:-excess]
                    total_fetched = max_followers
                    has_next_page = False
                
                logger.info(f"Fetched {len(followers)} followers (total: {total_fetched})")
                
                yield PaginationResult(
                    items=followers,
                    has_next_page=has_next_page and (not max_followers or total_fetched < max_followers),
                    next_cursor=next_cursor,
                    total_fetched=total_fetched
                )
                
                # Check if we should continue
                if not has_next_page or not next_cursor:
                    logger.info("No more pages available")
                    break
                
                cursor = next_cursor
                
            except TwitterAPIError as e:
                logger.error(f"Error fetching followers for {username}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching followers for {username}: {e}")
                raise TwitterAPIError(f"Unexpected error: {str(e)}")
    
    def get_list_members(self, list_id: str, max_members: Optional[int] = None) -> Generator[PaginationResult, None, None]:
        """
        Get members of a Twitter list with pagination support
        
        Args:
            list_id: Twitter list ID
            max_members: Maximum number of members to fetch (None for all)
            
        Yields:
            PaginationResult: Paginated results with list members data
            
        Raises:
            TwitterAPIError: If API request fails
            ValueError: If parameters are invalid
        """
        if not list_id:
            raise ValueError("List ID is required")
        
        logger.info(f"Starting to fetch members for list: {list_id}")
        
        cursor = ""
        total_fetched = 0
        
        while True:
            # Check rate limit
            self.rate_limiter.wait_if_needed()
            
            # Check if we've reached the max limit
            if max_members and total_fetched >= max_members:
                logger.info(f"Reached maximum members limit: {max_members}")
                break
            
            try:
                logger.info(f"Fetching list members page (cursor: {cursor or 'first'})")
                
                params = {
                    'list_id': list_id
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                response = self.core_client.make_request(
                    method='GET',
                    endpoint='/twitter/list/members',
                    params=params,
                    login_cookie=self.login_cookie,
                    proxy=self.proxy
                )
                
                # Parse response
                members_data = response.get('members', [])
                members = [TwitterUser.from_api_response(user) for user in members_data]
                
                # Check for pagination info
                has_next_page = response.get('has_next_page', False)
                next_cursor = response.get('next_cursor')
                
                total_fetched += len(members)
                
                logger.info(f"Fetched {len(members)} list members (total: {total_fetched})")
                
                # If we have a max limit, only return the members we need
                if max_members and total_fetched > max_members:
                    excess = total_fetched - max_members
                    members = members[:-excess]
                    total_fetched = max_members
                    has_next_page = False
                
                yield PaginationResult(
                    items=members,
                    has_next_page=has_next_page and (not max_members or total_fetched < max_members),
                    next_cursor=next_cursor,
                    total_fetched=total_fetched
                )
                
                # Check if we should continue
                if not has_next_page or not next_cursor:
                    logger.info("No more pages available")
                    break
                
                if max_members and total_fetched >= max_members:
                    logger.info(f"Reached maximum members limit: {max_members}")
                    break
                
                cursor = next_cursor
                
            except TwitterAPIError as e:
                logger.error(f"Error fetching list members for {list_id}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching list members for {list_id}: {e}")
                raise TwitterAPIError(f"Unexpected error: {str(e)}")
    
    def get_all_user_followers(self, username: str, max_followers: Optional[int] = None) -> List[TwitterUser]:
        """
        Get all followers for a user (convenience method)
        
        Args:
            username: Twitter username (without @)
            max_followers: Maximum number of followers to fetch (None for all)
            
        Returns:
            List[TwitterUser]: List of all followers
            
        Raises:
            TwitterAPIError: If API request fails
        """
        all_followers = []
        
        for page_result in self.get_user_followers(username, max_followers):
            all_followers.extend(page_result.items)
            
            if not page_result.has_next_page:
                break
        
        logger.info(f"Fetched total of {len(all_followers)} followers for {username}")
        return all_followers
    
    def get_all_list_members(self, list_id: str, max_members: Optional[int] = None) -> List[TwitterUser]:
        """
        Get all members of a Twitter list (convenience method)
        
        Args:
            list_id: Twitter list ID
            max_members: Maximum number of members to fetch (None for all)
            
        Returns:
            List[TwitterUser]: List of all list members
            
        Raises:
            TwitterAPIError: If API request fails
        """
        all_members = []
        
        for page_result in self.get_list_members(list_id, max_members):
            all_members.extend(page_result.items)
            
            if not page_result.has_next_page:
                break
        
        logger.info(f"Fetched total of {len(all_members)} members for list {list_id}")
        return all_members
    
    def validate_user_exists(self, username: str) -> bool:
        """
        Check if a user exists by attempting to fetch their followers
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            bool: True if user exists and is accessible
        """
        try:
            # Try to fetch just one page with minimal results
            for page_result in self.get_user_followers(username, max_followers=1):
                return True
            return True  # If we get here, user exists but has no followers
        except TwitterAPIError as e:
            logger.warning(f"User validation failed for {username}: {e}")
            return False
    
    def validate_list_exists(self, list_id: str) -> bool:
        """
        Check if a list exists by attempting to fetch its members
        
        Args:
            list_id: Twitter list ID
            
        Returns:
            bool: True if list exists and is accessible
        """
        try:
            # Try to fetch just one page with minimal results
            for page_result in self.get_list_members(list_id, max_members=1):
                return True
            return True  # If we get here, list exists but has no members
        except TwitterAPIError as e:
            logger.warning(f"List validation failed for {list_id}: {e}")
            return False

def create_client(login_cookie: Optional[str] = None, proxy: Optional[str] = None) -> TwitterAPIClient:
    """
    Factory function to create a TwitterAPI client
    
    Args:
        login_cookie: Session cookie for authenticated requests
        proxy: Proxy URL (uses default if not provided)
        
    Returns:
        TwitterAPIClient: Configured client instance
    """
    return TwitterAPIClient(login_cookie=login_cookie, proxy=proxy)