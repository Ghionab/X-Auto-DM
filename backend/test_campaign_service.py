"""
Unit tests for Campaign Service
Tests CRUD operations, validation, status management, and integration with target scraping.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from models import db, User, TwitterAccount, Campaign, CampaignTarget, CampaignMessage
from services.campaign_service import (
    CampaignService, 
    CampaignValidationError, 
    CampaignNotFoundError, 
    CampaignPermissionError,
    create_campaign_service
)
from services.target_scraper_service import ScrapingResult

class TestCampaignService:
    """Test cases for CampaignService"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def campaign_service(self, app):
        """Create campaign service instance"""
        with app.app_context():
            return CampaignService()
    
    @pytest.fixture
    def test_user(self, app):
        """Create test user"""
        with app.app_context():
            user = User(
                email='test@example.com',
                username='testuser',
                password_hash='hashed_password'
            )
            db.session.add(user)
            db.session.commit()
            return user
    
    @pytest.fixture
    def test_twitter_account(self, app, test_user):
        """Create test Twitter account"""
        with app.app_context():
            account = TwitterAccount(
                user_id=test_user.id,
                username='test_twitter',
                display_name='Test Twitter',
                login_cookie='test_cookie_data',
                connection_status='connected'
            )
            db.session.add(account)
            db.session.commit()
            return account
    
    @pytest.fixture
    def valid_campaign_data(self, test_twitter_account):
        """Valid campaign data for testing"""
        return {
            'name': 'Test Campaign',
            'description': 'Test campaign description',
            'message_template': 'Hello {name}, this is a test message!',
            'target_type': 'user_followers',
            'target_identifier': 'testuser',
            'twitter_account_id': test_twitter_account.id,
            'daily_limit': 50,
            'delay_min': 30,
            'delay_max': 120,
            'personalization_enabled': True,
            'ai_rules': {'tone': 'friendly', 'style': 'casual'}
        }
    
    def test_create_campaign_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful campaign creation"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert campaign.id is not None
        assert campaign.name == 'Test Campaign'
        assert campaign.user_id == test_user.id
        assert campaign.status == 'draft'
        assert campaign.message_template == 'Hello {name}, this is a test message!'
        assert campaign.target_type == 'user_followers'
        assert campaign.target_identifier == 'testuser'
        assert campaign.daily_limit == 50
        assert campaign.personalization_enabled is True
        
        # Check AI rules are stored as JSON
        ai_rules = json.loads(campaign.ai_rules)
        assert ai_rules['tone'] == 'friendly'
        assert ai_rules['style'] == 'casual'
    
    def test_create_campaign_missing_required_fields(self, campaign_service, test_user):
        """Test campaign creation with missing required fields"""
        invalid_data = {
            'name': 'Test Campaign'
            # Missing other required fields
        }
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, invalid_data)
        
        assert 'Missing required field' in str(exc_info.value)
    
    def test_create_campaign_invalid_user(self, campaign_service, valid_campaign_data):
        """Test campaign creation with invalid user ID"""
        with pytest.raises(ValueError) as exc_info:
            campaign_service.create_campaign(999, valid_campaign_data)
        
        assert 'User with ID 999 not found' in str(exc_info.value)
    
    def test_create_campaign_invalid_twitter_account(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign creation with invalid Twitter account"""
        valid_campaign_data['twitter_account_id'] = 999
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Invalid Twitter account' in str(exc_info.value)
    
    def test_create_campaign_unauthenticated_account(self, campaign_service, test_user, valid_campaign_data, app):
        """Test campaign creation with unauthenticated Twitter account"""
        with app.app_context():
            # Create account without login cookie
            account = TwitterAccount(
                user_id=test_user.id,
                username='unauth_twitter',
                display_name='Unauth Twitter',
                login_cookie=None,
                connection_status='disconnected'
            )
            db.session.add(account)
            db.session.commit()
            
            valid_campaign_data['twitter_account_id'] = account.id
            
            with pytest.raises(CampaignValidationError) as exc_info:
                campaign_service.create_campaign(test_user.id, valid_campaign_data)
            
            assert 'not properly authenticated' in str(exc_info.value)
    
    def test_create_campaign_invalid_target_type(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign creation with invalid target type"""
        valid_campaign_data['target_type'] = 'invalid_type'
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Invalid target_type' in str(exc_info.value)
    
    def test_create_campaign_invalid_message_template(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign creation with invalid message template"""
        # Too short
        valid_campaign_data['message_template'] = 'Hi'
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'at least 10 characters' in str(exc_info.value)
        
        # Too long
        valid_campaign_data['message_template'] = 'x' * 10001
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'less than 10,000 characters' in str(exc_info.value)
    
    def test_create_campaign_invalid_daily_limit(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign creation with invalid daily limit"""
        valid_campaign_data['daily_limit'] = 0
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Daily limit must be between 1 and 1000' in str(exc_info.value)
        
        valid_campaign_data['daily_limit'] = 1001
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Daily limit must be between 1 and 1000' in str(exc_info.value)
    
    def test_create_campaign_invalid_delay_settings(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign creation with invalid delay settings"""
        valid_campaign_data['delay_min'] = 0
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Minimum delay must be at least 1 minute' in str(exc_info.value)
        
        valid_campaign_data['delay_min'] = 60
        valid_campaign_data['delay_max'] = 30
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        assert 'Maximum delay must be greater than or equal to minimum delay' in str(exc_info.value)
    
    def test_get_campaigns_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful campaign retrieval"""
        # Create multiple campaigns
        campaign1 = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        valid_campaign_data['name'] = 'Second Campaign'
        campaign2 = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        campaigns = campaign_service.get_campaigns(test_user.id)
        
        assert len(campaigns) == 2
        assert campaigns[0].id == campaign2.id  # Should be ordered by created_at desc
        assert campaigns[1].id == campaign1.id
    
    def test_get_campaigns_with_status_filter(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign retrieval with status filter"""
        campaign1 = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        valid_campaign_data['name'] = 'Second Campaign'
        campaign2 = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        # Update one campaign status
        campaign2.status = 'active'
        db.session.commit()
        
        draft_campaigns = campaign_service.get_campaigns(test_user.id, status='draft')
        active_campaigns = campaign_service.get_campaigns(test_user.id, status='active')
        
        assert len(draft_campaigns) == 1
        assert draft_campaigns[0].id == campaign1.id
        assert len(active_campaigns) == 1
        assert active_campaigns[0].id == campaign2.id
    
    def test_get_campaigns_with_pagination(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign retrieval with pagination"""
        # Create 3 campaigns
        for i in range(3):
            valid_campaign_data['name'] = f'Campaign {i+1}'
            campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        # Test limit
        campaigns = campaign_service.get_campaigns(test_user.id, limit=2)
        assert len(campaigns) == 2
        
        # Test offset
        campaigns = campaign_service.get_campaigns(test_user.id, limit=2, offset=1)
        assert len(campaigns) == 2
    
    def test_get_campaign_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful single campaign retrieval"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        retrieved_campaign = campaign_service.get_campaign(campaign.id, test_user.id)
        
        assert retrieved_campaign.id == campaign.id
        assert retrieved_campaign.name == campaign.name
    
    def test_get_campaign_not_found(self, campaign_service, test_user):
        """Test campaign retrieval with invalid ID"""
        with pytest.raises(CampaignNotFoundError) as exc_info:
            campaign_service.get_campaign(999, test_user.id)
        
        assert 'Campaign with ID 999 not found' in str(exc_info.value)
    
    def test_get_campaign_permission_denied(self, campaign_service, test_user, valid_campaign_data, app):
        """Test campaign retrieval with wrong user"""
        with app.app_context():
            # Create another user
            other_user = User(
                email='other@example.com',
                username='otheruser',
                password_hash='hashed_password'
            )
            db.session.add(other_user)
            db.session.commit()
            
            campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
            
            with pytest.raises(CampaignPermissionError) as exc_info:
                campaign_service.get_campaign(campaign.id, other_user.id)
            
            assert "don't have permission" in str(exc_info.value)
    
    def test_update_campaign_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful campaign update"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        update_data = {
            'name': 'Updated Campaign Name',
            'description': 'Updated description',
            'daily_limit': 75
        }
        
        updated_campaign = campaign_service.update_campaign(campaign.id, test_user.id, update_data)
        
        assert updated_campaign.name == 'Updated Campaign Name'
        assert updated_campaign.description == 'Updated description'
        assert updated_campaign.daily_limit == 75
        assert updated_campaign.updated_at > campaign.created_at
    
    def test_update_campaign_active_restrictions(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign update restrictions for active campaigns"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        campaign.status = 'active'
        db.session.commit()
        
        # Should allow limited updates
        update_data = {'name': 'New Name', 'daily_limit': 75}
        updated_campaign = campaign_service.update_campaign(campaign.id, test_user.id, update_data)
        assert updated_campaign.name == 'New Name'
        
        # Should not allow message template update
        update_data = {'message_template': 'New template'}
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.update_campaign(campaign.id, test_user.id, update_data)
        
        assert "Cannot update 'message_template' for active campaign" in str(exc_info.value)
    
    def test_update_campaign_validation_errors(self, campaign_service, test_user, valid_campaign_data):
        """Test campaign update validation errors"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        # Empty name
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.update_campaign(campaign.id, test_user.id, {'name': ''})
        
        assert 'Campaign name cannot be empty' in str(exc_info.value)
        
        # Invalid daily limit
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.update_campaign(campaign.id, test_user.id, {'daily_limit': 0})
        
        assert 'Daily limit must be between 1 and 1000' in str(exc_info.value)
    
    def test_update_campaign_status_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful campaign status update"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        # Add some targets to allow activation
        campaign.total_targets = 10
        db.session.commit()
        
        updated_campaign = campaign_service.update_campaign_status(campaign.id, test_user.id, 'active')
        
        assert updated_campaign.status == 'active'
        assert updated_campaign.started_at is not None
    
    def test_update_campaign_status_invalid_transitions(self, campaign_service, test_user, valid_campaign_data):
        """Test invalid campaign status transitions"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        campaign.status = 'completed'
        db.session.commit()
        
        # Cannot transition from completed to active
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.update_campaign_status(campaign.id, test_user.id, 'active')
        
        assert "Cannot transition from 'completed' to 'active'" in str(exc_info.value)
    
    def test_update_campaign_status_no_targets(self, campaign_service, test_user, valid_campaign_data):
        """Test activating campaign without targets"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.update_campaign_status(campaign.id, test_user.id, 'active')
        
        assert 'Cannot activate campaign without targets' in str(exc_info.value)
    
    def test_delete_campaign_success(self, campaign_service, test_user, valid_campaign_data):
        """Test successful campaign deletion"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        campaign_id = campaign.id
        
        result = campaign_service.delete_campaign(campaign_id, test_user.id)
        
        assert result is True
        
        # Verify campaign is deleted
        with pytest.raises(CampaignNotFoundError):
            campaign_service.get_campaign(campaign_id, test_user.id)
    
    def test_delete_active_campaign_fails(self, campaign_service, test_user, valid_campaign_data):
        """Test that active campaigns cannot be deleted"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        campaign.status = 'active'
        db.session.commit()
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.delete_campaign(campaign.id, test_user.id)
        
        assert 'Cannot delete active campaign' in str(exc_info.value)
    
    @patch('services.campaign_service.TargetScraperService')
    def test_scrape_campaign_targets_user_followers(self, mock_scraper_class, campaign_service, test_user, valid_campaign_data):
        """Test scraping user followers for campaign"""
        # Setup mock
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_result = ScrapingResult(
            success=True,
            targets_found=100,
            targets_stored=95,
            message="Successfully scraped followers"
        )
        mock_scraper.clear_campaign_targets.return_value = None
        mock_scraper.scrape_user_followers.return_value = mock_result
        
        # Create service with mock
        service = CampaignService()
        campaign = service.create_campaign(test_user.id, valid_campaign_data)
        
        result = service.scrape_campaign_targets(campaign.id, test_user.id, max_targets=100)
        
        assert result.success is True
        assert result.targets_found == 100
        assert result.targets_stored == 95
        mock_scraper.clear_campaign_targets.assert_called_once_with(campaign.id)
        mock_scraper.scrape_user_followers.assert_called_once_with(
            campaign_id=campaign.id,
            username='testuser',
            max_followers=100
        )
    
    @patch('services.campaign_service.TargetScraperService')
    def test_scrape_campaign_targets_list_members(self, mock_scraper_class, campaign_service, test_user, valid_campaign_data):
        """Test scraping list members for campaign"""
        # Setup mock
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_result = ScrapingResult(
            success=True,
            targets_found=50,
            targets_stored=48,
            message="Successfully scraped list members"
        )
        mock_scraper.clear_campaign_targets.return_value = None
        mock_scraper.scrape_list_members.return_value = mock_result
        
        # Update campaign data for list members
        valid_campaign_data['target_type'] = 'list_members'
        valid_campaign_data['target_identifier'] = '123456789'
        
        # Create service with mock
        service = CampaignService()
        campaign = service.create_campaign(test_user.id, valid_campaign_data)
        
        result = service.scrape_campaign_targets(campaign.id, test_user.id, max_targets=50)
        
        assert result.success is True
        assert result.targets_found == 50
        assert result.targets_stored == 48
        mock_scraper.clear_campaign_targets.assert_called_once_with(campaign.id)
        mock_scraper.scrape_list_members.assert_called_once_with(
            campaign_id=campaign.id,
            list_id='123456789',
            max_members=50
        )
    
    def test_scrape_campaign_targets_non_draft_fails(self, campaign_service, test_user, valid_campaign_data):
        """Test that scraping fails for non-draft campaigns"""
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        campaign.status = 'active'
        db.session.commit()
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.scrape_campaign_targets(campaign.id, test_user.id)
        
        assert 'Can only scrape targets for draft campaigns' in str(exc_info.value)
    
    def test_scrape_campaign_targets_unsupported_type(self, campaign_service, test_user, valid_campaign_data):
        """Test scraping with unsupported target type"""
        valid_campaign_data['target_type'] = 'manual_list'
        campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
        
        with pytest.raises(CampaignValidationError) as exc_info:
            campaign_service.scrape_campaign_targets(campaign.id, test_user.id)
        
        assert 'Target scraping not supported for type: manual_list' in str(exc_info.value)
    
    def test_get_campaign_statistics(self, campaign_service, test_user, valid_campaign_data, app):
        """Test getting campaign statistics"""
        with app.app_context():
            campaign = campaign_service.create_campaign(test_user.id, valid_campaign_data)
            
            # Add some test data
            campaign.total_targets = 100
            campaign.messages_sent = 80
            campaign.replies_received = 10
            campaign.positive_replies = 8
            db.session.commit()
            
            # Mock target scraper statistics
            with patch.object(campaign_service.target_scraper, 'get_target_statistics') as mock_stats:
                mock_stats.return_value = {
                    'total_targets': 100,
                    'pending': 20,
                    'sent': 80,
                    'failed': 0
                }
                
                stats = campaign_service.get_campaign_statistics(campaign.id, test_user.id)
                
                assert stats['campaign_info']['id'] == campaign.id
                assert stats['campaign_info']['name'] == campaign.name
                assert stats['campaign_info']['status'] == campaign.status
                assert stats['targets']['total_targets'] == 100
                assert stats['messages']['total_messages'] == 0  # No CampaignMessage records
                assert stats['performance']['delivery_rate'] == 80.0  # 80/100 * 100
                assert stats['performance']['response_rate'] == 12.5  # 10/80 * 100
    
    def test_factory_function(self):
        """Test the factory function creates service instance"""
        service = create_campaign_service()
        assert isinstance(service, CampaignService)
        assert hasattr(service, 'target_scraper')

class TestCampaignServiceIntegration:
    """Integration tests for CampaignService with real database"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with real database"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_campaign_service.db'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_campaign_lifecycle(self, app):
        """Test complete campaign lifecycle"""
        with app.app_context():
            # Create test data
            user = User(
                email='test@example.com',
                username='testuser',
                password_hash='hashed_password'
            )
            db.session.add(user)
            db.session.commit()
            
            account = TwitterAccount(
                user_id=user.id,
                username='test_twitter',
                display_name='Test Twitter',
                login_cookie='test_cookie_data',
                connection_status='connected'
            )
            db.session.add(account)
            db.session.commit()
            
            # Create service
            service = CampaignService()
            
            # Create campaign
            campaign_data = {
                'name': 'Integration Test Campaign',
                'description': 'Test campaign for integration testing',
                'message_template': 'Hello {name}, this is a test message!',
                'target_type': 'user_followers',
                'target_identifier': 'testuser',
                'twitter_account_id': account.id,
                'daily_limit': 50,
                'delay_min': 30,
                'delay_max': 120,
                'personalization_enabled': True
            }
            
            campaign = service.create_campaign(user.id, campaign_data)
            assert campaign.status == 'draft'
            
            # Update campaign
            updated_campaign = service.update_campaign(
                campaign.id, 
                user.id, 
                {'name': 'Updated Integration Test Campaign'}
            )
            assert updated_campaign.name == 'Updated Integration Test Campaign'
            
            # Add targets to allow status change
            campaign.total_targets = 10
            db.session.commit()
            
            # Update status
            active_campaign = service.update_campaign_status(campaign.id, user.id, 'active')
            assert active_campaign.status == 'active'
            assert active_campaign.started_at is not None
            
            # Pause campaign
            paused_campaign = service.update_campaign_status(campaign.id, user.id, 'paused')
            assert paused_campaign.status == 'paused'
            
            # Complete campaign
            completed_campaign = service.update_campaign_status(campaign.id, user.id, 'completed')
            assert completed_campaign.status == 'completed'
            assert completed_campaign.completed_at is not None
            
            # Get statistics
            stats = service.get_campaign_statistics(campaign.id, user.id)
            assert stats['campaign_info']['status'] == 'completed'
            
            # Delete campaign
            result = service.delete_campaign(campaign.id, user.id)
            assert result is True