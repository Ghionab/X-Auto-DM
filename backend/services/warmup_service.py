import random
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import current_app

from models import db, TwitterAccount, WarmupActivity
from .twitter_service import TwitterService, AntiBot
from .gemini_service import GeminiService

logger = logging.getLogger(__name__)

class WarmupService:
    """Service for warming up Twitter accounts to appear more human-like"""
    
    def __init__(self):
        self.twitter_service = TwitterService()
        self.gemini_service = GeminiService()
    
    def start_warmup(self, twitter_account_id: int) -> Tuple[bool, Dict]:
        """Start warmup process for a Twitter account"""
        try:
            account = TwitterAccount.query.get(twitter_account_id)
            if not account:
                return False, {"error": "Twitter account not found"}
            
            if account.warmup_status != 'pending':
                return False, {"error": f"Account warmup is already {account.warmup_status}"}
            
            # Update account status
            account.warmup_status = 'in_progress'
            account.warmup_started_at = datetime.utcnow()
            
            db.session.commit()
            
            # Create warmup schedule for the account
            self._create_warmup_schedule(account)
            
            logger.info(f"Started warmup for Twitter account {twitter_account_id}")
            return True, {"message": "Warmup started successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting warmup: {str(e)}")
            return False, {"error": str(e)}
    
    def stop_warmup(self, twitter_account_id: int) -> Tuple[bool, Dict]:
        """Stop warmup process for a Twitter account"""
        try:
            account = TwitterAccount.query.get(twitter_account_id)
            if not account:
                return False, {"error": "Twitter account not found"}
            
            if account.warmup_status != 'in_progress':
                return False, {"error": f"Account warmup is not in progress (status: {account.warmup_status})"}
            
            account.warmup_status = 'pending'
            db.session.commit()
            
            logger.info(f"Stopped warmup for Twitter account {twitter_account_id}")
            return True, {"message": "Warmup stopped successfully"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error stopping warmup: {str(e)}")
            return False, {"error": str(e)}
    
    def _create_warmup_schedule(self, account: TwitterAccount) -> None:
        """Create a warmup schedule for an account"""
        warmup_duration = current_app.config['WARMUP_DURATION_DAYS']
        
        # Calculate daily activities for gradual increase
        daily_likes = self._calculate_daily_activities(
            current_app.config['WARMUP_LIKES_PER_DAY'], warmup_duration
        )
        daily_retweets = self._calculate_daily_activities(
            current_app.config['WARMUP_RETWEETS_PER_DAY'], warmup_duration
        )
        daily_replies = self._calculate_daily_activities(
            current_app.config['WARMUP_REPLIES_PER_DAY'], warmup_duration
        )
        
        # Schedule activities for each day
        for day in range(warmup_duration):
            scheduled_date = datetime.utcnow() + timedelta(days=day)
            
            # Schedule likes
            for _ in range(daily_likes[day]):
                self._schedule_warmup_activity(
                    account.id, 'like', scheduled_date
                )
            
            # Schedule retweets
            for _ in range(daily_retweets[day]):
                self._schedule_warmup_activity(
                    account.id, 'retweet', scheduled_date
                )
            
            # Schedule replies
            for _ in range(daily_replies[day]):
                self._schedule_warmup_activity(
                    account.id, 'reply', scheduled_date
                )
    
    def _calculate_daily_activities(self, max_daily: int, duration_days: int) -> List[int]:
        """Calculate daily activity counts with gradual increase"""
        daily_counts = []
        
        for day in range(duration_days):
            # Gradual increase: start with 20% on day 1, reach 100% by final day
            progress = (day + 1) / duration_days
            base_count = int(max_daily * (0.2 + 0.8 * progress))
            
            # Add randomization to make it more human-like
            variation = random.uniform(0.7, 1.3)
            daily_count = max(1, int(base_count * variation))
            
            daily_counts.append(daily_count)
        
        return daily_counts
    
    def _schedule_warmup_activity(self, twitter_account_id: int, activity_type: str, 
                                 base_date: datetime) -> None:
        """Schedule a single warmup activity"""
        # Random time within the day
        random_hour = random.randint(9, 21)  # 9 AM to 9 PM
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)
        
        scheduled_time = base_date.replace(
            hour=random_hour, 
            minute=random_minute, 
            second=random_second
        )
        
        activity = WarmupActivity(
            twitter_account_id=twitter_account_id,
            activity_type=activity_type,
            status='pending',
            created_at=scheduled_time  # Use created_at to represent scheduled time
        )
        
        db.session.add(activity)
    
    def execute_pending_warmup_activities(self) -> Dict:
        """Execute pending warmup activities (called by scheduler)"""
        logger.info("Executing pending warmup activities...")
        
        # Get activities that are due (within the last hour)
        cutoff_time = datetime.utcnow() - timedelta(minutes=60)
        
        pending_activities = WarmupActivity.query.filter(
            WarmupActivity.status == 'pending',
            WarmupActivity.created_at <= datetime.utcnow(),
            WarmupActivity.created_at >= cutoff_time
        ).limit(50).all()  # Process in batches
        
        executed_count = 0
        failed_count = 0
        
        for activity in pending_activities:
            try:
                success = self._execute_warmup_activity(activity)
                if success:
                    executed_count += 1
                else:
                    failed_count += 1
                
                # Human-like delay between activities
                AntiBot.random_delay(5, 15)
                
            except Exception as e:
                logger.error(f"Error executing warmup activity {activity.id}: {str(e)}")
                activity.status = 'failed'
                activity.error_message = str(e)
                failed_count += 1
        
        db.session.commit()
        
        logger.info(f"Warmup execution completed: {executed_count} executed, {failed_count} failed")
        
        return {
            "executed": executed_count,
            "failed": failed_count,
            "total_processed": len(pending_activities)
        }
    
    def _execute_warmup_activity(self, activity: WarmupActivity) -> bool:
        """Execute a single warmup activity"""
        try:
            account = TwitterAccount.query.get(activity.twitter_account_id)
            if not account or account.warmup_status != 'in_progress':
                activity.status = 'failed'
                activity.error_message = "Account not available for warmup"
                return False
            
            if activity.activity_type == 'like':
                return self._execute_like_activity(activity)
            elif activity.activity_type == 'retweet':
                return self._execute_retweet_activity(activity)
            elif activity.activity_type == 'reply':
                return self._execute_reply_activity(activity)
            elif activity.activity_type == 'follow':
                return self._execute_follow_activity(activity)
            else:
                activity.status = 'failed'
                activity.error_message = f"Unknown activity type: {activity.activity_type}"
                return False
                
        except Exception as e:
            logger.error(f"Error executing warmup activity: {str(e)}")
            activity.status = 'failed'
            activity.error_message = str(e)
            return False
    
    def _execute_like_activity(self, activity: WarmupActivity) -> bool:
        """Execute a like activity"""
        try:
            # Get trending tweets to like
            success, tweets_data = self.twitter_service.get_trending_tweets(limit=20)
            
            if not success or not tweets_data.get('tweets'):
                logger.warning("No trending tweets found for like activity")
                activity.status = 'failed'
                activity.error_message = "No tweets available to like"
                return False
            
            # Select a random tweet to like
            tweet = random.choice(tweets_data['tweets'])
            
            # Execute the like
            success, result = self.twitter_service.like_tweet(
                tweet_id=tweet['id'],
                account_tokens={}  # Would contain actual OAuth tokens
            )
            
            if success:
                activity.status = 'completed'
                activity.target_tweet_id = tweet['id']
                activity.target_username = tweet.get('author_username')
                activity.executed_at = datetime.utcnow()
                
                logger.info(f"Successfully liked tweet {tweet['id']} for warmup")
                return True
            else:
                activity.status = 'failed'
                activity.error_message = result.get('error', 'Unknown error')
                return False
                
        except Exception as e:
            logger.error(f"Error executing like activity: {str(e)}")
            activity.status = 'failed'
            activity.error_message = str(e)
            return False
    
    def _execute_retweet_activity(self, activity: WarmupActivity) -> bool:
        """Execute a retweet activity"""
        try:
            # Get trending tweets to retweet
            success, tweets_data = self.twitter_service.get_trending_tweets(limit=20)
            
            if not success or not tweets_data.get('tweets'):
                logger.warning("No trending tweets found for retweet activity")
                activity.status = 'failed'
                activity.error_message = "No tweets available to retweet"
                return False
            
            # Select a random tweet to retweet (prefer ones with lower retweet counts)
            tweets = tweets_data['tweets']
            selected_tweet = min(tweets, key=lambda t: t.get('public_metrics', {}).get('retweet_count', 0))
            
            # Execute the retweet
            success, result = self.twitter_service.retweet(
                tweet_id=selected_tweet['id'],
                account_tokens={}  # Would contain actual OAuth tokens
            )
            
            if success:
                activity.status = 'completed'
                activity.target_tweet_id = selected_tweet['id']
                activity.target_username = selected_tweet.get('author_username')
                activity.executed_at = datetime.utcnow()
                
                logger.info(f"Successfully retweeted {selected_tweet['id']} for warmup")
                return True
            else:
                activity.status = 'failed'
                activity.error_message = result.get('error', 'Unknown error')
                return False
                
        except Exception as e:
            logger.error(f"Error executing retweet activity: {str(e)}")
            activity.status = 'failed'
            activity.error_message = str(e)
            return False
    
    def _execute_reply_activity(self, activity: WarmupActivity) -> bool:
        """Execute a reply activity"""
        try:
            # Get trending tweets to reply to
            success, tweets_data = self.twitter_service.get_trending_tweets(limit=20)
            
            if not success or not tweets_data.get('tweets'):
                logger.warning("No trending tweets found for reply activity")
                activity.status = 'failed'
                activity.error_message = "No tweets available to reply to"
                return False
            
            # Select a random tweet to reply to
            tweet = random.choice(tweets_data['tweets'])
            
            # Generate a human-like reply using Gemini
            target_profile = {
                'tweet_text': tweet['text'],
                'author_username': tweet.get('author_username'),
                'author_name': tweet.get('author_name')
            }
            
            success, reply_text = self.gemini_service.generate_warmup_content(
                content_type='reply',
                target_profile=target_profile
            )
            
            if not success:
                # Fallback to generic replies
                generic_replies = [
                    "Great point!",
                    "Thanks for sharing this.",
                    "Very insightful.",
                    "Couldn't agree more.",
                    "Interesting perspective!",
                    "Well said!",
                    "This is valuable information."
                ]
                reply_text = random.choice(generic_replies)
            
            # Execute the reply
            success, result = self.twitter_service.reply_to_tweet(
                tweet_id=tweet['id'],
                reply_text=reply_text,
                account_tokens={}  # Would contain actual OAuth tokens
            )
            
            if success:
                activity.status = 'completed'
                activity.target_tweet_id = tweet['id']
                activity.target_username = tweet.get('author_username')
                activity.executed_at = datetime.utcnow()
                
                logger.info(f"Successfully replied to tweet {tweet['id']} for warmup")
                return True
            else:
                activity.status = 'failed'
                activity.error_message = result.get('error', 'Unknown error')
                return False
                
        except Exception as e:
            logger.error(f"Error executing reply activity: {str(e)}")
            activity.status = 'failed'
            activity.error_message = str(e)
            return False
    
    def _execute_follow_activity(self, activity: WarmupActivity) -> bool:
        """Execute a follow activity"""
        try:
            # This would implement following logic
            # For now, we'll mark as completed
            activity.status = 'completed'
            activity.executed_at = datetime.utcnow()
            
            logger.info(f"Follow activity completed for warmup (placeholder)")
            return True
            
        except Exception as e:
            logger.error(f"Error executing follow activity: {str(e)}")
            activity.status = 'failed'
            activity.error_message = str(e)
            return False
    
    def get_warmup_status(self, twitter_account_id: int) -> Tuple[bool, Dict]:
        """Get warmup status and statistics for an account"""
        try:
            account = TwitterAccount.query.get(twitter_account_id)
            if not account:
                return False, {"error": "Twitter account not found"}
            
            # Get activity statistics
            total_activities = WarmupActivity.query.filter_by(
                twitter_account_id=twitter_account_id
            ).count()
            
            completed_activities = WarmupActivity.query.filter_by(
                twitter_account_id=twitter_account_id,
                status='completed'
            ).count()
            
            pending_activities = WarmupActivity.query.filter_by(
                twitter_account_id=twitter_account_id,
                status='pending'
            ).count()
            
            failed_activities = WarmupActivity.query.filter_by(
                twitter_account_id=twitter_account_id,
                status='failed'
            ).count()
            
            # Activity breakdown by type
            activity_breakdown = {}
            activity_types = ['like', 'retweet', 'reply', 'follow']
            
            for activity_type in activity_types:
                completed_count = WarmupActivity.query.filter_by(
                    twitter_account_id=twitter_account_id,
                    activity_type=activity_type,
                    status='completed'
                ).count()
                
                activity_breakdown[activity_type] = completed_count
            
            # Calculate progress
            progress_percentage = (completed_activities / total_activities * 100) if total_activities > 0 else 0
            
            # Determine if warmup is complete
            if account.warmup_status == 'in_progress' and pending_activities == 0:
                account.warmup_status = 'completed'
                db.session.commit()
            
            # Calculate days remaining
            days_elapsed = 0
            days_remaining = 0
            
            if account.warmup_started_at:
                days_elapsed = (datetime.utcnow() - account.warmup_started_at).days
                days_remaining = max(0, current_app.config['WARMUP_DURATION_DAYS'] - days_elapsed)
            
            return True, {
                "account_id": twitter_account_id,
                "warmup_status": account.warmup_status,
                "warmup_started_at": account.warmup_started_at.isoformat() if account.warmup_started_at else None,
                "progress_percentage": round(progress_percentage, 1),
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "statistics": {
                    "total_activities": total_activities,
                    "completed_activities": completed_activities,
                    "pending_activities": pending_activities,
                    "failed_activities": failed_activities
                },
                "activity_breakdown": activity_breakdown,
                "next_activities": self._get_next_activities(twitter_account_id, limit=5)
            }
            
        except Exception as e:
            logger.error(f"Error getting warmup status: {str(e)}")
            return False, {"error": str(e)}
    
    def _get_next_activities(self, twitter_account_id: int, limit: int = 5) -> List[Dict]:
        """Get next scheduled activities for an account"""
        try:
            next_activities = WarmupActivity.query.filter_by(
                twitter_account_id=twitter_account_id,
                status='pending'
            ).order_by(WarmupActivity.created_at.asc()).limit(limit).all()
            
            return [
                {
                    "activity_type": activity.activity_type,
                    "scheduled_time": activity.created_at.isoformat(),
                    "time_until": self._calculate_time_until(activity.created_at)
                }
                for activity in next_activities
            ]
            
        except Exception as e:
            logger.error(f"Error getting next activities: {str(e)}")
            return []
    
    def _calculate_time_until(self, scheduled_time: datetime) -> str:
        """Calculate human-readable time until scheduled activity"""
        try:
            time_diff = scheduled_time - datetime.utcnow()
            
            if time_diff.total_seconds() < 0:
                return "Overdue"
            
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            if hours > 24:
                days = hours // 24
                return f"{days} days"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception:
            return "Unknown"
    
    def cleanup_old_activities(self, days_old: int = 30) -> int:
        """Clean up old warmup activities"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted_count = WarmupActivity.query.filter(
                WarmupActivity.created_at < cutoff_date,
                WarmupActivity.status.in_(['completed', 'failed'])
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old warmup activities")
            return deleted_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up old activities: {str(e)}")
            return 0
