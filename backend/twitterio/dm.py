"""
TwitterAPI.io Direct Message Module
Handles sending and retrieving direct messages using twitterapi.io endpoints
"""

import logging
import re
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
class DirectMessage:
    """Direct message data structure"""
    id: str
    recipient_id: str
    sender_id: str
    text: str
    time: str

@dataclass
class DMSendResult:
    """Result of sending a direct message"""
    message_id: str
    status: str
    message: Optional[str] = None

class TwitterDMClient:
    """Twitter Direct Message client using twitterapi.io"""
    
    def __init__(self, login_cookie: str, proxy: Optional[str] = None):
        """
        Initialize DM client with authentication
        
        Args:
            login_cookie: Login cookie from authentication
            proxy: Optional proxy URL
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
    
    def _validate_reply_to_message_id(self, reply_to_message_id: Optional[str]) -> bool:
        """
        Validate reply_to_message_id format
        
        Args:
            reply_to_message_id: Message ID to validate
            
        Returns:
            bool: True if valid format, False otherwise
        """
        if reply_to_message_id is None:
            return False
            
        if not reply_to_message_id or not reply_to_message_id.strip():
            return False
        
        # Twitter message IDs are typically numeric strings (Long values)
        # They should be non-empty strings containing only digits
        pattern = r'^\d+$'
        is_valid = bool(re.match(pattern, reply_to_message_id.strip()))
        
        if not is_valid:
            logger.warning(f"Invalid reply_to_message_id format: '{reply_to_message_id}' - must be numeric")
        
        return is_valid

    def send_dm(self, user_id: str, text: str, 
                media_ids: Optional[List[str]] = None,
                reply_to_message_id: Optional[str] = None) -> DMSendResult:
        """
        Send a direct message to a user using twitterapi.io send_dm_to_user endpoint
        
        According to the API docs:
        POST /twitter/send_dm_to_user
        - Requires: login_cookies, user_id, text, proxy
        - Optional: media_ids, reply_to_message_id
        - Returns: message_id, status, msg
        
        Args:
            user_id: Target user ID
            text: Message text content
            media_ids: Optional list of media IDs to attach
            reply_to_message_id: Optional message ID to reply to
            
        Returns:
            DMSendResult: Result with message ID and status
            
        Raises:
            TwitterAPIError: If sending fails
        """
        if not user_id:
            raise TwitterAPIError("User ID is required")
        
        if not text or not text.strip():
            raise TwitterAPIError("Message text is required")
        
        logger.info(f"Preparing to send DM to user: {user_id}, text length: {len(text)}")
        
        # Build request data with only required parameters
        data = {
            "user_id": user_id,
            "text": text.strip()
        }
        
        # Validate and conditionally add optional parameters
        
        # Handle media_ids parameter
        if media_ids and len(media_ids) > 0:
            # Filter out empty/None media IDs
            valid_media_ids = [mid for mid in media_ids if mid and mid.strip()]
            if valid_media_ids:
                data["media_ids"] = valid_media_ids
                logger.debug(f"Including media_ids parameter: {len(valid_media_ids)} media items")
            else:
                logger.debug("media_ids provided but all entries were empty - excluding from request")
        else:
            logger.debug("media_ids not provided or empty - excluding from request")
            
        # Handle reply_to_message_id parameter
        if reply_to_message_id:
            if self._validate_reply_to_message_id(reply_to_message_id):
                data["reply_to_message_id"] = reply_to_message_id.strip()
                logger.debug(f"Including reply_to_message_id parameter: {reply_to_message_id}")
            else:
                logger.warning(f"Invalid reply_to_message_id '{reply_to_message_id}' - excluding from request")
        else:
            logger.debug("reply_to_message_id not provided - excluding from request")
        
        # Log final request data structure for debugging
        logger.debug(f"Final request data structure: {data}")
        logger.info(f"Sending DM request with {len(data)} parameters: {list(data.keys())}")
        
        try:
            response = self.core_client.make_request(
                method="POST",
                endpoint="/twitter/send_dm_to_user",
                data=data,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            result = DMSendResult(
                message_id=response.get("message_id", ""),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully sent DM to {user_id}, message_id: {result.message_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to send DM to {user_id}: {e}")
            # Check if it's a retryable error
            if "retry" in str(e).lower():
                logger.info("DM sending may be retryable according to API documentation")
            raise
    
    def get_dm_history(self, user_id: str) -> List[DirectMessage]:
        """
        Get direct message history with a user using twitterapi.io get_dm_history_by_user_id endpoint
        
        According to the API docs:
        GET /twitter/get_dm_history_by_user_id
        - Requires: login_cookies, user_id, proxy (as query params)
        - Returns: messages array with id, recipient_id, sender_id, text, time
        
        Args:
            user_id: User ID to get message history with
            
        Returns:
            List[DirectMessage]: List of messages
            
        Raises:
            TwitterAPIError: If retrieval fails
        """
        if not user_id:
            raise TwitterAPIError("User ID is required")
        
        params = {"user_id": user_id}
        
        logger.info(f"Retrieving DM history with user: {user_id}")
        
        try:
            response = self.core_client.make_request(
                method="GET",
                endpoint="/twitter/get_dm_history_by_user_id",
                params=params,
                login_cookie=self.login_cookie,
                proxy=self.proxy
            )
            
            messages = []
            for msg_data in response.get("messages", []):
                message = DirectMessage(
                    id=msg_data["id"],
                    recipient_id=msg_data["recipient_id"], 
                    sender_id=msg_data["sender_id"],
                    text=msg_data["text"],
                    time=msg_data["time"]
                )
                messages.append(message)
            
            logger.info(f"Retrieved {len(messages)} messages from history with {user_id}")
            return messages
            
        except TwitterAPIError as e:
            logger.error(f"Failed to get DM history with {user_id}: {e}")
            raise


# Convenience functions
def send_direct_message(login_cookie: str, user_id: str, text: str,
                       media_ids: Optional[List[str]] = None,
                       reply_to_message_id: Optional[str] = None,
                       proxy: Optional[str] = None) -> DMSendResult:
    """
    Convenience function to send a direct message
    
    Args:
        login_cookie: Login cookie from authentication
        user_id: Target user ID
        text: Message text
        media_ids: Optional media IDs
        reply_to_message_id: Optional message to reply to
        proxy: Optional proxy URL
        
    Returns:
        DMSendResult: Send result
    """
    dm_client = TwitterDMClient(login_cookie=login_cookie, proxy=proxy)
    return dm_client.send_dm(user_id, text, media_ids, reply_to_message_id)

def get_message_history(login_cookie: str, user_id: str, 
                       proxy: Optional[str] = None) -> List[DirectMessage]:
    """
    Convenience function to get DM history
    
    Args:
        login_cookie: Login cookie from authentication
        user_id: User ID to get history with
        proxy: Optional proxy URL
        
    Returns:
        List[DirectMessage]: Message history
    """
    dm_client = TwitterDMClient(login_cookie=login_cookie, proxy=proxy)
    return dm_client.get_dm_history(user_id)
