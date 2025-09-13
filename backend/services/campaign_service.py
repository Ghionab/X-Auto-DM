"""
Campaign Service
Core business logic for campaign management including CRUD operations,
status management, validation, and integration with target scraping.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json

from models import db, Campaign, CampaignTarget, CampaignMessage, TwitterAccount, User
from services.target_scraper_service import TargetScraperService, ScrapingResult

logger = logging.getLogger(__name__)

class CampaignValidationError(Exception):
    """Raised when campaign validation fails"""
    pass

class CampaignNotFoundError(Exception):
    """Raised when campaign is not found"""
    pass

class CampaignPermissionError(Exception):
    """Raised when user doesn't have permission to access campaign"""
    pass

class CampaignService:
    """Service for managing DM campaigns"""
    
    def __init__(self):
        """Initialize the campaign service"""
        self.logger = logging.getLogger(__name__)
        self.target_scraper = TargetScraperService()
    
    def create_campaign(self, user_id: int, campaign_data: Dict[str, Any]) -> Campaign:
        """
        Create a new campaign with validation
        
        Args:
            user_id: ID of the user creating the campaign
            campaign_data: Dictionary containing campaign configuration
            
        Returns:
            Campaign: Created campaign object
            
        Raises:
            CampaignValidationError: If validation fails
            ValueError: If required data is missing
        """
        try:
            # Validate required fields
            required_fields = ['name', 'message_template', 'target_type', 'target_identifier', 'twitter_account_id']
            for field in required_fields:
                if field not in campaign_data or not campaign_data[field]:
                    raise CampaignValidationError(f"Missing required field: {field}")
            
            # Validate user exists
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Validate Twitter account belongs to user
            twitter_account = TwitterAccount.query.filter_by(
                id=campaign_data['twitter_account_id'],
                user_id=user_id
            ).first()
            if not twitter_account:
                raise CampaignValidationError("Invalid Twitter account or account doesn't belong to user")
            
            # Validate Twitter account has login cookie
            if not twitter_account.login_cookie:
                raise CampaignValidationError("Twitter account is not properly authenticated")
            
            # Validate target type
            valid_target_types = ['user_followers', 'list_members', 'manual_list', 'csv_upload']
            if campaign_data['target_type'] not in valid_target_types:
                raise CampaignValidationError(f"Invalid target_type. Must be one of: {valid_target_types}")
            
            # Validate message template
            message_template = campaign_data['message_template'].strip()
            if len(message_template) < 10:
                raise CampaignValidationError("Message template must be at least 10 characters long")
            if len(message_template) > 10000:
                raise CampaignValidationError("Message template must be less than 10,000 characters")
            
            # Validate daily limit
            daily_limit = campaign_data.get('daily_limit', 50)
            if not isinstance(daily_limit, int) or daily_limit < 1 or daily_limit > 1000:
                raise CampaignValidationError("Daily limit must be between 1 and 1000")
            
            # Validate delay settings
            delay_min = campaign_data.get('delay_min', 30)
            delay_max = campaign_data.get('delay_max', 120)
            if not isinstance(delay_min, int) or delay_min < 1:
                raise CampaignValidationError("Minimum delay must be at least 1 minute")
            if not isinstance(delay_max, int) or delay_max < delay_min:
                raise CampaignValidationError("Maximum delay must be greater than or equal to minimum delay")
            
            # Process AI rules if provided
            ai_rules = campaign_data.get('ai_rules', {})
            if ai_rules and not isinstance(ai_rules, dict):
                raise CampaignValidationError("AI rules must be a dictionary")
            
            # Create campaign
            campaign = Campaign(
                user_id=user_id,
                twitter_account_id=campaign_data['twitter_account_id'],
                name=campaign_data['name'].strip(),
                description=campaign_data.get('description', '').strip(),
                target_type=campaign_data['target_type'],
                target_identifier=campaign_data['target_identifier'].strip(),
                message_template=message_template,
                personalization_enabled=campaign_data.get('personalization_enabled', True),
                ai_rules=json.dumps(ai_rules) if ai_rules else None,
                daily_limit=daily_limit,
                delay_min=delay_min,
                delay_max=delay_max,
                status='draft'
            )
            
            db.session.add(campaign)
            db.session.commit()
            
            self.logger.info(f"Created campaign '{campaign.name}' (ID: {campaign.id}) for user {user_id}")
            return campaign
            
        except CampaignValidationError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating campaign: {e}")
            raise CampaignValidationError(f"Failed to create campaign: {str(e)}")
    
    def get_campaigns(self, user_id: int, status: Optional[str] = None, 
                     limit: Optional[int] = None, offset: int = 0) -> List[Campaign]:
        """
        Retrieve campaigns for a user with optional filtering
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            limit: Maximum number of campaigns to return
            offset: Number of campaigns to skip
            
        Returns:
            List[Campaign]: List of campaigns
        """
        query = Campaign.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(Campaign.created_at.desc())
        query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        campaigns = query.all()
        self.logger.debug(f"Retrieved {len(campaigns)} campaigns for user {user_id}")
        return campaigns
    
    def get_campaign(self, campaign_id: int, user_id: int) -> Campaign:
        """
        Get a specific campaign by ID
        
        Args:
            campaign_id: ID of the campaign
            user_id: ID of the user (for permission check)
            
        Returns:
            Campaign: Campaign object
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise CampaignNotFoundError(f"Campaign with ID {campaign_id} not found")
        
        if campaign.user_id != user_id:
            raise CampaignPermissionError("You don't have permission to access this campaign")
        
        return campaign
    
    def update_campaign(self, campaign_id: int, user_id: int, 
                       update_data: Dict[str, Any]) -> Campaign:
        """
        Update an existing campaign
        
        Args:
            campaign_id: ID of the campaign to update
            user_id: ID of the user (for permission check)
            update_data: Dictionary containing fields to update
            
        Returns:
            Campaign: Updated campaign object
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
            CampaignValidationError: If validation fails
        """
        try:
            campaign = self.get_campaign(campaign_id, user_id)
            
            # Check if campaign can be updated
            if campaign.status in ['active', 'completed']:
                # Only allow limited updates for active/completed campaigns
                allowed_fields = ['name', 'description', 'daily_limit']
                for field in update_data:
                    if field not in allowed_fields:
                        raise CampaignValidationError(
                            f"Cannot update '{field}' for {campaign.status} campaign"
                        )
            
            # Update allowed fields with validation
            if 'name' in update_data:
                name = update_data['name'].strip()
                if not name:
                    raise CampaignValidationError("Campaign name cannot be empty")
                campaign.name = name
            
            if 'description' in update_data:
                campaign.description = update_data['description'].strip()
            
            if 'message_template' in update_data and campaign.status == 'draft':
                message_template = update_data['message_template'].strip()
                if len(message_template) < 10:
                    raise CampaignValidationError("Message template must be at least 10 characters long")
                if len(message_template) > 10000:
                    raise CampaignValidationError("Message template must be less than 10,000 characters")
                campaign.message_template = message_template
            
            if 'daily_limit' in update_data:
                daily_limit = update_data['daily_limit']
                if not isinstance(daily_limit, int) or daily_limit < 1 or daily_limit > 1000:
                    raise CampaignValidationError("Daily limit must be between 1 and 1000")
                campaign.daily_limit = daily_limit
            
            if 'delay_min' in update_data and campaign.status == 'draft':
                delay_min = update_data['delay_min']
                if not isinstance(delay_min, int) or delay_min < 1:
                    raise CampaignValidationError("Minimum delay must be at least 1 minute")
                campaign.delay_min = delay_min
            
            if 'delay_max' in update_data and campaign.status == 'draft':
                delay_max = update_data['delay_max']
                if not isinstance(delay_max, int) or delay_max < campaign.delay_min:
                    raise CampaignValidationError("Maximum delay must be greater than or equal to minimum delay")
                campaign.delay_max = delay_max
            
            if 'ai_rules' in update_data and campaign.status == 'draft':
                ai_rules = update_data['ai_rules']
                if ai_rules and not isinstance(ai_rules, dict):
                    raise CampaignValidationError("AI rules must be a dictionary")
                campaign.ai_rules = json.dumps(ai_rules) if ai_rules else None
            
            if 'personalization_enabled' in update_data and campaign.status == 'draft':
                campaign.personalization_enabled = bool(update_data['personalization_enabled'])
            
            campaign.updated_at = datetime.utcnow()
            db.session.commit()
            
            self.logger.info(f"Updated campaign {campaign_id} for user {user_id}")
            return campaign
            
        except (CampaignNotFoundError, CampaignPermissionError, CampaignValidationError):
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error updating campaign {campaign_id}: {e}")
            raise CampaignValidationError(f"Failed to update campaign: {str(e)}")
    
    def update_campaign_status(self, campaign_id: int, user_id: int, 
                              new_status: str) -> Campaign:
        """
        Update campaign status with validation
        
        Args:
            campaign_id: ID of the campaign
            user_id: ID of the user (for permission check)
            new_status: New status to set
            
        Returns:
            Campaign: Updated campaign object
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
            CampaignValidationError: If status transition is invalid
        """
        try:
            campaign = self.get_campaign(campaign_id, user_id)
            
            # Validate status transition
            valid_statuses = ['draft', 'active', 'paused', 'completed', 'failed']
            if new_status not in valid_statuses:
                raise CampaignValidationError(f"Invalid status: {new_status}")
            
            # Check valid status transitions
            current_status = campaign.status
            valid_transitions = {
                'draft': ['active', 'failed'],
                'active': ['paused', 'completed', 'failed'],
                'paused': ['active', 'completed', 'failed'],
                'completed': [],  # Terminal state
                'failed': ['draft']  # Allow retry from failed state
            }
            
            if new_status not in valid_transitions.get(current_status, []):
                raise CampaignValidationError(
                    f"Cannot transition from '{current_status}' to '{new_status}'"
                )
            
            # Additional validation for specific transitions
            if new_status == 'active':
                # Ensure campaign has targets before activating
                if campaign.total_targets == 0:
                    raise CampaignValidationError("Cannot activate campaign without targets")
                
                # Set started_at timestamp
                if not campaign.started_at:
                    campaign.started_at = datetime.utcnow()
            
            elif new_status == 'completed':
                # Set completed_at timestamp
                campaign.completed_at = datetime.utcnow()
            
            # Update status
            campaign.status = new_status
            campaign.updated_at = datetime.utcnow()
            db.session.commit()
            
            self.logger.info(f"Updated campaign {campaign_id} status from '{current_status}' to '{new_status}'")
            return campaign
            
        except (CampaignNotFoundError, CampaignPermissionError, CampaignValidationError):
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error updating campaign status: {e}")
            raise CampaignValidationError(f"Failed to update campaign status: {str(e)}")
    
    def delete_campaign(self, campaign_id: int, user_id: int) -> bool:
        """
        Delete a campaign and all associated data
        
        Args:
            campaign_id: ID of the campaign to delete
            user_id: ID of the user (for permission check)
            
        Returns:
            bool: True if successfully deleted
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
            CampaignValidationError: If campaign cannot be deleted
        """
        try:
            campaign = self.get_campaign(campaign_id, user_id)
            
            # Check if campaign can be deleted
            if campaign.status == 'active':
                raise CampaignValidationError("Cannot delete active campaign. Pause it first.")
            
            # Delete associated data (handled by cascade relationships)
            # This will delete CampaignTargets, CampaignMessages, DirectMessages, etc.
            db.session.delete(campaign)
            db.session.commit()
            
            self.logger.info(f"Deleted campaign {campaign_id} and all associated data")
            return True
            
        except (CampaignNotFoundError, CampaignPermissionError, CampaignValidationError):
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error deleting campaign {campaign_id}: {e}")
            raise CampaignValidationError(f"Failed to delete campaign: {str(e)}")
    
    def scrape_campaign_targets(self, campaign_id: int, user_id: int,
                               max_targets: Optional[int] = None) -> ScrapingResult:
        """
        Scrape targets for a campaign based on its configuration
        
        Args:
            campaign_id: ID of the campaign
            user_id: ID of the user (for permission check)
            max_targets: Maximum number of targets to scrape
            
        Returns:
            ScrapingResult: Result of the scraping operation
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
            CampaignValidationError: If campaign configuration is invalid
        """
        try:
            campaign = self.get_campaign(campaign_id, user_id)
            
            # Check if campaign is in draft status
            if campaign.status != 'draft':
                raise CampaignValidationError("Can only scrape targets for draft campaigns")
            
            # Clear existing targets
            self.target_scraper.clear_campaign_targets(campaign_id)
            
            # Scrape based on target type
            if campaign.target_type == 'user_followers':
                result = self.target_scraper.scrape_user_followers(
                    campaign_id=campaign_id,
                    username=campaign.target_identifier,
                    max_followers=max_targets
                )
            elif campaign.target_type == 'list_members':
                result = self.target_scraper.scrape_list_members(
                    campaign_id=campaign_id,
                    list_id=campaign.target_identifier,
                    max_members=max_targets
                )
            else:
                raise CampaignValidationError(
                    f"Target scraping not supported for type: {campaign.target_type}"
                )
            
            self.logger.info(f"Scraped targets for campaign {campaign_id}: {result}")
            return result
            
        except (CampaignNotFoundError, CampaignPermissionError, CampaignValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error scraping targets for campaign {campaign_id}: {e}")
            raise CampaignValidationError(f"Failed to scrape targets: {str(e)}")
    
    def get_campaign_statistics(self, campaign_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a campaign
        
        Args:
            campaign_id: ID of the campaign
            user_id: ID of the user (for permission check)
            
        Returns:
            Dict[str, Any]: Campaign statistics
            
        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignPermissionError: If user doesn't have permission
        """
        campaign = self.get_campaign(campaign_id, user_id)
        
        # Get target statistics
        target_stats = self.target_scraper.get_target_statistics(campaign_id)
        
        # Get message statistics
        message_stats = self._get_message_statistics(campaign_id)
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(campaign)
        
        return {
            'campaign_info': {
                'id': campaign.id,
                'name': campaign.name,
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat(),
                'started_at': campaign.started_at.isoformat() if campaign.started_at else None,
                'completed_at': campaign.completed_at.isoformat() if campaign.completed_at else None
            },
            'targets': target_stats,
            'messages': message_stats,
            'performance': performance_metrics
        }
    
    def _get_message_statistics(self, campaign_id: int) -> Dict[str, Any]:
        """Get message statistics for a campaign"""
        messages = CampaignMessage.query.filter_by(campaign_id=campaign_id).all()
        
        if not messages:
            return {
                'total_messages': 0,
                'status_breakdown': {},
                'success_rate': 0.0
            }
        
        status_counts = {}
        for message in messages:
            status = message.status or 'pending'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        sent_count = status_counts.get('sent', 0) + status_counts.get('delivered', 0)
        success_rate = (sent_count / len(messages)) * 100 if messages else 0
        
        return {
            'total_messages': len(messages),
            'status_breakdown': status_counts,
            'success_rate': round(success_rate, 2)
        }
    
    def _calculate_performance_metrics(self, campaign: Campaign) -> Dict[str, Any]:
        """Calculate performance metrics for a campaign"""
        metrics = {
            'delivery_rate': 0.0,
            'response_rate': 0.0,
            'positive_response_rate': 0.0,
            'engagement_score': 0.0
        }
        
        if campaign.total_targets > 0:
            # Delivery rate
            if campaign.messages_sent > 0:
                metrics['delivery_rate'] = (campaign.messages_sent / campaign.total_targets) * 100
            
            # Response rate
            if campaign.replies_received > 0 and campaign.messages_sent > 0:
                metrics['response_rate'] = (campaign.replies_received / campaign.messages_sent) * 100
            
            # Positive response rate
            if campaign.positive_replies > 0 and campaign.replies_received > 0:
                metrics['positive_response_rate'] = (campaign.positive_replies / campaign.replies_received) * 100
            
            # Engagement score (weighted combination of metrics)
            engagement_score = (
                metrics['delivery_rate'] * 0.3 +
                metrics['response_rate'] * 0.5 +
                metrics['positive_response_rate'] * 0.2
            )
            metrics['engagement_score'] = round(engagement_score, 2)
        
        # Round all metrics
        for key in ['delivery_rate', 'response_rate', 'positive_response_rate']:
            metrics[key] = round(metrics[key], 2)
        
        return metrics

# Factory function for creating service instances
def create_campaign_service() -> CampaignService:
    """
    Factory function to create a CampaignService instance
    
    Returns:
        CampaignService: Configured service instance
    """
    return CampaignService()