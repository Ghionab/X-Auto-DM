import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_
from flask import current_app

from models import db, Campaign, CampaignTarget, DirectMessage, TwitterAccount
from .twitter_service import TwitterService, AntiBot
from .gemini_service import GeminiService
from .scraper_service import ScraperService

logger = logging.getLogger(__name__)

class CampaignService:
    """Service for managing DM campaigns"""
    
    def __init__(self):
        self.twitter_service = TwitterService()
        self.gemini_service = GeminiService()
        self.scraper_service = ScraperService()
    
    def create_campaign(self, user_id: int, campaign_data: Dict) -> Tuple[bool, Dict]:
        """Create a new DM campaign"""
        try:
            campaign = Campaign(
                user_id=user_id,
                twitter_account_id=campaign_data['twitter_account_id'],
                name=campaign_data['name'],
                description=campaign_data.get('description', ''),
                target_type=campaign_data['target_type'],
                target_username=campaign_data.get('target_username'),
                ai_rules=json.dumps(campaign_data.get('ai_rules', {})),
                message_template=campaign_data.get('message_template', ''),
                personalization_enabled=campaign_data.get('personalization_enabled', True),
                daily_limit=campaign_data.get('daily_limit', 50),
                delay_min=campaign_data.get('delay_min', 30),
                delay_max=campaign_data.get('delay_max', 120),
                scheduled_start=campaign_data.get('scheduled_start'),
                scheduled_end=campaign_data.get('scheduled_end')
            )
            
            db.session.add(campaign)
            db.session.commit()
            
            logger.info(f"Created campaign {campaign.id} for user {user_id}")
            return True, campaign.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating campaign: {str(e)}")
            return False, {"error": str(e)}
    
    def add_targets_to_campaign(self, campaign_id: int, targets: List[Dict]) -> Tuple[bool, Dict]:
        """Add target users to a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            added_targets = []
            
            for target_data in targets:
                # Check if target already exists in campaign
                existing = CampaignTarget.query.filter_by(
                    campaign_id=campaign_id,
                    username=target_data['username']
                ).first()
                
                if existing:
                    continue  # Skip duplicates
                
                target = CampaignTarget(
                    campaign_id=campaign_id,
                    username=target_data['username'],
                    display_name=target_data.get('display_name', ''),
                    bio=target_data.get('bio', ''),
                    followers_count=target_data.get('followers_count', 0),
                    following_count=target_data.get('following_count', 0),
                    profile_image_url=target_data.get('profile_image_url', '')
                )
                
                db.session.add(target)
                added_targets.append(target_data)
            
            # Update campaign total targets count
            campaign.total_targets = CampaignTarget.query.filter_by(campaign_id=campaign_id).count()
            
            db.session.commit()
            
            logger.info(f"Added {len(added_targets)} targets to campaign {campaign_id}")
            return True, {
                "added_count": len(added_targets),
                "total_targets": campaign.total_targets,
                "targets": added_targets
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding targets to campaign: {str(e)}")
            return False, {"error": str(e)}
    
    def start_campaign(self, campaign_id: int) -> Tuple[bool, Dict]:
        """Start a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            if campaign.status != 'draft':
                return False, {"error": f"Campaign is already {campaign.status}"}
            
            # Validate campaign has targets
            target_count = CampaignTarget.query.filter_by(campaign_id=campaign_id).count()
            if target_count == 0:
                return False, {"error": "Campaign has no targets"}
            
            # Validate Twitter account is active
            twitter_account = TwitterAccount.query.get(campaign.twitter_account_id)
            if not twitter_account or not twitter_account.is_active:
                return False, {"error": "Twitter account not available"}
            
            campaign.status = 'active'
            campaign.scheduled_start = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Started campaign {campaign_id}")
            return True, {"message": "Campaign started successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting campaign: {str(e)}")
            return False, {"error": str(e)}
    
    def pause_campaign(self, campaign_id: int) -> Tuple[bool, Dict]:
        """Pause a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            if campaign.status != 'active':
                return False, {"error": f"Campaign is not active (current status: {campaign.status})"}
            
            campaign.status = 'paused'
            db.session.commit()
            
            logger.info(f"Paused campaign {campaign_id}")
            return True, {"message": "Campaign paused successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error pausing campaign: {str(e)}")
            return False, {"error": str(e)}
    
    def resume_campaign(self, campaign_id: int) -> Tuple[bool, Dict]:
        """Resume a paused campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            if campaign.status != 'paused':
                return False, {"error": f"Campaign is not paused (current status: {campaign.status})"}
            
            campaign.status = 'active'
            db.session.commit()
            
            logger.info(f"Resumed campaign {campaign_id}")
            return True, {"message": "Campaign resumed successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resuming campaign: {str(e)}")
            return False, {"error": str(e)}
    
    def process_campaign_messages(self, campaign_id: int, batch_size: int = 10) -> Tuple[bool, Dict]:
        """Process a batch of messages for a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign or campaign.status != 'active':
                return False, {"error": "Campaign not active"}
            
            # Check daily limits
            today = datetime.utcnow().date()
            messages_sent_today = DirectMessage.query.filter(
                and_(
                    DirectMessage.campaign_id == campaign_id,
                    DirectMessage.sent_at >= today,
                    DirectMessage.status == 'sent'
                )
            ).count()
            
            if messages_sent_today >= campaign.daily_limit:
                logger.info(f"Campaign {campaign_id} has reached daily limit ({campaign.daily_limit})")
                return True, {"message": "Daily limit reached", "processed": 0}
            
            # Get pending targets
            available_slots = min(batch_size, campaign.daily_limit - messages_sent_today)
            targets = CampaignTarget.query.filter_by(
                campaign_id=campaign_id,
                status='pending'
            ).limit(available_slots).all()
            
            if not targets:
                # Mark campaign as completed if no more targets
                campaign.status = 'completed'
                db.session.commit()
                return True, {"message": "Campaign completed - no more targets", "processed": 0}
            
            processed_count = 0
            errors = []
            
            for target in targets:
                try:
                    success, result = self._send_dm_to_target(campaign, target)
                    if success:
                        processed_count += 1
                        # Add delay between messages
                        delay = random.randint(campaign.delay_min, campaign.delay_max) * 60  # Convert to seconds
                        time.sleep(delay)
                    else:
                        errors.append(f"Failed to send to @{target.username}: {result.get('error', 'Unknown error')}")
                        target.status = 'failed'
                
                except Exception as e:
                    logger.error(f"Error processing target {target.username}: {str(e)}")
                    errors.append(f"Error with @{target.username}: {str(e)}")
                    target.status = 'failed'
            
            # Update campaign stats
            campaign.messages_sent += processed_count
            db.session.commit()
            
            logger.info(f"Processed {processed_count} messages for campaign {campaign_id}")
            
            return True, {
                "processed": processed_count,
                "errors": errors,
                "remaining_targets": CampaignTarget.query.filter_by(
                    campaign_id=campaign_id, status='pending'
                ).count()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing campaign messages: {str(e)}")
            return False, {"error": str(e)}
    
    def _send_dm_to_target(self, campaign: Campaign, target: CampaignTarget) -> Tuple[bool, Dict]:
        """Send a DM to a specific target"""
        try:
            # Generate personalized message
            ai_rules = json.loads(campaign.ai_rules) if campaign.ai_rules else {}
            target_profile = {
                'username': target.username,
                'name': target.display_name,
                'bio': target.bio,
                'followers_count': target.followers_count,
                'following_count': target.following_count
            }
            
            if campaign.personalization_enabled:
                success, message_content = self.gemini_service.generate_personalized_dm(
                    target_profile=target_profile,
                    campaign_rules=ai_rules,
                    template=campaign.message_template
                )
                
                if not success:
                    logger.error(f"Failed to generate DM for @{target.username}: {message_content}")
                    message_content = campaign.message_template or "Hello! Hope you're having a great day!"
            else:
                message_content = campaign.message_template or "Hello! Hope you're having a great day!"
            
            # Validate message quality
            if campaign.personalization_enabled:
                validation_success, validation_result = self.gemini_service.validate_message_quality(
                    message_content, ai_rules
                )
                
                if validation_success and not validation_result.get('approved', True):
                    logger.warning(f"Message quality validation failed for @{target.username}")
                    # You might want to regenerate or use a fallback message here
            
            # Send the message
            twitter_account = TwitterAccount.query.get(campaign.twitter_account_id)
            success, send_result = self.twitter_service.send_direct_message(
                recipient_username=target.username,
                message=message_content,
                sender_account_tokens={}  # Would contain actual OAuth tokens
            )
            
            # Create DirectMessage record
            dm = DirectMessage(
                campaign_id=campaign.id,
                target_id=target.id,
                twitter_account_id=campaign.twitter_account_id,
                content=message_content,
                twitter_message_id=send_result.get('message_id') if success else None,
                status='sent' if success else 'failed',
                error_message=send_result.get('error') if not success else None,
                ai_generated=campaign.personalization_enabled,
                sent_at=datetime.utcnow() if success else None
            )
            
            db.session.add(dm)
            
            # Update target status
            if success:
                target.status = 'sent'
                target.message_sent_at = datetime.utcnow()
            else:
                target.status = 'failed'
            
            db.session.commit()
            
            if success:
                logger.info(f"Successfully sent DM to @{target.username}")
            else:
                logger.error(f"Failed to send DM to @{target.username}: {send_result}")
            
            return success, send_result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending DM to target {target.username}: {str(e)}")
            return False, {"error": str(e)}
    
    def preview_campaign_message(self, campaign_id: int, target_username: str = None) -> Tuple[bool, Dict]:
        """Generate a preview message for the campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            # Get target profile (use a random target if none specified)
            if target_username:
                target = CampaignTarget.query.filter_by(
                    campaign_id=campaign_id,
                    username=target_username
                ).first()
            else:
                target = CampaignTarget.query.filter_by(
                    campaign_id=campaign_id
                ).first()
            
            if not target:
                return False, {"error": "No targets found for preview"}
            
            target_profile = {
                'username': target.username,
                'name': target.display_name,
                'bio': target.bio,
                'followers_count': target.followers_count,
                'following_count': target.following_count
            }
            
            ai_rules = json.loads(campaign.ai_rules) if campaign.ai_rules else {}
            
            if campaign.personalization_enabled:
                success, message_content = self.gemini_service.generate_personalized_dm(
                    target_profile=target_profile,
                    campaign_rules=ai_rules,
                    template=campaign.message_template
                )
                
                if not success:
                    message_content = campaign.message_template or "Hello! Hope you're having a great day!"
            else:
                message_content = campaign.message_template or "Hello! Hope you're having a great day!"
            
            # Validate message quality
            validation_result = {}
            if campaign.personalization_enabled:
                validation_success, validation_result = self.gemini_service.validate_message_quality(
                    message_content, ai_rules
                )
                if not validation_success:
                    validation_result = {"error": "Validation failed"}
            
            return True, {
                "message": message_content,
                "target_profile": target_profile,
                "validation": validation_result,
                "character_count": len(message_content),
                "estimated_delivery_time": self._calculate_delivery_time(campaign)
            }
            
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            return False, {"error": str(e)}
    
    def get_campaign_analytics(self, campaign_id: int) -> Tuple[bool, Dict]:
        """Get detailed analytics for a campaign"""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            # Basic stats
            total_targets = CampaignTarget.query.filter_by(campaign_id=campaign_id).count()
            messages_sent = DirectMessage.query.filter_by(
                campaign_id=campaign_id,
                status='sent'
            ).count()
            
            # Reply stats
            replies_received = DirectMessage.query.filter_by(
                campaign_id=campaign_id,
                message_type='inbound'
            ).count()
            
            positive_replies = DirectMessage.query.filter_by(
                campaign_id=campaign_id,
                message_type='inbound',
                sentiment='positive'
            ).count()
            
            negative_replies = DirectMessage.query.filter_by(
                campaign_id=campaign_id,
                message_type='inbound',
                sentiment='negative'
            ).count()
            
            # Calculate rates
            reply_rate = (replies_received / messages_sent * 100) if messages_sent > 0 else 0
            positive_rate = (positive_replies / replies_received * 100) if replies_received > 0 else 0
            
            # Status breakdown
            status_breakdown = {}
            statuses = db.session.query(
                CampaignTarget.status,
                db.func.count(CampaignTarget.id)
            ).filter_by(campaign_id=campaign_id).group_by(CampaignTarget.status).all()
            
            for status, count in statuses:
                status_breakdown[status] = count
            
            # Recent messages
            recent_messages = DirectMessage.query.filter_by(
                campaign_id=campaign_id
            ).order_by(DirectMessage.created_at.desc()).limit(10).all()
            
            return True, {
                "campaign_info": campaign.to_dict(),
                "stats": {
                    "total_targets": total_targets,
                    "messages_sent": messages_sent,
                    "replies_received": replies_received,
                    "positive_replies": positive_replies,
                    "negative_replies": negative_replies,
                    "reply_rate": round(reply_rate, 2),
                    "positive_rate": round(positive_rate, 2),
                },
                "status_breakdown": status_breakdown,
                "recent_messages": [msg.to_dict() for msg in recent_messages],
                "performance_metrics": self._calculate_performance_metrics(campaign)
            }
            
        except Exception as e:
            logger.error(f"Error getting campaign analytics: {str(e)}")
            return False, {"error": str(e)}
    
    def _calculate_delivery_time(self, campaign: Campaign) -> str:
        """Calculate estimated delivery time for campaign"""
        pending_targets = CampaignTarget.query.filter_by(
            campaign_id=campaign.id,
            status='pending'
        ).count()
        
        if pending_targets == 0:
            return "Campaign completed"
        
        daily_limit = campaign.daily_limit
        days_needed = (pending_targets + daily_limit - 1) // daily_limit  # Ceiling division
        
        if days_needed == 1:
            return "1 day"
        else:
            return f"{days_needed} days"
    
    def _calculate_performance_metrics(self, campaign: Campaign) -> Dict:
        """Calculate advanced performance metrics"""
        # This would include metrics like:
        # - Average response time
        # - Best performing message variations
        # - Time-based performance patterns
        # - Target demographic performance
        
        return {
            "avg_response_time": "2.5 hours",  # Mock data
            "best_performing_time": "2-4 PM",
            "top_performing_keywords": ["startup", "entrepreneur", "tech"],
            "demographic_performance": {
                "verified_users": {"reply_rate": 15.2, "positive_rate": 78.5},
                "high_followers": {"reply_rate": 12.8, "positive_rate": 82.1},
                "tech_industry": {"reply_rate": 18.9, "positive_rate": 85.3}
            }
        }
    
    def get_user_campaigns(self, user_id: int, status: str = None) -> List[Dict]:
        """Get all campaigns for a user"""
        try:
            query = Campaign.query.filter_by(user_id=user_id)
            
            if status:
                query = query.filter_by(status=status)
            
            campaigns = query.order_by(Campaign.created_at.desc()).all()
            
            return [campaign.to_dict() for campaign in campaigns]
            
        except Exception as e:
            logger.error(f"Error getting user campaigns: {str(e)}")
            return []
    
    def delete_campaign(self, campaign_id: int, user_id: int) -> Tuple[bool, Dict]:
        """Delete a campaign"""
        try:
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return False, {"error": "Campaign not found"}
            
            if campaign.status == 'active':
                return False, {"error": "Cannot delete active campaign. Pause it first."}
            
            # Delete related records (cascade should handle this)
            db.session.delete(campaign)
            db.session.commit()
            
            logger.info(f"Deleted campaign {campaign_id} for user {user_id}")
            return True, {"message": "Campaign deleted successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting campaign: {str(e)}")
            return False, {"error": str(e)}
