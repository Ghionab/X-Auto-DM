"""
TwitterAPI.io Media Module
Handles media upload using twitterapi.io endpoints
"""

import os
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
class MediaUploadResult:
    """Result of media upload"""
    media_id: str
    status: str
    message: Optional[str] = None

class TwitterMediaClient:
    """Twitter Media client using twitterapi.io"""
    
    def __init__(self, login_cookie: str, proxy: Optional[str] = None):
        """
        Initialize Media client with authentication
        
        Args:
            login_cookie: Login cookie from authentication
            proxy: Optional proxy URL
        """
        self.core_client = get_core_client()
        self.login_cookie = login_cookie
        self.proxy = proxy
    
    def upload_media(self, file_path: str, is_long_video: bool = False) -> MediaUploadResult:
        """
        Upload media file to Twitter using twitterapi.io upload_media_v2 endpoint
        
        According to the API docs:
        POST /twitter/upload_media_v2
        - Content-Type: multipart/form-data
        - Requires: login_cookies, proxy, file
        - Optional: is_long_video
        - Returns: media_id, status, msg
        
        Args:
            file_path: Path to the media file
            is_long_video: Whether this is a long video
            
        Returns:
            MediaUploadResult: Upload result with media_id
            
        Raises:
            TwitterAPIError: If upload fails
        """
        if not file_path:
            raise TwitterAPIError("File path is required")
        
        if not os.path.exists(file_path):
            raise TwitterAPIError(f"File not found: {file_path}")
        
        # Check file size (basic validation)
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise TwitterAPIError("File is empty")
        
        # Basic file type validation
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            raise TwitterAPIError(f"Unsupported file type: {file_ext}")
        
        logger.info(f"Uploading media file: {file_path} (size: {file_size} bytes)")
        
        try:
            with open(file_path, 'rb') as file:
                files = {
                    'file': (os.path.basename(file_path), file, self._get_content_type(file_ext)),
                    'proxy': (None, self.proxy or self.core_client.config.default_proxy),
                    'login_cookies': (None, self.login_cookie),
                    'is_long_video': (None, str(is_long_video).lower())
                }
                
                response = self.core_client.make_request(
                    method="POST",
                    endpoint="/twitter/upload_media_v2",
                    files=files,
                    login_cookie=self.login_cookie,
                    proxy=self.proxy
                )
            
            result = MediaUploadResult(
                media_id=response.get("media_id", ""),
                status=response.get("status", "unknown"),
                message=response.get("msg")
            )
            
            logger.info(f"Successfully uploaded media, ID: {result.media_id}")
            return result
            
        except TwitterAPIError as e:
            logger.error(f"Failed to upload media {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading media {file_path}: {e}")
            raise TwitterAPIError(f"Media upload failed: {str(e)}")
    
    def _get_content_type(self, file_ext: str) -> str:
        """
        Get content type for file extension
        
        Args:
            file_ext: File extension (with dot)
            
        Returns:
            str: MIME type
        """
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo'
        }
        
        return content_types.get(file_ext.lower(), 'application/octet-stream')


# Convenience functions
def upload_media(login_cookie: str, file_path: str, 
                is_long_video: bool = False, 
                proxy: Optional[str] = None) -> MediaUploadResult:
    """
    Convenience function to upload media
    
    Args:
        login_cookie: Login cookie from authentication
        file_path: Path to media file
        is_long_video: Whether this is a long video
        proxy: Optional proxy URL
        
    Returns:
        MediaUploadResult: Upload result
    """
    media_client = TwitterMediaClient(login_cookie=login_cookie, proxy=proxy)
    return media_client.upload_media(file_path, is_long_video)
