"""
Target Scraper Service
Handles scraping followers and list members using TwitterAPI.io endpoints
with validation, filtering, and database storage functionality.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass

from models import db, Campaign, CampaignTarget, TwitterAccount
from services.twitterapi_client import TwitterAPIClient, TwitterUser, TwitterAPIError

logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    success: bool
    total_scraped: int
    valid_targets: int
    filtered_out: int
    error_message: Optional[str] = None
    targets: List[TwitterUser] = None

class TargetValidationError(Exception):
    """Raised when target validation fails"""
    pass

class TargetScraperService:
    """Service for scraping and managing campaign targets"""
    
    def __init__(self):
        """Initialize the target scraper service"""
        self.logger = logging.getLogger(__name__)
    
    def scrape_user_followers(self, campaign_id: int, username: str, 
                            max_followers: Optional[int] = None,
                            validate_targets: bool = True) -> ScrapingResult:
        """
        Scrape followers from a Twitter user and store as campaign targets
        
        Args:
            campaign_id: ID of the campaign to associate targets with
            username: Twitter username to scrape followers from (without @)
            max_followers: Maximum number of followers to scrape (None for all)
            validate_targets: Whether to validate and filter targets
            
        Returns:
            ScrapingResult: Result of the scraping operation
            
        Raises:
            ValueError: If campaign not found or invalid parameters
            TargetValidationError: If target validation fails
        """
        try:
            # Get campaign and validate
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign with ID {campaign_id} not found")
            
            # Get Twitter account for authentication
            twitter_account = TwitterAccount.query.get(campaign.twitter_account_id)
            if not twitter_account or not twitter_account.login_cookie:
                raise ValueError("No valid Twitter account found for campaign")
            
            self.logger.info(f"Starting follower scraping for user: {username}, campaign: {campaign_id}")
            
            # Initialize TwitterAPI client
            client = TwitterAPIClient(
                login_cookie=twitter_account.login_cookie,
                proxy=None  # Use default proxy configuration
            )
            
            # Validate that the user exists
            if not client.validate_user_exists(username):
                return ScrapingResult(
                    success=False,
                    total_scraped=0,
                    valid_targets=0,
                    filtered_out=0,
                    error_message=f"User '{username}' not found or not accessible"
                )
            
            # Scrape followers
            all_followers = []
            total_scraped = 0
            
            for page_result in client.get_user_followers(username, max_followers):
                all_followers.extend(page_result.items)
                total_scraped = page_result.total_fetched
                
                self.logger.info(f"Scraped {len(page_result.items)} followers "
                               f"(total: {total_scraped})")
                
                if not page_result.has_next_page:
                    break
            
            # Validate and filter targets if requested
            if validate_targets:
                valid_followers = self._validate_and_filter_targets(all_followers)
                filtered_out = len(all_followers) - len(valid_followers)
            else:
                valid_followers = all_followers
                filtered_out = 0
            
            # Store targets in database
            stored_count = self._store_targets(campaign_id, valid_followers)
            
            # Update campaign target count
            campaign.total_targets = stored_count
            db.session.commit()
            
            self.logger.info(f"Successfully scraped {total_scraped} followers, "
                           f"stored {stored_count} valid targets for campaign {campaign_id}")
            
            return ScrapingResult(
                success=True,
                total_scraped=total_scraped,
                valid_targets=stored_count,
                filtered_out=filtered_out,
                targets=valid_followers
            )
            
        except TwitterAPIError as e:
            self.logger.error(f"TwitterAPI error during follower scraping: {e}")
            return ScrapingResult(
                success=False,
                total_scraped=0,
                valid_targets=0,
                filtered_out=0,
                error_message=f"Twitter API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during follower scraping: {e}")
            db.session.rollback()
            return ScrapingResult(
                success=False,
                total_scraped=0,
                valid_targets=0,
                filtered_out=0,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def scrape_list_members(self, campaign_id: int, list_id: str,
                          max_members: Optional[int] = None,
                          validate_targets: bool = True) -> ScrapingResult:
        """
        Scrape members from a Twitter list and store as campaign targets
        
        Args:
            campaign_id: ID of the campaign to associate targets with
            list_id: Twitter list ID to scrape members from
            max_members: Maximum number of members to scrape (None for all)
            validate_targets: Whether to validate and filter targets
            
        Returns:
            ScrapingResult: Result of the scraping operation
            
        Raises:
            ValueError: If campaign not found or invalid parameters
            TargetValidationError: If target validation fails
        """
        try:
            # Get campaign and validate
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign with ID {campaign_id} not found")
            
            # Get Twitter account for authentication
            twitter_account = TwitterAccount.query.get(campaign.twitter_account_id)
            if not twitter_account or not twitter_account.login_cookie:
                raise ValueError("No valid Twitter account found for campaign")
            
            self.logger.info(f"Starting list member scraping for list: {list_id}, campaign: {campaign_id}")
            
            # Initialize TwitterAPI client
            client = TwitterAPIClient(
                login_cookie=twitter_account.login_cookie,
                proxy=None  # Use default proxy configuration
            )
            
            # Validate that the list exists
            if not client.validate_list_exists(list_id):
                return ScrapingResult(
                    success=False,
                    total_scraped=0,
                    valid_targets=0,
                    filtered_out=0,
                    error_message=f"List '{list_id}' not found or not accessible"
                )
            
            # Scrape list members
            all_members = []
            total_scraped = 0
            
            for page_result in client.get_list_members(list_id, max_members):
                all_members.extend(page_result.items)
                total_scraped = page_result.total_fetched
                
                self.logger.info(f"Scraped {len(page_result.items)} list members "
                               f"(total: {total_scraped})")
                
                if not page_result.has_next_page:
                    break
            
            # Validate and filter targets if requested
            if validate_targets:
                valid_members = self._validate_and_filter_targets(all_members)
                filtered_out = len(all_members) - len(valid_members)
            else:
                valid_members = all_members
                filtered_out = 0
            
            # Store targets in database
            stored_count = self._store_targets(campaign_id, valid_members)
            
            # Update campaign target count
            campaign.total_targets = stored_count
            db.session.commit()
            
            self.logger.info(f"Successfully scraped {total_scraped} list members, "
                           f"stored {stored_count} valid targets for campaign {campaign_id}")
            
            return ScrapingResult(
                success=True,
                total_scraped=total_scraped,
                valid_targets=stored_count,
                filtered_out=filtered_out,
                targets=valid_members
            )
            
        except TwitterAPIError as e:
            self.logger.error(f"TwitterAPI error during list member scraping: {e}")
            return ScrapingResult(
                success=False,
                total_scraped=0,
                valid_targets=0,
                filtered_out=0,
                error_message=f"Twitter API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during list member scraping: {e}")
            db.session.rollback()
            return ScrapingResult(
                success=False,
                total_scraped=0,
                valid_targets=0,
                filtered_out=0,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _validate_and_filter_targets(self, targets: List[TwitterUser]) -> List[TwitterUser]:
        """
        Validate and filter targets based on various criteria
        
        Args:
            targets: List of TwitterUser objects to validate
            
        Returns:
            List[TwitterUser]: Filtered list of valid targets
        """
        valid_targets = []
        
        for target in targets:
            # Check if user can receive DMs
            if not target.can_dm:
                self.logger.debug(f"Filtering out {target.username}: cannot receive DMs")
                continue
            
            # Check if account appears to be active (has recent activity indicators)
            if not self._is_active_account(target):
                self.logger.debug(f"Filtering out {target.username}: appears inactive")
                continue
            
            # Check for suspicious account patterns
            if self._is_suspicious_account(target):
                self.logger.debug(f"Filtering out {target.username}: suspicious account pattern")
                continue
            
            # Check minimum follower count (avoid very new accounts)
            if target.followers_count < 1:
                self.logger.debug(f"Filtering out {target.username}: no followers")
                continue
            
            valid_targets.append(target)
        
        self.logger.info(f"Validated {len(valid_targets)} targets out of {len(targets)} total")
        return valid_targets
    
    def _is_active_account(self, user: TwitterUser) -> bool:
        """
        Check if a Twitter account appears to be active
        
        Args:
            user: TwitterUser object to check
            
        Returns:
            bool: True if account appears active
        """
        # Check if user has a reasonable follower to following ratio
        if user.following_count > 0:
            ratio = user.followers_count / user.following_count
            # Avoid accounts with extremely high following counts relative to followers
            if ratio < 0.1 and user.following_count > 1000:
                return False
        
        # Check if user has posted content
        if user.statuses_count == 0:
            return False
        
        # Check if user has a profile description
        if not user.description or len(user.description.strip()) == 0:
            return False
        
        return True
    
    def _is_suspicious_account(self, user: TwitterUser) -> bool:
        """
        Check if a Twitter account shows suspicious patterns
        
        Args:
            user: TwitterUser object to check
            
        Returns:
            bool: True if account appears suspicious
        """
        # Check for default profile picture (basic heuristic)
        if not user.profile_picture or 'default_profile' in user.profile_picture:
            return True
        
        # Check for very high following count with low followers (potential spam)
        if user.following_count > 5000 and user.followers_count < 100:
            return True
        
        # Check for suspicious username patterns (numbers only, etc.)
        username_lower = user.username.lower()
        if username_lower.isdigit() or len(username_lower) < 3:
            return True
        
        # Check for empty or very short display name
        if not user.name or len(user.name.strip()) < 2:
            return True
        
        return False
    
    def _store_targets(self, campaign_id: int, targets: List[TwitterUser]) -> int:
        """
        Store scraped targets in the database
        
        Args:
            campaign_id: ID of the campaign to associate targets with
            targets: List of TwitterUser objects to store
            
        Returns:
            int: Number of targets successfully stored
            
        Raises:
            Exception: If database operation fails
        """
        stored_count = 0
        
        try:
            for target in targets:
                # Check if target already exists for this campaign
                existing_target = CampaignTarget.query.filter_by(
                    campaign_id=campaign_id,
                    twitter_user_id=target.id
                ).first()
                
                if existing_target:
                    self.logger.debug(f"Target {target.username} already exists for campaign {campaign_id}")
                    continue
                
                # Create new campaign target
                campaign_target = CampaignTarget(
                    campaign_id=campaign_id,
                    twitter_user_id=target.id,
                    username=target.username,
                    display_name=target.name,
                    bio=target.description,
                    profile_picture=target.profile_picture,
                    follower_count=target.followers_count,
                    following_count=target.following_count,
                    is_verified=target.is_verified or target.is_blue_verified,
                    can_dm=target.can_dm,
                    status='pending'
                )
                
                db.session.add(campaign_target)
                stored_count += 1
            
            # Commit all targets at once
            db.session.commit()
            self.logger.info(f"Successfully stored {stored_count} targets for campaign {campaign_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing targets: {e}")
            db.session.rollback()
            raise
        
        return stored_count
    
    def get_campaign_targets(self, campaign_id: int, status: Optional[str] = None,
                           limit: Optional[int] = None, offset: int = 0) -> List[CampaignTarget]:
        """
        Retrieve campaign targets with optional filtering
        
        Args:
            campaign_id: ID of the campaign
            status: Optional status filter ('pending', 'sent', 'failed', 'replied')
            limit: Maximum number of targets to return
            offset: Number of targets to skip
            
        Returns:
            List[CampaignTarget]: List of campaign targets
        """
        query = CampaignTarget.query.filter_by(campaign_id=campaign_id)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_target_statistics(self, campaign_id: int) -> Dict[str, Any]:
        """
        Get statistics about campaign targets
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            Dict[str, Any]: Statistics about the targets
        """
        targets = CampaignTarget.query.filter_by(campaign_id=campaign_id).all()
        
        if not targets:
            return {
                'total_targets': 0,
                'status_breakdown': {},
                'avg_follower_count': 0,
                'verified_count': 0,
                'can_dm_count': 0
            }
        
        # Calculate statistics
        status_counts = {}
        total_followers = 0
        verified_count = 0
        can_dm_count = 0
        
        for target in targets:
            # Status breakdown
            status = target.status or 'pending'
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Follower statistics
            total_followers += target.follower_count or 0
            
            # Verification and DM capability
            if target.is_verified:
                verified_count += 1
            if target.can_dm:
                can_dm_count += 1
        
        avg_follower_count = total_followers / len(targets) if targets else 0
        
        return {
            'total_targets': len(targets),
            'status_breakdown': status_counts,
            'avg_follower_count': round(avg_follower_count, 2),
            'verified_count': verified_count,
            'can_dm_count': can_dm_count,
            'verified_percentage': round((verified_count / len(targets)) * 100, 2),
            'can_dm_percentage': round((can_dm_count / len(targets)) * 100, 2)
        }
    
    def clear_campaign_targets(self, campaign_id: int) -> int:
        """
        Clear all targets for a campaign
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            int: Number of targets deleted
        """
        try:
            deleted_count = CampaignTarget.query.filter_by(campaign_id=campaign_id).delete()
            
            # Update campaign target count
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                campaign.total_targets = 0
            
            db.session.commit()
            
            self.logger.info(f"Cleared {deleted_count} targets for campaign {campaign_id}")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error clearing targets for campaign {campaign_id}: {e}")
            db.session.rollback()
            raise

# Factory function for creating service instances
def create_target_scraper_service() -> TargetScraperService:
    """
    Factory function to create a TargetScraperService instance
    
    Returns:
        TargetScraperService: Configured service instance
    """
    return TargetScraperService()