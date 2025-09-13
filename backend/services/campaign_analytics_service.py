"""
Campaign Analytics Service

This service provides comprehensive analytics and metrics calculation for DM campaigns.
It calculates delivery rates, response rates, engagement metrics, target demographics,
and provides campaign comparison and data export functionality.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, desc


class CampaignAnalyticsService:
    """Service for calculating campaign analytics and metrics"""
    
    def __init__(self):
        from models import db
        self.db = db
    
    def calculate_campaign_metrics(self, campaign_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics for a specific campaign
        
        Args:
            campaign_id: ID of the campaign to analyze
            
        Returns:
            Dict containing campaign metrics including delivery rates, response rates, and engagement
        """
        try:
            from models import db, Campaign, CampaignTarget, CampaignMessage
            
            # Get campaign basic info
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Calculate target metrics
            total_targets = CampaignTarget.query.filter_by(campaign_id=campaign_id).count()
            
            # Calculate message status counts
            message_stats = db.session.query(
                CampaignMessage.status,
                func.count(CampaignMessage.id).label('count')
            ).filter_by(campaign_id=campaign_id).group_by(CampaignMessage.status).all()
            
            status_counts = {status: count for status, count in message_stats}
            
            # Calculate target status counts
            target_stats = db.session.query(
                CampaignTarget.status,
                func.count(CampaignTarget.id).label('count')
            ).filter_by(campaign_id=campaign_id).group_by(CampaignTarget.status).all()
            
            target_status_counts = {status: count for status, count in target_stats}
            
            # Calculate reply sentiment counts
            sentiment_stats = db.session.query(
                CampaignTarget.reply_sentiment,
                func.count(CampaignTarget.id).label('count')
            ).filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.reply_sentiment.isnot(None)
            ).group_by(CampaignTarget.reply_sentiment).all()
            
            sentiment_counts = {sentiment: count for sentiment, count in sentiment_stats}
            
            # Calculate rates
            messages_sent = status_counts.get('sent', 0) + status_counts.get('delivered', 0)
            messages_failed = status_counts.get('failed', 0)
            replies_received = target_status_counts.get('replied', 0)
            
            delivery_rate = (messages_sent / total_targets * 100) if total_targets > 0 else 0
            failure_rate = (messages_failed / total_targets * 100) if total_targets > 0 else 0
            response_rate = (replies_received / messages_sent * 100) if messages_sent > 0 else 0
            
            # Calculate engagement metrics
            positive_replies = sentiment_counts.get('positive', 0)
            negative_replies = sentiment_counts.get('negative', 0)
            neutral_replies = sentiment_counts.get('neutral', 0)
            
            positive_rate = (positive_replies / replies_received * 100) if replies_received > 0 else 0
            negative_rate = (negative_replies / replies_received * 100) if replies_received > 0 else 0
            
            # Calculate time-based metrics
            campaign_duration = None
            if campaign.started_at:
                end_time = campaign.completed_at or datetime.utcnow()
                campaign_duration = (end_time - campaign.started_at).total_seconds() / 3600  # hours
            
            return {
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'campaign_status': campaign.status,
                'total_targets': total_targets,
                'messages_sent': messages_sent,
                'messages_failed': messages_failed,
                'replies_received': replies_received,
                'delivery_rate': round(delivery_rate, 2),
                'failure_rate': round(failure_rate, 2),
                'response_rate': round(response_rate, 2),
                'positive_replies': positive_replies,
                'negative_replies': negative_replies,
                'neutral_replies': neutral_replies,
                'positive_rate': round(positive_rate, 2),
                'negative_rate': round(negative_rate, 2),
                'campaign_duration_hours': round(campaign_duration, 2) if campaign_duration else None,
                'status_breakdown': status_counts,
                'target_status_breakdown': target_status_counts,
                'sentiment_breakdown': sentiment_counts,
                'created_at': campaign.created_at.isoformat(),
                'started_at': campaign.started_at.isoformat() if campaign.started_at else None,
                'completed_at': campaign.completed_at.isoformat() if campaign.completed_at else None
            }
            
        except Exception as e:
            raise Exception(f"Error calculating campaign metrics: {str(e)}")    

    def get_target_demographics(self, campaign_id: int) -> Dict[str, Any]:
        """
        Analyze target demographics for a campaign
        
        Args:
            campaign_id: ID of the campaign to analyze
            
        Returns:
            Dict containing demographic analysis of campaign targets
        """
        try:
            from models import db, CampaignTarget
            
            # Get follower count distribution
            follower_ranges = [
                (0, 100, 'micro'),
                (101, 1000, 'small'),
                (1001, 10000, 'medium'),
                (10001, 100000, 'large'),
                (100001, float('inf'), 'mega')
            ]
            
            follower_distribution = {}
            for min_count, max_count, label in follower_ranges:
                if max_count == float('inf'):
                    count = CampaignTarget.query.filter(
                        CampaignTarget.campaign_id == campaign_id,
                        CampaignTarget.follower_count >= min_count
                    ).count()
                else:
                    count = CampaignTarget.query.filter(
                        CampaignTarget.campaign_id == campaign_id,
                        CampaignTarget.follower_count >= min_count,
                        CampaignTarget.follower_count <= max_count
                    ).count()
                follower_distribution[label] = count
            
            # Get verification status distribution
            verified_count = CampaignTarget.query.filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.is_verified == True
            ).count()
            
            unverified_count = CampaignTarget.query.filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.is_verified == False
            ).count()
            
            # Calculate average metrics
            avg_stats = db.session.query(
                func.avg(CampaignTarget.follower_count).label('avg_followers'),
                func.avg(CampaignTarget.following_count).label('avg_following'),
                func.min(CampaignTarget.follower_count).label('min_followers'),
                func.max(CampaignTarget.follower_count).label('max_followers')
            ).filter(CampaignTarget.campaign_id == campaign_id).first()
            
            # Get DM capability distribution
            can_dm_count = CampaignTarget.query.filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.can_dm == True
            ).count()
            
            cannot_dm_count = CampaignTarget.query.filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.can_dm == False
            ).count()
            
            total_targets = CampaignTarget.query.filter_by(campaign_id=campaign_id).count()
            
            return {
                'campaign_id': campaign_id,
                'total_targets': total_targets,
                'follower_distribution': follower_distribution,
                'verification_status': {
                    'verified': verified_count,
                    'unverified': unverified_count,
                    'verification_rate': round((verified_count / total_targets * 100), 2) if total_targets > 0 else 0
                },
                'dm_capability': {
                    'can_dm': can_dm_count,
                    'cannot_dm': cannot_dm_count,
                    'dm_rate': round((can_dm_count / total_targets * 100), 2) if total_targets > 0 else 0
                },
                'follower_stats': {
                    'average_followers': round(avg_stats.avg_followers, 2) if avg_stats.avg_followers else 0,
                    'average_following': round(avg_stats.avg_following, 2) if avg_stats.avg_following else 0,
                    'min_followers': avg_stats.min_followers or 0,
                    'max_followers': avg_stats.max_followers or 0
                }
            }
            
        except Exception as e:
            raise Exception(f"Error analyzing target demographics: {str(e)}")
    
    def compare_campaigns(self, campaign_ids: List[int]) -> Dict[str, Any]:
        """
        Compare metrics across multiple campaigns
        
        Args:
            campaign_ids: List of campaign IDs to compare
            
        Returns:
            Dict containing comparative analysis of campaigns
        """
        if not campaign_ids:
            raise ValueError("No campaign IDs provided for comparison")
        
        try:
            
            comparison_data = []
            
            for campaign_id in campaign_ids:
                metrics = self.calculate_campaign_metrics(campaign_id)
                demographics = self.get_target_demographics(campaign_id)
                
                comparison_data.append({
                    'campaign_id': campaign_id,
                    'campaign_name': metrics['campaign_name'],
                    'total_targets': metrics['total_targets'],
                    'delivery_rate': metrics['delivery_rate'],
                    'response_rate': metrics['response_rate'],
                    'positive_rate': metrics['positive_rate'],
                    'avg_followers': demographics['follower_stats']['average_followers'],
                    'verification_rate': demographics['verification_status']['verification_rate'],
                    'campaign_duration_hours': metrics['campaign_duration_hours'],
                    'created_at': metrics['created_at']
                })
            
            # Calculate aggregate statistics
            if comparison_data:
                avg_delivery_rate = sum(c['delivery_rate'] for c in comparison_data) / len(comparison_data)
                avg_response_rate = sum(c['response_rate'] for c in comparison_data) / len(comparison_data)
                avg_positive_rate = sum(c['positive_rate'] for c in comparison_data) / len(comparison_data)
                total_targets_all = sum(c['total_targets'] for c in comparison_data)
                
                # Find best and worst performing campaigns
                best_delivery = max(comparison_data, key=lambda x: x['delivery_rate'])
                best_response = max(comparison_data, key=lambda x: x['response_rate'])
                worst_delivery = min(comparison_data, key=lambda x: x['delivery_rate'])
                worst_response = min(comparison_data, key=lambda x: x['response_rate'])
                
                return {
                    'campaigns': comparison_data,
                    'summary': {
                        'total_campaigns': len(comparison_data),
                        'total_targets_all_campaigns': total_targets_all,
                        'average_delivery_rate': round(avg_delivery_rate, 2),
                        'average_response_rate': round(avg_response_rate, 2),
                        'average_positive_rate': round(avg_positive_rate, 2)
                    },
                    'performance_insights': {
                        'best_delivery_campaign': {
                            'id': best_delivery['campaign_id'],
                            'name': best_delivery['campaign_name'],
                            'rate': best_delivery['delivery_rate']
                        },
                        'best_response_campaign': {
                            'id': best_response['campaign_id'],
                            'name': best_response['campaign_name'],
                            'rate': best_response['response_rate']
                        },
                        'worst_delivery_campaign': {
                            'id': worst_delivery['campaign_id'],
                            'name': worst_delivery['campaign_name'],
                            'rate': worst_delivery['delivery_rate']
                        },
                        'worst_response_campaign': {
                            'id': worst_response['campaign_id'],
                            'name': worst_response['campaign_name'],
                            'rate': worst_response['response_rate']
                        }
                    }
                }
            else:
                return {'campaigns': [], 'summary': {}, 'performance_insights': {}}
                
        except Exception as e:
            raise Exception(f"Error comparing campaigns: {str(e)}")
    
    def export_campaign_data(self, campaign_id: int, format: str = 'csv') -> str:
        """
        Export campaign data in specified format
        
        Args:
            campaign_id: ID of the campaign to export
            format: Export format ('csv' currently supported)
            
        Returns:
            String containing the exported data
        """
        if format.lower() != 'csv':
            raise ValueError("Only CSV format is currently supported")
        
        try:
            
            from models import db, Campaign, CampaignTarget, CampaignMessage
            
            # Get campaign data
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Get targets with their message status
            targets_query = db.session.query(
                CampaignTarget,
                CampaignMessage.status.label('message_status'),
                CampaignMessage.sent_at,
                CampaignMessage.error_message.label('message_error')
            ).outerjoin(
                CampaignMessage,
                CampaignTarget.id == CampaignMessage.target_id
            ).filter(CampaignTarget.campaign_id == campaign_id)
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            headers = [
                'Target ID', 'Username', 'Display Name', 'Twitter User ID',
                'Follower Count', 'Following Count', 'Is Verified', 'Can DM',
                'Target Status', 'Message Status', 'Reply Sentiment',
                'Message Sent At', 'Reply Received At', 'Error Message',
                'Created At'
            ]
            writer.writerow(headers)
            
            # Write data rows
            for target, message_status, sent_at, message_error in targets_query:
                row = [
                    target.id,
                    target.username,
                    target.display_name or '',
                    target.twitter_user_id,
                    target.follower_count or 0,
                    target.following_count or 0,
                    target.is_verified,
                    target.can_dm,
                    target.status,
                    message_status or 'no_message',
                    target.reply_sentiment or '',
                    sent_at.isoformat() if sent_at else '',
                    target.reply_received_at.isoformat() if target.reply_received_at else '',
                    message_error or target.error_message or '',
                    target.created_at.isoformat()
                ]
                writer.writerow(row)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Error exporting campaign data: {str(e)}")
    
    def generate_campaign_report(self, campaign_id: int) -> Dict[str, Any]:
        """
        Generate a comprehensive campaign report
        
        Args:
            campaign_id: ID of the campaign to report on
            
        Returns:
            Dict containing comprehensive campaign report
        """
        try:
            from models import db, CampaignTarget, CampaignMessage
            
            metrics = self.calculate_campaign_metrics(campaign_id)
            demographics = self.get_target_demographics(campaign_id)
            
            # Get recent activity (last 7 days of messages)
            recent_activity = db.session.query(
                func.date(CampaignMessage.sent_at).label('date'),
                func.count(CampaignMessage.id).label('messages_sent')
            ).filter(
                CampaignMessage.campaign_id == campaign_id,
                CampaignMessage.sent_at >= datetime.utcnow() - timedelta(days=7),
                CampaignMessage.status == 'sent'
            ).group_by(func.date(CampaignMessage.sent_at)).all()
            
            activity_data = [
                {
                    'date': date.isoformat(),
                    'messages_sent': count
                }
                for date, count in recent_activity
            ]
            
            # Get top performing targets (by follower count)
            top_targets = CampaignTarget.query.filter_by(
                campaign_id=campaign_id
            ).order_by(desc(CampaignTarget.follower_count)).limit(10).all()
            
            top_targets_data = [
                {
                    'username': target.username,
                    'display_name': target.display_name,
                    'follower_count': target.follower_count,
                    'is_verified': target.is_verified,
                    'status': target.status
                }
                for target in top_targets
            ]
            
            # Generate insights and recommendations
            insights = []
            
            if metrics['delivery_rate'] < 70:
                insights.append("Low delivery rate detected. Consider reviewing target quality and account warmup status.")
            
            if metrics['response_rate'] > 10:
                insights.append("High response rate achieved! Consider analyzing successful message templates.")
            
            if demographics['verification_status']['verification_rate'] > 20:
                insights.append("High percentage of verified targets may indicate quality audience selection.")
            
            if metrics['negative_rate'] > 30:
                insights.append("High negative response rate. Consider refining message content and targeting criteria.")
            
            return {
                'campaign_metrics': metrics,
                'target_demographics': demographics,
                'recent_activity': activity_data,
                'top_targets': top_targets_data,
                'insights_and_recommendations': insights,
                'report_generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating campaign report: {str(e)}")