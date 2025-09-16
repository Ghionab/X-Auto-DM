"""
Username Resolution Service
Handles username-to-user-ID conversion and user information caching for XReacher
"""

import logging
import re
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

from twitterio import get_user_info, TwitterAPIError, TwitterUser
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class UserResolution:
    """User resolution result with caching metadata"""
    user_id: str
    username: str
    name: str
    profile_picture: Optional[str] = None
    can_dm: bool = False
    verified: bool = False
    exists: bool = True
    cached_at: datetime = None
    
    def __post_init__(self):
        if self.cached_at is None:
            self.cached_at = datetime.now(timezone.utc)
    
    def is_expired(self, ttl_hours: int = 1) -> bool:
        """Check if cached data is expired"""
        if not self.cached_at:
            return True
        expiry_time = self.cached_at + timedelta(hours=ttl_hours)
        return datetime.now(timezone.utc) > expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['cached_at'] = self.cached_at.isoformat() if self.cached_at else None
        return data

@dataclass
class UserInfo:
    """Comprehensive user information"""
    user_id: str
    username: str
    name: str
    profile_picture: Optional[str] = None
    description: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    can_dm: bool = False
    verified: bool = False
    exists: bool = True
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

class UsernameResolverError(Exception):
    """Custom exception for username resolution errors"""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", username: str = None):
        self.message = message
        self.error_code = error_code
        self.username = username
        super().__init__(self.message)

