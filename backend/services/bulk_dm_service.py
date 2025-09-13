"""
Bulk DM Service for Campaign Management
Handles batch DM operations with rate limiting, personalization, and progress tracking
"""

import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from threading import Lock
import json

try:
    from ..models import db, Campaign, CampaignTarget, CampaignMessage, TwitterAccount
    from ..twitterio.dm import TwitterDMClient, DMSendResult, TwitterAPIError
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import db, Campaign, CampaignTarget, CampaignMessage, TwitterAccount
    from twitterio.dm import TwitterDMClient, DMSendResult, TwitterAPIError

logger = logging.getLogger(__name__)

@dataclass
class BulkDMProgress:
    """Progress tracking for bulk DM operations"""
    campaign_id: int
    total_targets: int
    processed: int
    sent: int
    failed: int
    current_target: Optional[str] = None
    status: str = "running"
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

@dataclass
class BulkDMResult:
    """Result of bulk DM operation"""
    campaign_id: int
    total_targets: int
    sent_count: int
    failed_count: int
    errors: List[Dict[str, Any]]
    duration_seconds: float
    status: str

class RateLimiter:
    """Rate limiter for DM sending operations"""
    
    def __init__(self, daily_limit: int = 50, delay_min: int = 30, delay_max: int = 120):
        """
        Initialize rate limiter
        
        Args:
            daily_limit: Maximum DMs per day
            delay_min: Minimum delay between DMs in seconds
            delay_max: Maximum delay between DMs in seconds
        """
        self.daily_limit = daily_limit
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.sent_today = 0
        self.last_sent_time = None
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self._lock = Lock()
    
    def can_send(self) -> bool:
        """Check if we can send a DM now"""
        with self._lock:
            # Reset daily counter if it's a new day
            if datetime.now() >= self.daily_reset_time:
                self.sent_today = 0
                self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            # Check daily limit (allow sending up to the limit, not after reaching it)
            if self.sent_today >= self.daily_limit:
                return False
            
            # Check time delay
            if self.last_sent_time:
                time_since_last = (datetime.now() - self.last_sent_time).total_seconds()
                if time_since_last < self.delay_min:
                    return False
            
            return True
    
    def wait_time(self) -> int:
        """Get seconds to wait before next send"""
        with self._lock:
            # Check if we need to wait for daily reset
            if self.sent_today >= self.daily_limit:
                return int((self.daily_reset_time - datetime.now()).total_seconds())
            
            # Check time delay
            if self.last_sent_time:
                time_since_last = (datetime.now() - self.last_sent_time).total_seconds()
                if time_since_last < self.delay_min:
                    return int(self.delay_min - time_since_last)
            
            return 0
    
    def record_send(self):
        """Record that a DM was sent"""
        with self._lock:
            self.sent_today += 1
            self.last_sent_time = datetime.now()

