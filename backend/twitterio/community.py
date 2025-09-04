"""
TwitterAPI.io Community Module
Handles community operations using twitterapi.io endpoints
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
class CommunityResult:
    """Result of community creation"""
    community_id: str
    status: str
    message: Optional[str] = None

@dataclass
class CommunityActionResult:
    """Result of community actions (join, leave, delete)"""
    community_id: Optional[str] = None
    community_name: Optional[str] = None
    status: str = "unknown"
    message: Optional[str] = None

class TwitterCommunityClient:
    """Twitter Community client using twitterapi.io"""
    
    def __init__(self, login_cookie: str, proxy: Optional[str] = None):
        """
        Initialize Community client with authentication
        
        Args:
            login_cookie: Login cookie from authentication
            proxy: Optional proxy URL
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
    
    def create_community(self, name: str, description: str) -> CommunityResult:
        """
        Create a new community using twitterapi.io create_community_v2 endpoint
        
        According to the API docs:
        POST /twitter/create_community_v2
        - Requires: login_cookie, name, description, proxy
        - Returns: community_id, status, msg
        
        Args:
            name: Community name
            description: Community description
            
        Returns:
            CommunityResult: Creation result with community_id
            
        Raises:
            TwitterAPIError: If creation fails
        """
        if not name or not name.strip():
            raise TwitterAPIError("Community name is required")
        
        if not description or not description.strip():
            raise TwitterAPIError("Community description is required")
        
        data = {
            "name": name.strip(),
            "description": description.strip()
        }
        
        logger.info(f"Creating community: {name}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/create_community_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = CommunityResult(
                community_id=response.get("community_id", ""),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully created community: {name}, ID: {result.community_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to create community {name}: {e}")
            raise
    
    def delete_community(self, community_id: str, community_name: str) -> CommunityActionResult:
        """
        Delete a community using twitterapi.io delete_community_v2 endpoint
        
        According to the API docs:
        POST /twitter/delete_community_v2
        - Requires: login_cookie, community_id, community_name, proxy
        - Returns: status, msg
        
        Args:
            community_id: ID of community to delete
            community_name: Name of community to delete
            
        Returns:
            CommunityActionResult: Deletion result
            
        Raises:
            TwitterAPIError: If deletion fails
        """
        if not community_id:
            raise TwitterAPIError("Community ID is required")
        
        if not community_name:
            raise TwitterAPIError("Community name is required")
        
        data = {
            "community_id": community_id,
            "community_name": community_name
        }
        
        logger.info(f"Deleting community: {community_name} ({community_id})")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/delete_community_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = CommunityActionResult(
                community_id=community_id,
                community_name=community_name,
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully deleted community: {community_name}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to delete community {community_name}: {e}")
            raise
    
    def join_community(self, community_id: str) -> CommunityActionResult:
        """
        Join a community using twitterapi.io join_community_v2 endpoint
        
        According to the API docs:
        POST /twitter/join_community_v2
        - Requires: login_cookie, community_id, proxy
        - Returns: community_id, community_name, status, msg
        
        Args:
            community_id: ID of community to join
            
        Returns:
            CommunityActionResult: Join result
            
        Raises:
            TwitterAPIError: If join fails
        """
        if not community_id:
            raise TwitterAPIError("Community ID is required")
        
        data = {"community_id": community_id}
        
        logger.info(f"Joining community: {community_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/join_community_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = CommunityActionResult(
                community_id=response.get("community_id", community_id),
                community_name=response.get("community_name"),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully joined community: {result.community_name} ({community_id})")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to join community {community_id}: {e}")
            raise
    
    def leave_community(self, community_id: str) -> CommunityActionResult:
        """
        Leave a community using twitterapi.io leave_community_v2 endpoint
        
        According to the API docs:
        POST /twitter/leave_community_v2
        - Requires: login_cookie, community_id, proxy
        - Returns: community_id, community_name, status, msg
        
        Args:
            community_id: ID of community to leave
            
        Returns:
            CommunityActionResult: Leave result
            
        Raises:
            TwitterAPIError: If leave fails
        """
        if not community_id:
            raise TwitterAPIError("Community ID is required")
        
        data = {"community_id": community_id}
        
        logger.info(f"Leaving community: {community_id}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/leave_community_v2",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = CommunityActionResult(
                community_id=response.get("community_id", community_id),
                community_name=response.get("community_name"),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully left community: {result.community_name} ({community_id})")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to leave community {community_id}: {e}")
            raise


# Convenience functions
def create_community(login_cookie: str, name: str, description: str,
                    proxy: Optional[str] = None) -> CommunityResult:
    """
    Convenience function to create a community
    
    Args:
        login_cookie: Login cookie from authentication
        name: Community name
        description: Community description
        proxy: Optional proxy URL
        
    Returns:
        CommunityResult: Creation result
    """
    community_client = TwitterCommunityClient(login_cookie=login_cookie, proxy=proxy)
    return community_client.create_community(name, description)

def delete_community(login_cookie: str, community_id: str, community_name: str,
                    proxy: Optional[str] = None) -> CommunityActionResult:
    """
    Convenience function to delete a community
    
    Args:
        login_cookie: Login cookie from authentication
        community_id: Community ID
        community_name: Community name
        proxy: Optional proxy URL
        
    Returns:
        CommunityActionResult: Deletion result
    """
    community_client = TwitterCommunityClient(login_cookie=login_cookie, proxy=proxy)
    return community_client.delete_community(community_id, community_name)

def join_community(login_cookie: str, community_id: str,
                  proxy: Optional[str] = None) -> CommunityActionResult:
    """
    Convenience function to join a community
    
    Args:
        login_cookie: Login cookie from authentication
        community_id: Community ID
        proxy: Optional proxy URL
        
    Returns:
        CommunityActionResult: Join result
    """
    community_client = TwitterCommunityClient(login_cookie=login_cookie, proxy=proxy)
    return community_client.join_community(community_id)

def leave_community(login_cookie: str, community_id: str,
                   proxy: Optional[str] = None) -> CommunityActionResult:
    """
    Convenience function to leave a community
    
    Args:
        login_cookie: Login cookie from authentication
        community_id: Community ID
        proxy: Optional proxy URL
        
    Returns:
        CommunityActionResult: Leave result
    """
    community_client = TwitterCommunityClient(login_cookie=login_cookie, proxy=proxy)
    return community_client.leave_community(community_id)
