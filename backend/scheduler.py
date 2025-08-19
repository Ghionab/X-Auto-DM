import logging
import schedule
import time
import threading
from datetime import datetime
from flask import Flask

from app import create_app
from services.campaign_service import CampaignService
from services.warmup_service import WarmupService
from models import db, Campaign

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Background scheduler for running periodic tasks"""
    
    def __init__(self):
        self.app = create_app()
        self.campaign_service = CampaignService()
        self.warmup_service = WarmupService()
        self.running = False
        self.thread = None
    
    def setup_schedules(self):
        """Setup all scheduled tasks"""
        
        # Campaign processing - every 30 minutes
        schedule.every(30).minutes.do(self.process_active_campaigns)
        
        # Warmup activities - every 15 minutes
        schedule.every(15).minutes.do(self.execute_warmup_activities)
        
        # Daily cleanup - every day at 2 AM
        schedule.every().day.at("02:00").do(self.daily_cleanup)
        
        # Analytics aggregation - every 6 hours
        schedule.every(6).hours.do(self.aggregate_analytics)
        
        logger.info("Background tasks scheduled successfully")
    
    def process_active_campaigns(self):
        """Process messages for active campaigns"""
        try:
            with self.app.app_context():
                logger.info("Processing active campaigns...")
                
                # Get all active campaigns
                active_campaigns = Campaign.query.filter_by(status='active').all()
                
                total_processed = 0
                total_errors = 0
                
                for campaign in active_campaigns:
                    try:
                        success, result = self.campaign_service.process_campaign_messages(
                            campaign.id, 
                            batch_size=5  # Process 5 messages per campaign per run
                        )
                        
                        if success:
                            processed = result.get('processed', 0)
                            errors = len(result.get('errors', []))
                            total_processed += processed
                            total_errors += errors
                            
                            if processed > 0:
                                logger.info(f"Campaign {campaign.id}: processed {processed} messages")
                        
                    except Exception as e:
                        logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
                        total_errors += 1
                
                logger.info(f"Campaign processing completed: {total_processed} processed, {total_errors} errors")
                
        except Exception as e:
            logger.error(f"Error in campaign processing task: {str(e)}")
    
    def execute_warmup_activities(self):
        """Execute pending warmup activities"""
        try:
            with self.app.app_context():
                logger.info("Executing warmup activities...")
                
                result = self.warmup_service.execute_pending_warmup_activities()
                
                executed = result.get('executed', 0)
                failed = result.get('failed', 0)
                
                if executed > 0 or failed > 0:
                    logger.info(f"Warmup activities: {executed} executed, {failed} failed")
                
        except Exception as e:
            logger.error(f"Error in warmup activities task: {str(e)}")
    
    def daily_cleanup(self):
        """Daily cleanup tasks"""
        try:
            with self.app.app_context():
                logger.info("Running daily cleanup...")
                
                # Cleanup old warmup activities (older than 30 days)
                deleted_activities = self.warmup_service.cleanup_old_activities(days_old=30)
                
                # Cleanup old analytics data (older than 90 days)
                # This would be implemented when analytics service is added
                
                # Update campaign statuses if needed
                self._update_campaign_statuses()
                
                logger.info(f"Daily cleanup completed: {deleted_activities} old activities removed")
                
        except Exception as e:
            logger.error(f"Error in daily cleanup task: {str(e)}")
    
    def aggregate_analytics(self):
        """Aggregate analytics data"""
        try:
            with self.app.app_context():
                logger.info("Aggregating analytics data...")
                
                # This would implement analytics aggregation
                # - Calculate daily/weekly/monthly metrics
                # - Update user statistics
                # - Generate performance reports
                
                logger.info("Analytics aggregation completed")
                
        except Exception as e:
            logger.error(f"Error in analytics aggregation task: {str(e)}")
    
    def _update_campaign_statuses(self):
        """Update campaign statuses based on targets and scheduling"""
        try:
            from models import CampaignTarget
            
            # Find campaigns that should be completed
            active_campaigns = Campaign.query.filter_by(status='active').all()
            
            for campaign in active_campaigns:
                # Check if all targets are processed
                pending_targets = CampaignTarget.query.filter_by(
                    campaign_id=campaign.id,
                    status='pending'
                ).count()
                
                if pending_targets == 0:
                    campaign.status = 'completed'
                    logger.info(f"Campaign {campaign.id} marked as completed")
                
                # Check if campaign has exceeded end date
                elif campaign.scheduled_end and datetime.utcnow() > campaign.scheduled_end:
                    campaign.status = 'completed'
                    logger.info(f"Campaign {campaign.id} completed due to end date")
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating campaign statuses: {str(e)}")
            db.session.rollback()
    
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.setup_schedules()
        self.running = True
        
        def run_scheduler():
            logger.info("Background scheduler started")
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Scheduler error: {str(e)}")
                    time.sleep(60)
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Background scheduler thread started")
    
    def stop(self):
        """Stop the background scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        self.running = False
        schedule.clear()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("Background scheduler stopped")

# Global scheduler instance
scheduler = BackgroundScheduler()

def start_background_tasks():
    """Start background tasks (called from main app)"""
    scheduler.start()

def stop_background_tasks():
    """Stop background tasks"""
    scheduler.stop()

if __name__ == '__main__':
    # Run scheduler as standalone script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting XReacher background scheduler...")
    
    try:
        scheduler.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.stop()
        logger.info("Scheduler stopped")
