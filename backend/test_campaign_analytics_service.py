"""
Unit tests for Campaign Analytics Service

Tests all analytics calculations, demographic analysis, campaign comparison,
and data export functionality.
"""

import pytest
import csv
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from services.campaign_analytics_service import CampaignAnalyticsService
from models import (
    db, Campaign, CampaignTarget, CampaignMessage, DirectMessage,
    TwitterAccount, User
)


class TestCampaignAnalyticsService:
    """Test suite for CampaignAnalyticsService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analytics_service = CampaignAnalyticsService()
        
        # Mock database session
        self.mock_session = Mock()
        
        # Sample campaign data
        self.sample_campaign = Mock()
        self.sample_campaign.id = 1
        self.sample_campaign.name = "Test Campaign"
        self.sample_campaign.status = "completed"
        self.sample_campaign.created_at = datetime(2024, 1, 1, 10, 0, 0)
        self.sample_campaign.started_at = datetime(2024, 1, 1, 11, 0, 0)
        self.sample_campaign.completed_at = datetime(2024, 1, 1, 15, 0, 0)
    
    @patch('models.db')
    @patch('models.Campaign')
    @patch('models.CampaignTarget')
    @patch('models.CampaignMessage')
    def test_calculate_campaign_metrics_success(self, mock_campaign_message, mock_campaign_target, mock_campaign, mock_db):
        """Test successful campaign metrics calculation"""
        # Mock Campaign.query.get
        mock_campaign.query.get.return_value = self.sample_campaign
        
        # Mock target count
        mock_campaign_target.query.filter_by.return_value.count.return_value = 100
        
        # Mock database session queries
        mock_db.session.query.return_value.filter_by.return_value.group_by.return_value.all.side_effect = [
            [('sent', 80), ('failed', 10), ('pending', 10)],  # message stats
            [('sent', 75), ('replied', 15), ('failed', 10)],  # target stats
            [('positive', 10), ('negative', 3), ('neutral', 2)]  # sentiment stats
        ]
        
        result = self.analytics_service.calculate_campaign_metrics(1)
        
        # Verify calculations
        assert result['campaign_id'] == 1
        assert result['campaign_name'] == "Test Campaign"
        assert result['total_targets'] == 100
        assert result['messages_sent'] == 80
        assert result['messages_failed'] == 10
        assert result['replies_received'] == 15
        assert result['delivery_rate'] == 80.0  # 80/100 * 100
        assert result['failure_rate'] == 10.0   # 10/100 * 100
        assert result['response_rate'] == 18.75  # 15/80 * 100
        assert result['positive_replies'] == 10
        assert result['negative_replies'] == 3
        assert result['positive_rate'] == 66.67  # 10/15 * 100
        assert result['campaign_duration_hours'] == 4.0  # 4 hours between start and end
    
    @patch('services.campaign_analytics_service.Campaign')
    def test_calculate_campaign_metrics_campaign_not_found(self, mock_campaign):
        """Test campaign metrics calculation when campaign doesn't exist"""
        mock_campaign.query.get.return_value = None
        
        with pytest.raises(ValueError, match="Campaign 999 not found"):
            self.analytics_service.calculate_campaign_metrics(999)
    
    @patch('services.campaign_analytics_service.CampaignTarget')
    def test_get_target_demographics_success(self, mock_campaign_target):
        """Test successful target demographics analysis"""
        # Mock follower distribution queries
        mock_query = Mock()
        mock_campaign_target.query.filter.return_value = mock_query
        mock_query.count.side_effect = [20, 30, 25, 15, 10]  # follower ranges
        
        # Mock verification status queries
        mock_campaign_target.query.filter.return_value.count.side_effect = [25, 75]  # verified, unverified
        
        # Mock DM capability queries  
        mock_campaign_target.query.filter.return_value.count.side_effect = [90, 10]  # can_dm, cannot_dm
        
        # Mock total targets
        mock_campaign_target.query.filter_by.return_value.count.return_value = 100
        
        # Mock average stats
        mock_avg_stats = Mock()
        mock_avg_stats.avg_followers = 5000.0
        mock_avg_stats.avg_following = 1500.0
        mock_avg_stats.min_followers = 50
        mock_avg_stats.max_followers = 50000
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_avg_stats
        
        result = self.analytics_service.get_target_demographics(1)
        
        assert result['campaign_id'] == 1
        assert result['total_targets'] == 100
        assert result['verification_status']['verified'] == 25
        assert result['verification_status']['verification_rate'] == 25.0
        assert result['dm_capability']['can_dm'] == 90
        assert result['dm_capability']['dm_rate'] == 90.0
        assert result['follower_stats']['average_followers'] == 5000.0
        assert result['follower_stats']['min_followers'] == 50
        assert result['follower_stats']['max_followers'] == 50000
    
    def test_compare_campaigns_success(self):
        """Test successful campaign comparison"""
        # Mock calculate_campaign_metrics and get_target_demographics
        with patch.object(self.analytics_service, 'calculate_campaign_metrics') as mock_metrics, \
             patch.object(self.analytics_service, 'get_target_demographics') as mock_demographics:
            
            # Mock metrics for two campaigns
            mock_metrics.side_effect = [
                {
                    'campaign_id': 1,
                    'campaign_name': 'Campaign 1',
                    'total_targets': 100,
                    'delivery_rate': 85.0,
                    'response_rate': 15.0,
                    'positive_rate': 70.0,
                    'campaign_duration_hours': 4.0,
                    'created_at': '2024-01-01T10:00:00'
                },
                {
                    'campaign_id': 2,
                    'campaign_name': 'Campaign 2',
                    'total_targets': 150,
                    'delivery_rate': 90.0,
                    'response_rate': 12.0,
                    'positive_rate': 80.0,
                    'campaign_duration_hours': 6.0,
                    'created_at': '2024-01-02T10:00:00'
                }
            ]
            
            # Mock demographics
            mock_demographics.side_effect = [
                {
                    'follower_stats': {'average_followers': 5000.0},
                    'verification_status': {'verification_rate': 25.0}
                },
                {
                    'follower_stats': {'average_followers': 7500.0},
                    'verification_status': {'verification_rate': 30.0}
                }
            ]
            
            result = self.analytics_service.compare_campaigns([1, 2])
            
            assert len(result['campaigns']) == 2
            assert result['summary']['total_campaigns'] == 2
            assert result['summary']['total_targets_all_campaigns'] == 250
            assert result['summary']['average_delivery_rate'] == 87.5  # (85+90)/2
            assert result['summary']['average_response_rate'] == 13.5   # (15+12)/2
            
            # Check performance insights
            assert result['performance_insights']['best_delivery_campaign']['id'] == 2
            assert result['performance_insights']['best_response_campaign']['id'] == 1
    
    def test_compare_campaigns_empty_list(self):
        """Test campaign comparison with empty campaign list"""
        with pytest.raises(ValueError, match="No campaign IDs provided for comparison"):
            self.analytics_service.compare_campaigns([])
    
    @patch('services.campaign_analytics_service.Campaign')
    @patch('services.campaign_analytics_service.CampaignTarget')
    @patch('services.campaign_analytics_service.CampaignMessage')
    def test_export_campaign_data_csv_success(self, mock_campaign_message, mock_campaign_target, mock_campaign):
        """Test successful CSV export of campaign data"""
        # Mock campaign
        mock_campaign.query.get.return_value = self.sample_campaign
        
        # Mock targets with message data
        mock_target1 = Mock()
        mock_target1.id = 1
        mock_target1.username = "user1"
        mock_target1.display_name = "User One"
        mock_target1.twitter_user_id = "123456"
        mock_target1.follower_count = 1000
        mock_target1.following_count = 500
        mock_target1.is_verified = True
        mock_target1.can_dm = True
        mock_target1.status = "sent"
        mock_target1.reply_sentiment = "positive"
        mock_target1.reply_received_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_target1.error_message = None
        mock_target1.created_at = datetime(2024, 1, 1, 10, 0, 0)
        
        mock_query_result = [(mock_target1, 'sent', datetime(2024, 1, 1, 11, 30, 0), None)]
        self.mock_session.query.return_value.outerjoin.return_value.filter.return_value = mock_query_result
        
        result = self.analytics_service.export_campaign_data(1, 'csv')
        
        # Parse CSV to verify content
        csv_reader = csv.reader(io.StringIO(result))
        rows = list(csv_reader)
        
        # Check header
        expected_headers = [
            'Target ID', 'Username', 'Display Name', 'Twitter User ID',
            'Follower Count', 'Following Count', 'Is Verified', 'Can DM',
            'Target Status', 'Message Status', 'Reply Sentiment',
            'Message Sent At', 'Reply Received At', 'Error Message',
            'Created At'
        ]
        assert rows[0] == expected_headers
        
        # Check data row
        data_row = rows[1]
        assert data_row[0] == '1'  # Target ID
        assert data_row[1] == 'user1'  # Username
        assert data_row[2] == 'User One'  # Display Name
        assert data_row[4] == '1000'  # Follower Count
        assert data_row[6] == 'True'  # Is Verified
        assert data_row[8] == 'sent'  # Target Status
        assert data_row[9] == 'sent'  # Message Status
    
    @patch('services.campaign_analytics_service.Campaign')
    def test_export_campaign_data_campaign_not_found(self, mock_campaign):
        """Test CSV export when campaign doesn't exist"""
        mock_campaign.query.get.return_value = None
        
        with pytest.raises(ValueError, match="Campaign 999 not found"):
            self.analytics_service.export_campaign_data(999, 'csv')
    
    def test_export_campaign_data_unsupported_format(self):
        """Test export with unsupported format"""
        with pytest.raises(ValueError, match="Only CSV format is currently supported"):
            self.analytics_service.export_campaign_data(1, 'json')
    
    def test_generate_campaign_report_success(self):
        """Test successful campaign report generation"""
        # Mock the dependent methods
        with patch.object(self.analytics_service, 'calculate_campaign_metrics') as mock_metrics, \
             patch.object(self.analytics_service, 'get_target_demographics') as mock_demographics:
            
            mock_metrics.return_value = {
                'campaign_id': 1,
                'delivery_rate': 85.0,
                'response_rate': 15.0,
                'negative_rate': 20.0
            }
            
            mock_demographics.return_value = {
                'verification_status': {'verification_rate': 25.0}
            }
            
            # Mock recent activity query
            mock_activity = [(datetime(2024, 1, 1).date(), 50), (datetime(2024, 1, 2).date(), 30)]
            self.mock_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_activity
            
            # Mock top targets query
            mock_target = Mock()
            mock_target.username = "topuser"
            mock_target.display_name = "Top User"
            mock_target.follower_count = 10000
            mock_target.is_verified = True
            mock_target.status = "sent"
            
            with patch('services.campaign_analytics_service.CampaignTarget') as mock_campaign_target:
                mock_campaign_target.query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_target]
                
                result = self.analytics_service.generate_campaign_report(1)
                
                assert 'campaign_metrics' in result
                assert 'target_demographics' in result
                assert 'recent_activity' in result
                assert 'top_targets' in result
                assert 'insights_and_recommendations' in result
                assert 'report_generated_at' in result
                
                # Check activity data
                assert len(result['recent_activity']) == 2
                assert result['recent_activity'][0]['messages_sent'] == 50
                
                # Check top targets
                assert len(result['top_targets']) == 1
                assert result['top_targets'][0]['username'] == "topuser"
                
                # Check insights (should include high verification rate insight)
                insights = result['insights_and_recommendations']
                assert any("quality audience" in insight for insight in insights)
    
    def test_calculate_campaign_metrics_zero_division_handling(self):
        """Test metrics calculation handles zero division gracefully"""
        with patch('services.campaign_analytics_service.Campaign') as mock_campaign, \
             patch('services.campaign_analytics_service.CampaignTarget') as mock_campaign_target:
            
            mock_campaign.query.get.return_value = self.sample_campaign
            mock_campaign_target.query.filter_by.return_value.count.return_value = 0
            
            # Mock empty stats
            self.mock_session.query.return_value.filter_by.return_value.group_by.return_value.all.side_effect = [
                [],  # message stats
                [],  # target stats  
                []   # sentiment stats
            ]
            
            result = self.analytics_service.calculate_campaign_metrics(1)
            
            # Should handle zero division gracefully
            assert result['delivery_rate'] == 0
            assert result['response_rate'] == 0
            assert result['positive_rate'] == 0
    
    def test_get_target_demographics_edge_cases(self):
        """Test demographics analysis with edge cases"""
        with patch('backend.services.campaign_analytics_service.CampaignTarget') as mock_campaign_target:
            
            # Mock zero targets
            mock_campaign_target.query.filter_by.return_value.count.return_value = 0
            mock_campaign_target.query.filter.return_value.count.return_value = 0
            
            # Mock null average stats
            mock_avg_stats = Mock()
            mock_avg_stats.avg_followers = None
            mock_avg_stats.avg_following = None
            mock_avg_stats.min_followers = None
            mock_avg_stats.max_followers = None
            self.mock_session.query.return_value.filter.return_value.first.return_value = mock_avg_stats
            
            result = self.analytics_service.get_target_demographics(1)
            
            # Should handle null values gracefully
            assert result['verification_status']['verification_rate'] == 0
            assert result['dm_capability']['dm_rate'] == 0
            assert result['follower_stats']['average_followers'] == 0
            assert result['follower_stats']['min_followers'] == 0
    
    def test_error_handling_in_methods(self):
        """Test error handling in all methods"""
        # Test calculate_campaign_metrics error
        with patch('services.campaign_analytics_service.Campaign') as mock_campaign:
            mock_campaign.query.get.side_effect = Exception("Database error")
            
            with pytest.raises(Exception, match="Error calculating campaign metrics"):
                self.analytics_service.calculate_campaign_metrics(1)
        
        # Test get_target_demographics error
        with patch('services.campaign_analytics_service.CampaignTarget') as mock_campaign_target:
            mock_campaign_target.query.filter.side_effect = Exception("Database error")
            
            with pytest.raises(Exception, match="Error analyzing target demographics"):
                self.analytics_service.get_target_demographics(1)
        
        # Test compare_campaigns error
        with patch.object(self.analytics_service, 'calculate_campaign_metrics') as mock_metrics:
            mock_metrics.side_effect = Exception("Metrics error")
            
            with pytest.raises(Exception, match="Error comparing campaigns"):
                self.analytics_service.compare_campaigns([1, 2])
        
        # Test export_campaign_data error
        with patch('services.campaign_analytics_service.Campaign') as mock_campaign:
            mock_campaign.query.get.side_effect = Exception("Database error")
            
            with pytest.raises(Exception, match="Error exporting campaign data"):
                self.analytics_service.export_campaign_data(1)
        
        # Test generate_campaign_report error
        with patch.object(self.analytics_service, 'calculate_campaign_metrics') as mock_metrics:
            mock_metrics.side_effect = Exception("Metrics error")
            
            with pytest.raises(Exception, match="Error generating campaign report"):
                self.analytics_service.generate_campaign_report(1)


if __name__ == '__main__':
    pytest.main([__file__])