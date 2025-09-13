"""
Unit tests for Bulk DM Service
Tests bulk DM operations, rate limiting, personalization, and error handling
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.bulk_dm_service import (
    BulkDMService, RateLimiter, MessagePersonalizer, 
    BulkDMProgress, BulkDMResult, send_bulk_dms, get_sending_progress
)
from models import Campaign, CampaignTarget, CampaignMessage, TwitterAccount, db
from twitterio.dm import DMSendResult, TwitterAPIError


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values"""
        limiter = RateLimiter()
        assert limiter.daily_limit == 50
        assert limiter.delay_min == 30
        assert limiter.delay_max == 120
        assert limiter.sent_today == 0
        assert limiter.last_sent_time is None
    
    def test_rate_limiter_custom_values(self):
        """Test rate limiter initialization with custom values"""
        limiter = RateLimiter(daily_limit=100, delay_min=60, delay_max=180)
        assert limiter.daily_limit == 100
        assert limiter.delay_min == 60
        assert limiter.delay_max == 180
    
    def test_can_send_initial(self):
        """Test can_send returns True initially"""
        limiter = RateLimiter()
        assert limiter.can_send() is True
    
    def test_can_send_after_daily_limit(self):
        """Test can_send returns False after reaching daily limit"""
        limiter = RateLimiter(daily_limit=2, delay_min=0)  # No delay for this test
        
        # First send should be allowed
        assert limiter.can_send() is True
        limiter.record_send()
        
        # Second send should be allowed (up to limit)
        assert limiter.can_send() is True
        limiter.record_send()
        
        # Third send should be blocked (exceeds limit)
        assert limiter.can_send() is False
    
    def test_can_send_with_time_delay(self):
        """Test can_send respects time delays"""
        limiter = RateLimiter(delay_min=60)  # 1 minute delay
        
        # First send should be allowed
        assert limiter.can_send() is True
        limiter.record_send()
        
        # Immediate second send should be blocked
        assert limiter.can_send() is False
    
    def test_wait_time_calculation(self):
        """Test wait time calculation"""
        limiter = RateLimiter(delay_min=60)
        
        # No wait time initially
        assert limiter.wait_time() == 0
        
        # After sending, should have wait time
        limiter.record_send()
        wait_time = limiter.wait_time()
        assert 55 <= wait_time <= 60  # Allow for small timing differences
    
    def test_daily_reset(self):
        """Test daily counter reset"""
        limiter = RateLimiter(daily_limit=1, delay_min=0)  # No delay for this test
        
        # Reach daily limit
        limiter.record_send()
        assert limiter.can_send() is False
        
        # Simulate next day
        limiter.daily_reset_time = datetime.now() - timedelta(hours=1)
        assert limiter.can_send() is True


class TestMessagePersonalizer:
    """Test message personalization functionality"""
    
    def setup_method(self):
        """Set up test data"""
        self.target = Mock()
        self.target.username = "testuser"
        self.target.display_name = "Test User"
        self.target.follower_count = 1000
        self.target.following_count = 500
    
    def test_personalize_basic_variables(self):
        """Test basic variable replacement"""
        template = "Hello {name}, welcome to our service!"
        result = MessagePersonalizer.personalize_message(template, self.target)
        assert result == "Hello Test User, welcome to our service!"
    
    def test_personalize_username_variable(self):
        """Test username variable replacement"""
        template = "Hi @{username}, thanks for following!"
        result = MessagePersonalizer.personalize_message(template, self.target)
        assert result == "Hi @testuser, thanks for following!"
    
    def test_personalize_follower_count(self):
        """Test follower count variable replacement"""
        template = "Wow, you have {follower_count} followers!"
        result = MessagePersonalizer.personalize_message(template, self.target)
        assert result == "Wow, you have 1000 followers!"
    
    def test_personalize_multiple_variables(self):
        """Test multiple variable replacement"""
        template = "Hi {name} (@{username}), you have {follower_count} followers and follow {following_count} accounts."
        result = MessagePersonalizer.personalize_message(template, self.target)
        expected = "Hi Test User (@testuser), you have 1000 followers and follow 500 accounts."
        assert result == expected
    
    def test_personalize_missing_display_name(self):
        """Test fallback when display name is missing"""
        self.target.display_name = None
        template = "Hello {name}!"
        result = MessagePersonalizer.personalize_message(template, self.target)
        assert result == "Hello testuser!"
    
    def test_personalize_missing_counts(self):
        """Test handling of missing follower counts"""
        self.target.follower_count = None
        self.target.following_count = None
        template = "You have {follower_count} followers"
        result = MessagePersonalizer.personalize_message(template, self.target)
        assert result == "You have 0 followers"
    
    def test_personalize_empty_template(self):
        """Test handling of empty template"""
        result = MessagePersonalizer.personalize_message("", self.target)
        assert result == ""
        
        result = MessagePersonalizer.personalize_message(None, self.target)
        assert result == ""
    
    def test_validate_template_valid(self):
        """Test template validation for valid templates"""
        template = "Hello {name}, you have {follower_count} followers!"
        is_valid, errors = MessagePersonalizer.validate_template(template)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_template_empty(self):
        """Test template validation for empty templates"""
        is_valid, errors = MessagePersonalizer.validate_template("")
        assert is_valid is False
        assert "Template cannot be empty" in errors
        
        is_valid, errors = MessagePersonalizer.validate_template(None)
        assert is_valid is False
        assert "Template cannot be empty" in errors
    
    def test_validate_template_unsupported_variable(self):
        """Test template validation for unsupported variables"""
        template = "Hello {name}, your email is {email}"
        is_valid, errors = MessagePersonalizer.validate_template(template)
        assert is_valid is False
        assert "Unsupported variable: {email}" in errors
    
    def test_validate_template_too_long(self):
        """Test template validation for overly long templates"""
        template = "x" * 9001  # Exceeds 9000 character limit
        is_valid, errors = MessagePersonalizer.validate_template(template)
        assert is_valid is False
        assert "Template too long" in errors[0]