class MessagePersonalizer:
    """Handles message personalization using target data"""
    
    @staticmethod
    def personalize_message(template: str, target: CampaignTarget) -> str:
        """
        Personalize message template with target data
        
        Args:
            template: Message template with placeholders
            target: Target user data
            
        Returns:
            Personalized message
        """
        if not template:
            return ""
        
        # Available personalization variables
        variables = {
            '{name}': target.display_name or target.username,
            '{username}': target.username,
            '{display_name}': target.display_name or target.username,
            '{follower_count}': str(target.follower_count) if target.follower_count else "0",
            '{following_count}': str(target.following_count) if target.following_count else "0"
        }
        
        # Replace variables in template
        personalized = template
        for placeholder, value in variables.items():
            personalized = personalized.replace(placeholder, value)
        
        return personalized
    
    @staticmethod
    def validate_template(template: str) -> Tuple[bool, List[str]]:
        """
        Validate message template for supported variables
        
        Args:
            template: Message template to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not template or not template.strip():
            return False, ["Template cannot be empty"]
        
        errors = []
        
        # Check for unsupported variables
        supported_vars = ['{name}', '{username}', '{display_name}', '{follower_count}', '{following_count}']
        
        # Find all variables in template
        variables = re.findall(r'\{[^}]+\}', template)
        
        for var in variables:
            if var not in supported_vars:
                errors.append(f"Unsupported variable: {var}")
        
        # Check message length (Twitter DM limit is 10,000 characters)
        if len(template) > 9000:  # Leave room for personalization
            errors.append("Template too long (max 9000 characters)")
        
        return len(errors) == 0, errors

class BulkDMService:
    """Service for sending bulk DMs to campaign targets"""
    
    def __init__(self):
        self.progress_cache = {}  # Store progress for active campaigns
        self._lock = Lock()
    
    def start_campaign_sending(self, campaign_id: int) -> BulkDMResult:
        """
        Start sending DMs for a campaign
        
        Args:
            campaign_id: Campaign ID to process
            
        Returns:
            BulkDMResult with operation results
            
        Raises:
            ValueError: If campaign not found or invalid
            TwitterAPIError: If DM sending fails
        """
        logger.info(f"Starting bulk DM sending for campaign {campaign_id}")
        
        # Get campaign and validate
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.status not in ['draft', 'paused']:
            raise ValueError(f"Campaign {campaign_id} is not in a sendable state (status: {campaign.status})")
        
        # Get Twitter account
        twitter_account = campaign.twitter_account
        if not twitter_account or not twitter_account.login_cookie:
            raise ValueError(f"No valid Twitter account found for campaign {campaign_id}")
        
        # Validate message template
        is_valid, errors = MessagePersonalizer.validate_template(campaign.message_template)
        if not is_valid:
            raise ValueError(f"Invalid message template: {', '.join(errors)}")
        
        # Get targets that haven't been sent to yet
        targets = CampaignTarget.query.filter_by(
            campaign_id=campaign_id,
            status='pending'
        ).filter(
            CampaignTarget.can_dm == True
        ).all()
        
        if not targets:
            logger.warning(f"No pending targets found for campaign {campaign_id}")
            return BulkDMResult(
                campaign_id=campaign_id,
                total_targets=0,
                sent_count=0,
                failed_count=0,
                errors=[],
                duration_seconds=0.0,
                status="completed"
            )
        
        # Update campaign status
        campaign.status = 'active'
        campaign.started_at = datetime.utcnow()
        db.session.commit()
        
        # Initialize progress tracking
        progress = BulkDMProgress(
            campaign_id=campaign_id,
            total_targets=len(targets),
            processed=0,
            sent=0,
            failed=0,
            started_at=datetime.now(),
            status="running"
        )
        
        with self._lock:
            self.progress_cache[campaign_id] = progress
        
        # Initialize rate limiter
        rate_limiter = RateLimiter(
            daily_limit=campaign.daily_limit,
            delay_min=campaign.delay_min,
            delay_max=campaign.delay_max
        )
        
        # Send DMs
        start_time = time.time()
        result = self._send_dm_batch(
            targets=targets,
            campaign=campaign,
            twitter_account=twitter_account,
            rate_limiter=rate_limiter,
            progress=progress
        )
        
        duration = time.time() - start_time
        
        # Update campaign status
        if result.failed_count == 0:
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
        elif result.sent_count == 0:
            campaign.status = 'failed'
        else:
            campaign.status = 'completed'  # Partial success still counts as completed
            campaign.completed_at = datetime.utcnow()
        
        campaign.messages_sent = result.sent_count
        db.session.commit()
        
        # Clean up progress cache
        with self._lock:
            if campaign_id in self.progress_cache:
                del self.progress_cache[campaign_id]
        
        result.duration_seconds = duration
        logger.info(f"Completed bulk DM sending for campaign {campaign_id}: {result.sent_count} sent, {result.failed_count} failed")
        
        return result
    
    def _send_dm_batch(self, targets: List[CampaignTarget], campaign: Campaign, 
                      twitter_account: TwitterAccount, rate_limiter: RateLimiter,
                      progress: BulkDMProgress) -> BulkDMResult:
        """
        Send DMs to a batch of targets
        
        Args:
            targets: List of targets to send to
            campaign: Campaign object
            twitter_account: Twitter account to send from
            rate_limiter: Rate limiter instance
            progress: Progress tracking object
            
        Returns:
            BulkDMResult with batch results
        """
        dm_client = TwitterDMClient(
            login_cookie=twitter_account.login_cookie,
            proxy=None  # Add proxy support if needed
        )
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        for i, target in enumerate(targets):
            # Check if campaign was paused
            current_campaign = Campaign.query.get(campaign.id)
            if current_campaign.status == 'paused':
                logger.info(f"Campaign {campaign.id} was paused, stopping DM sending")
                break
            
            # Update progress
            progress.processed = i + 1
            progress.current_target = target.username
            
            # Wait for rate limiting
            while not rate_limiter.can_send():
                wait_time = rate_limiter.wait_time()
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time} seconds")
                    time.sleep(min(wait_time, 60))  # Sleep in chunks of max 60 seconds
            
            try:
                # Personalize message
                personalized_message = MessagePersonalizer.personalize_message(
                    campaign.message_template, target
                )
                
                # Send DM
                result = dm_client.send_dm(
                    user_id=target.twitter_user_id,
                    text=personalized_message
                )
                
                # Record successful send
                rate_limiter.record_send()
                sent_count += 1
                progress.sent += 1
                
                # Update target status
                target.status = 'sent'
                target.message_sent_at = datetime.utcnow()
                
                # Create campaign message record
                campaign_message = CampaignMessage(
                    campaign_id=campaign.id,
                    target_id=target.id,
                    message_content=personalized_message,
                    twitter_message_id=result.message_id,
                    status='sent',
                    sent_at=datetime.utcnow()
                )
                db.session.add(campaign_message)
                
                logger.info(f"Successfully sent DM to {target.username} (message_id: {result.message_id})")
                
            except TwitterAPIError as e:
                # Handle DM sending error
                failed_count += 1
                progress.failed += 1
                
                error_info = {
                    'target_id': target.id,
                    'username': target.username,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                errors.append(error_info)
                
                # Update target status
                target.status = 'failed'
                target.error_message = str(e)
                
                logger.error(f"Failed to send DM to {target.username}: {e}")
                
                # Check if it's a retryable error
                if self._is_retryable_error(e):
                    logger.info(f"Error for {target.username} may be retryable")
                    # Could implement retry logic here
            
            except Exception as e:
                # Handle unexpected errors
                failed_count += 1
                progress.failed += 1
                
                error_info = {
                    'target_id': target.id,
                    'username': target.username,
                    'error': f"Unexpected error: {str(e)}",
                    'timestamp': datetime.utcnow().isoformat()
                }
                errors.append(error_info)
                
                target.status = 'failed'
                target.error_message = f"Unexpected error: {str(e)}"
                
                logger.error(f"Unexpected error sending DM to {target.username}: {e}")
            
            # Commit changes for this target
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to commit database changes for target {target.username}: {e}")
                db.session.rollback()
        
        progress.status = "completed"
        
        return BulkDMResult(
            campaign_id=campaign.id,
            total_targets=len(targets),
            sent_count=sent_count,
            failed_count=failed_count,
            errors=errors,
            duration_seconds=0.0,  # Will be set by caller
            status="completed" if failed_count == 0 else "partial"
        )
    
    def _is_retryable_error(self, error: TwitterAPIError) -> bool:
        """
        Determine if an error is retryable
        
        Args:
            error: TwitterAPIError to check
            
        Returns:
            True if error is retryable
        """
        error_str = str(error).lower()
        
        # Retryable errors
        retryable_indicators = [
            'rate limit',
            'timeout',
            'network',
            'connection',
            'temporary',
            'retry'
        ]
        
        # Non-retryable errors
        non_retryable_indicators = [
            'unauthorized',
            'forbidden',
            'not found',
            'blocked',
            'suspended',
            'invalid'
        ]
        
        # Check for non-retryable first
        for indicator in non_retryable_indicators:
            if indicator in error_str:
                return False
        
        # Check for retryable
        for indicator in retryable_indicators:
            if indicator in error_str:
                return True
        
        # Default to non-retryable for unknown errors
        return False
    
    def pause_campaign_sending(self, campaign_id: int) -> bool:
        """
        Pause an active campaign
        
        Args:
            campaign_id: Campaign ID to pause
            
        Returns:
            True if successfully paused
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return False
        
        if campaign.status == 'active':
            campaign.status = 'paused'
            db.session.commit()
            logger.info(f"Paused campaign {campaign_id}")
            return True
        
        return False
    
    def resume_campaign_sending(self, campaign_id: int) -> BulkDMResult:
        """
        Resume a paused campaign
        
        Args:
            campaign_id: Campaign ID to resume
            
        Returns:
            BulkDMResult with operation results
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.status != 'paused':
            raise ValueError(f"Campaign {campaign_id} is not paused (status: {campaign.status})")
        
        logger.info(f"Resuming campaign {campaign_id}")
        return self.start_campaign_sending(campaign_id)
    
    def get_campaign_progress(self, campaign_id: int) -> Optional[BulkDMProgress]:
        """
        Get current progress for a campaign
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            BulkDMProgress if campaign is active, None otherwise
        """
        with self._lock:
            return self.progress_cache.get(campaign_id)
    
    def retry_failed_targets(self, campaign_id: int, target_ids: Optional[List[int]] = None) -> BulkDMResult:
        """
        Retry sending DMs to failed targets
        
        Args:
            campaign_id: Campaign ID
            target_ids: Optional list of specific target IDs to retry
            
        Returns:
            BulkDMResult with retry results
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Get failed targets
        query = CampaignTarget.query.filter_by(
            campaign_id=campaign_id,
            status='failed'
        )
        
        if target_ids:
            query = query.filter(CampaignTarget.id.in_(target_ids))
        
        failed_targets = query.all()
        
        if not failed_targets:
            logger.info(f"No failed targets found for campaign {campaign_id}")
            return BulkDMResult(
                campaign_id=campaign_id,
                total_targets=0,
                sent_count=0,
                failed_count=0,
                errors=[],
                duration_seconds=0.0,
                status="completed"
            )
        
        # Reset target status to pending for retry
        for target in failed_targets:
            target.status = 'pending'
            target.error_message = None
        
        db.session.commit()
        
        logger.info(f"Retrying {len(failed_targets)} failed targets for campaign {campaign_id}")
        
        # Use the regular sending process
        return self.start_campaign_sending(campaign_id)


# Convenience functions
def send_bulk_dms(campaign_id: int) -> BulkDMResult:
    """
    Convenience function to send bulk DMs for a campaign
    
    Args:
        campaign_id: Campaign ID to process
        
    Returns:
        BulkDMResult with operation results
    """
    service = BulkDMService()
    return service.start_campaign_sending(campaign_id)

def get_sending_progress(campaign_id: int) -> Optional[BulkDMProgress]:
    """
    Convenience function to get campaign sending progress
    
    Args:
        campaign_id: Campaign ID
        
    Returns:
        BulkDMProgress if available
    """
    service = BulkDMService()
    return service.get_campaign_progress(campaign_id)