class UsernameResolver:
    """
    Service for resolving Twitter usernames to user IDs with caching
    
    This service handles:
    - Username normalization and validation
    - API calls to twitterapi.io for user information
    - In-memory caching with TTL for performance
    - Comprehensive error handling
    """
    
    def __init__(self, api_key: Optional[str] = None, proxy: Optional[str] = None):
        """
        Initialize username resolver
        
        Args:
            api_key: TwitterAPI.io API key (optional, uses config if not provided)
            proxy: Optional proxy URL for API requests
        """
        self.api_key = api_key or Config.TWITTER_API_KEY
        self.proxy = proxy
        self.cache: Dict[str, UserResolution] = {}
        self.cache_ttl_hours = 1  # 1 hour TTL as per requirements
        
        logger.info("UsernameResolver initialized")
    
    def _normalize_username(self, username: str) -> str:
        """
        Normalize and validate username format
        
        Args:
            username: Raw username input (may include @)
            
        Returns:
            str: Normalized username without @
            
        Raises:
            UsernameResolverError: If username format is invalid
        """
        if not username or not isinstance(username, str):
            raise UsernameResolverError(
                "Username is required and must be a string",
                "INVALID_USERNAME_FORMAT",
                username
            )
        
        # Remove @ symbol if present
        normalized = username.strip().lstrip('@')
        
        if not normalized:
            raise UsernameResolverError(
                "Username cannot be empty",
                "INVALID_USERNAME_FORMAT", 
                username
            )
        
        # Validate Twitter username format
        # Twitter usernames: 1-15 characters, letters, numbers, underscores only
        if not re.match(r'^[a-zA-Z0-9_]{1,15}$', normalized):
            raise UsernameResolverError(
                "Invalid username format. Use letters, numbers, and underscores only (1-15 characters)",
                "INVALID_USERNAME_FORMAT",
                username
            )
        
        return normalized
    
    def _cache_user_info(self, username: str, user_resolution: UserResolution) -> None:
        """
        Cache user resolution with TTL
        
        Args:
            username: Normalized username
            user_resolution: User resolution data to cache
        """
        try:
            self.cache[username.lower()] = user_resolution
            logger.debug(f"Cached user info for @{username}")
        except Exception as e:
            logger.warning(f"Failed to cache user info for @{username}: {e}")
    
    def _get_cached_user_info(self, username: str) -> Optional[UserResolution]:
        """
        Get cached user resolution if not expired
        
        Args:
            username: Normalized username
            
        Returns:
            UserResolution or None if not cached or expired
        """
        try:
            cached = self.cache.get(username.lower())
            if cached and not cached.is_expired(self.cache_ttl_hours):
                logger.debug(f"Cache hit for @{username}")
                return cached
            elif cached:
                # Remove expired entry
                del self.cache[username.lower()]
                logger.debug(f"Cache expired for @{username}")
        except Exception as e:
            logger.warning(f"Error checking cache for @{username}: {e}")
        
        return None
    
    async def resolve_username(self, username: str) -> UserResolution:
        """
        Resolve username to user ID using twitterapi.io
        
        This method:
        1. Normalizes and validates the username
        2. Checks cache for existing resolution
        3. Calls twitterapi.io API if not cached
        4. Caches the result for future use
        
        Args:
            username: X username (with or without @)
            
        Returns:
            UserResolution: Object with user_id, username, name, can_dm status
            
        Raises:
            UsernameResolverError: If username is invalid or resolution fails
        """
        try:
            # Normalize username
            normalized_username = self._normalize_username(username)
            
            # Check cache first
            cached_result = self._get_cached_user_info(normalized_username)
            if cached_result:
                logger.info(f"Username resolution cache hit for @{normalized_username}")
                return cached_result
            
            # Get user info from API
            user_info = await self.get_user_info(normalized_username)
            
            # Convert to UserResolution
            resolution = UserResolution(
                user_id=user_info.user_id,
                username=user_info.username,
                name=user_info.name,
                profile_picture=user_info.profile_picture,
                can_dm=user_info.can_dm,
                verified=user_info.verified,
                exists=user_info.exists,
                cached_at=datetime.now(timezone.utc)
            )
            
            # Cache the result
            self._cache_user_info(normalized_username, resolution)
            
            logger.info(f"Successfully resolved @{normalized_username} to user_id {resolution.user_id}")
            return resolution
            
        except UsernameResolverError:
            # Re-raise our custom errors
            raise
        except TwitterAPIError as e:
            error_message = str(e).lower()
            
            # Map TwitterAPI errors to our error codes
            if 'not found' in error_message or 'user not found' in error_message:
                raise UsernameResolverError(
                    f"Username '@{username}' not found. Please check the spelling and try again.",
                    "USERNAME_NOT_FOUND",
                    username
                )
            elif 'rate limit' in error_message:
                raise UsernameResolverError(
                    "Too many requests. Please wait a moment and try again.",
                    "RATE_LIMITED",
                    username
                )
            elif 'suspended' in error_message or 'locked' in error_message:
                raise UsernameResolverError(
                    f"Account '@{username}' is suspended or locked.",
                    "ACCOUNT_SUSPENDED",
                    username
                )
            else:
                raise UsernameResolverError(
                    f"Unable to verify username '@{username}'. Please try again.",
                    "API_ERROR",
                    username
                )
        except UsernameResolverError as e:
            # Handle errors from get_user_info that are already UsernameResolverError
            if e.error_code == "API_ERROR" and "rate limit" in e.message.lower():
                raise UsernameResolverError(
                    "Too many requests. Please wait a moment and try again.",
                    "RATE_LIMITED",
                    username
                )
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error resolving username @{username}: {e}")
            raise UsernameResolverError(
                f"Failed to resolve username '@{username}'. Please try again.",
                "INTERNAL_ERROR",
                username
            )
    
    async def get_user_info(self, username: str) -> UserInfo:
        """
        Get comprehensive user information using twitterapi.io
        
        Uses: GET /twitter/user/info?userName={username}
        
        Args:
            username: Twitter username (normalized, without @)
            
        Returns:
            UserInfo: Comprehensive user information
            
        Raises:
            UsernameResolverError: If user lookup fails
        """
        try:
            logger.info(f"Fetching user info for @{username}")
            
            # Call twitterapi.io user info endpoint
            twitter_user: TwitterUser = get_user_info(username, proxy=self.proxy)
            
            # Convert TwitterUser to our UserInfo format
            user_info = UserInfo(
                user_id=twitter_user.id,
                username=twitter_user.username,
                name=twitter_user.name,
                profile_picture=twitter_user.profile_picture,
                description=twitter_user.description,
                followers_count=twitter_user.followers,
                following_count=twitter_user.following,
                can_dm=twitter_user.can_dm,
                verified=twitter_user.verified,
                exists=True,
                created_at=twitter_user.created_at
            )
            
            logger.info(f"Successfully fetched user info for @{username}")
            return user_info
            
        except TwitterAPIError as e:
            error_message = str(e).lower()
            
            if 'not found' in error_message or 'user not found' in error_message:
                # Return UserInfo with exists=False for not found users
                return UserInfo(
                    user_id="",
                    username=username,
                    name="",
                    exists=False
                )
            elif 'rate limit' in error_message:
                raise UsernameResolverError(
                    "Too many requests. Please wait a moment and try again.",
                    "RATE_LIMITED",
                    username
                )
            else:
                # Re-raise for other API errors
                raise UsernameResolverError(
                    f"Failed to get user info for '@{username}': {str(e)}",
                    "API_ERROR",
                    username
                )
        except Exception as e:
            logger.error(f"Unexpected error getting user info for @{username}: {e}")
            raise UsernameResolverError(
                f"Failed to get user info for '@{username}'. Please try again.",
                "INTERNAL_ERROR",
                username
            )
    
    def clear_cache(self) -> None:
        """Clear all cached username resolutions"""
        self.cache.clear()
        logger.info("Username resolution cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() 
                            if entry.is_expired(self.cache_ttl_hours))
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "cache_ttl_hours": self.cache_ttl_hours
        }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired entries from cache and return count removed"""
        expired_usernames = [
            username for username, entry in self.cache.items()
            if entry.is_expired(self.cache_ttl_hours)
        ]
        
        for username in expired_usernames:
            del self.cache[username]
        
        if expired_usernames:
            logger.info(f"Cleaned up {len(expired_usernames)} expired cache entries")
        
        return len(expired_usernames)

# Global instance for convenience
_username_resolver_instance: Optional[UsernameResolver] = None

def get_username_resolver(api_key: Optional[str] = None, proxy: Optional[str] = None) -> UsernameResolver:
    """
    Get or create global username resolver instance
    
    Args:
        api_key: TwitterAPI.io API key (optional)
        proxy: Optional proxy URL
        
    Returns:
        UsernameResolver: Global instance
    """
    global _username_resolver_instance
    
    if _username_resolver_instance is None:
        _username_resolver_instance = UsernameResolver(api_key=api_key, proxy=proxy)
    
    return _username_resolver_instance

# Convenience functions for direct usage
async def resolve_username(username: str, api_key: Optional[str] = None, proxy: Optional[str] = None) -> UserResolution:
    """
    Convenience function to resolve a username
    
    Args:
        username: Twitter username to resolve
        api_key: Optional API key
        proxy: Optional proxy URL
        
    Returns:
        UserResolution: Resolution result
    """
    resolver = get_username_resolver(api_key=api_key, proxy=proxy)
    return await resolver.resolve_username(username)

async def get_user_info_by_username(username: str, api_key: Optional[str] = None, proxy: Optional[str] = None) -> UserInfo:
    """
    Convenience function to get user information
    
    Args:
        username: Twitter username
        api_key: Optional API key
        proxy: Optional proxy URL
        
    Returns:
        UserInfo: User information
    """
    resolver = get_username_resolver(api_key=api_key, proxy=proxy)
    return await resolver.get_user_info(username)