class TestBulkDMService:
    """Test bulk DM service functionality"""
    
    def setup_method(self):
        """Set up test data"""
        self.service = BulkDMService()
        
        # Mock campaign
        self.campaign = Mock()
        self.campaign.id = 1
        self.campaign.status = 'draft'
        self.campaign.message_template = "Hello {name}!"
        self.campaign.daily_limit = 50
        self.campaign.delay_min = 30
        self.campaign.delay_max = 120
        
        # Mock Twitter account
        self.twitter_account = Mock()
        self.twitter_account.login_cookie = "test_cookie"
        self.campaign.twitter_account = self.twitter_account
        
        # Mock targets
        self.target1 = Mock()
        self.target1.id = 1
        self.target1.username = "user1"
        self.target1.display_name = "User One"
        self.target1.twitter_user_id = "123456"
        self.target1.status = 'pending'
        self.target1.can_dm = True
        
        self.target2 = Mock()
        self.target2.id = 2
        self.target2.username = "user2"
        self.target2.display_name = "User Two"
        self.target2.twitter_user_id = "789012"
        self.target2.status = 'pending'
        self.target2.can_dm = True
    
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.CampaignTarget')
    def test_start_campaign_sending_campaign_not_found(self, mock_target, mock_campaign):
        """Test error handling when campaign is not found"""
        mock_campaign.query.get.return_value = None
        
        with pytest.raises(ValueError, match="Campaign 1 not found"):
            self.service.start_campaign_sending(1)
    
    @patch('services.bulk_dm_service.Campaign')
    def test_start_campaign_sending_invalid_status(self, mock_campaign):
        """Test error handling for invalid campaign status"""
        campaign = Mock()
        campaign.status = 'completed'
        mock_campaign.query.get.return_value = campaign
        
        with pytest.raises(ValueError, match="not in a sendable state"):
            self.service.start_campaign_sending(1)
    
    @patch('services.bulk_dm_service.Campaign')
    def test_start_campaign_sending_no_twitter_account(self, mock_campaign):
        """Test error handling when no Twitter account is available"""
        campaign = Mock()
        campaign.status = 'draft'
        campaign.twitter_account = None
        mock_campaign.query.get.return_value = campaign
        
        with pytest.raises(ValueError, match="No valid Twitter account found"):
            self.service.start_campaign_sending(1)
    
    @patch('services.bulk_dm_service.Campaign')
    def test_start_campaign_sending_invalid_template(self, mock_campaign):
        """Test error handling for invalid message template"""
        campaign = Mock()
        campaign.status = 'draft'
        campaign.message_template = ""
        campaign.twitter_account = Mock()
        campaign.twitter_account.login_cookie = "test"
        mock_campaign.query.get.return_value = campaign
        
        with pytest.raises(ValueError, match="Invalid message template"):
            self.service.start_campaign_sending(1)
    
    @patch('services.bulk_dm_service.db')
    @patch('services.bulk_dm_service.CampaignTarget')
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.TwitterDMClient')
    def test_send_dm_batch_success(self, mock_dm_client, mock_campaign, mock_target, mock_db):
        """Test successful DM batch sending"""
        # Setup mocks
        mock_campaign.query.get.return_value = self.campaign
        mock_target.query.filter_by.return_value.filter.return_value.all.return_value = [self.target1, self.target2]
        
        # Mock DM client
        dm_client_instance = Mock()
        mock_dm_client.return_value = dm_client_instance
        
        # Mock successful DM sends
        dm_result = DMSendResult(message_id="msg123", status="sent")
        dm_client_instance.send_dm.return_value = dm_result
        
        # Mock rate limiter to always allow sending
        with patch.object(self.service, '_send_dm_batch') as mock_send_batch:
            mock_send_batch.return_value = BulkDMResult(
                campaign_id=1,
                total_targets=2,
                sent_count=2,
                failed_count=0,
                errors=[],
                duration_seconds=1.0,
                status="completed"
            )
            
            result = self.service.start_campaign_sending(1)
            
            assert result.sent_count == 2
            assert result.failed_count == 0
            assert result.status == "completed"
    
    @patch('services.bulk_dm_service.TwitterDMClient')
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.CampaignMessage')
    @patch('services.bulk_dm_service.db')
    def test_send_dm_batch_with_failures(self, mock_db, mock_campaign_message, mock_campaign, mock_dm_client):
        """Test DM batch sending with some failures"""
        # Mock DM client
        dm_client_instance = Mock()
        mock_dm_client.return_value = dm_client_instance
        
        # Mock mixed results - first succeeds, second fails
        dm_client_instance.send_dm.side_effect = [
            DMSendResult(message_id="msg123", status="sent"),
            TwitterAPIError("Rate limit exceeded")
        ]
        
        # Mock campaign query to return the same campaign (not paused)
        mock_campaign.query.get.return_value = self.campaign
        
        # Mock rate limiter
        rate_limiter = Mock()
        rate_limiter.can_send.return_value = True
        
        # Mock progress
        progress = BulkDMProgress(
            campaign_id=1,
            total_targets=2,
            processed=0,
            sent=0,
            failed=0
        )
        
        result = self.service._send_dm_batch(
            targets=[self.target1, self.target2],
            campaign=self.campaign,
            twitter_account=self.twitter_account,
            rate_limiter=rate_limiter,
            progress=progress
        )
        
        assert result.sent_count == 1
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert result.errors[0]['username'] == 'user2'
    
    def test_is_retryable_error(self):
        """Test retryable error detection"""
        # Retryable errors
        assert self.service._is_retryable_error(TwitterAPIError("Rate limit exceeded")) is True
        assert self.service._is_retryable_error(TwitterAPIError("Network timeout")) is True
        assert self.service._is_retryable_error(TwitterAPIError("Connection failed")) is True
        
        # Non-retryable errors
        assert self.service._is_retryable_error(TwitterAPIError("Unauthorized")) is False
        assert self.service._is_retryable_error(TwitterAPIError("User not found")) is False
        assert self.service._is_retryable_error(TwitterAPIError("Account suspended")) is False
    
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.db')
    def test_pause_campaign_sending(self, mock_db, mock_campaign):
        """Test pausing an active campaign"""
        campaign = Mock()
        campaign.status = 'active'
        mock_campaign.query.get.return_value = campaign
        
        result = self.service.pause_campaign_sending(1)
        
        assert result is True
        assert campaign.status == 'paused'
    
    @patch('services.bulk_dm_service.Campaign')
    def test_pause_campaign_sending_not_found(self, mock_campaign):
        """Test pausing a non-existent campaign"""
        mock_campaign.query.get.return_value = None
        
        result = self.service.pause_campaign_sending(1)
        assert result is False
    
    @patch('services.bulk_dm_service.Campaign')
    def test_pause_campaign_sending_not_active(self, mock_campaign):
        """Test pausing a non-active campaign"""
        campaign = Mock()
        campaign.status = 'draft'
        mock_campaign.query.get.return_value = campaign
        
        result = self.service.pause_campaign_sending(1)
        assert result is False
    
    def test_get_campaign_progress(self):
        """Test getting campaign progress"""
        # No progress initially
        progress = self.service.get_campaign_progress(1)
        assert progress is None
        
        # Add progress to cache
        test_progress = BulkDMProgress(
            campaign_id=1,
            total_targets=10,
            processed=5,
            sent=4,
            failed=1
        )
        
        with self.service._lock:
            self.service.progress_cache[1] = test_progress
        
        progress = self.service.get_campaign_progress(1)
        assert progress is not None
        assert progress.campaign_id == 1
        assert progress.processed == 5
        assert progress.sent == 4
        assert progress.failed == 1
    
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.CampaignTarget')
    @patch('services.bulk_dm_service.db')
    def test_retry_failed_targets(self, mock_db, mock_target, mock_campaign):
        """Test retrying failed targets"""
        # Mock campaign
        campaign = Mock()
        campaign.id = 1
        mock_campaign.query.get.return_value = campaign
        
        # Mock failed targets
        failed_target = Mock()
        failed_target.status = 'failed'
        failed_target.error_message = "Previous error"
        
        mock_target.query.filter_by.return_value.all.return_value = [failed_target]
        
        # Mock the start_campaign_sending method
        with patch.object(self.service, 'start_campaign_sending') as mock_start:
            mock_start.return_value = BulkDMResult(
                campaign_id=1,
                total_targets=1,
                sent_count=1,
                failed_count=0,
                errors=[],
                duration_seconds=1.0,
                status="completed"
            )
            
            result = self.service.retry_failed_targets(1)
            
            # Check that target was reset
            assert failed_target.status == 'pending'
            assert failed_target.error_message is None
            
            # Check that start_campaign_sending was called
            mock_start.assert_called_once_with(1)
            
            assert result.sent_count == 1
            assert result.failed_count == 0


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('services.bulk_dm_service.BulkDMService')
    def test_send_bulk_dms(self, mock_service_class):
        """Test send_bulk_dms convenience function"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        expected_result = BulkDMResult(
            campaign_id=1,
            total_targets=5,
            sent_count=5,
            failed_count=0,
            errors=[],
            duration_seconds=10.0,
            status="completed"
        )
        mock_service.start_campaign_sending.return_value = expected_result
        
        result = send_bulk_dms(1)
        
        mock_service.start_campaign_sending.assert_called_once_with(1)
        assert result == expected_result
    
    @patch('services.bulk_dm_service.BulkDMService')
    def test_get_sending_progress(self, mock_service_class):
        """Test get_sending_progress convenience function"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        expected_progress = BulkDMProgress(
            campaign_id=1,
            total_targets=10,
            processed=5,
            sent=4,
            failed=1
        )
        mock_service.get_campaign_progress.return_value = expected_progress
        
        result = get_sending_progress(1)
        
        mock_service.get_campaign_progress.assert_called_once_with(1)
        assert result == expected_progress


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    def setup_method(self):
        """Set up integration test data"""
        self.service = BulkDMService()
    
    @patch('services.bulk_dm_service.Campaign')
    @patch('services.bulk_dm_service.CampaignTarget')
    @patch('services.bulk_dm_service.TwitterDMClient')
    @patch('services.bulk_dm_service.db')
    def test_full_campaign_workflow(self, mock_db, mock_dm_client, mock_target, mock_campaign):
        """Test complete campaign workflow from start to finish"""
        # Setup campaign
        campaign = Mock()
        campaign.id = 1
        campaign.status = 'draft'
        campaign.message_template = "Hello {name}, welcome!"
        campaign.daily_limit = 50
        campaign.delay_min = 1  # Short delay for testing
        campaign.delay_max = 2
        campaign.twitter_account = Mock()
        campaign.twitter_account.login_cookie = "test_cookie"
        
        mock_campaign.query.get.return_value = campaign
        
        # Setup targets
        target1 = Mock()
        target1.id = 1
        target1.username = "user1"
        target1.display_name = "User One"
        target1.twitter_user_id = "123"
        target1.status = 'pending'
        target1.can_dm = True
        
        target2 = Mock()
        target2.id = 2
        target2.username = "user2"
        target2.display_name = "User Two"
        target2.twitter_user_id = "456"
        target2.status = 'pending'
        target2.can_dm = True
        
        mock_target.query.filter_by.return_value.filter.return_value.all.return_value = [target1, target2]
        
        # Setup DM client
        dm_client_instance = Mock()
        mock_dm_client.return_value = dm_client_instance
        dm_client_instance.send_dm.return_value = DMSendResult(message_id="msg123", status="sent")
        
        # Run campaign
        result = self.service.start_campaign_sending(1)
        
        # Verify results
        assert result.campaign_id == 1
        assert result.total_targets == 2
        assert result.sent_count == 2
        assert result.failed_count == 0
        assert result.status == "completed"
        
        # Verify campaign status was updated
        assert campaign.status == 'completed'
        assert campaign.messages_sent == 2


if __name__ == '__main__':
    pytest.main([__file__])