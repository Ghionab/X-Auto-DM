"""
DM Analytics API Routes
Provides endpoints for accessing DM analytics, performance metrics, and error trends
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from ..services.dm_analytics_service import DMAnalyticsService
from ..services.twitter_api_client import TwitterAPIClient
from ..models import User, TwitterAccount, Campaign
import os

# Create blueprint
dm_analytics_bp = Blueprint('dm_analytics', __name__, url_prefix='/api/analytics')

# Initialize services
analytics_service = DMAnalyticsService()

def get_twitter_client():
    """Get TwitterAPIClient instance"""
    api_key = os.getenv('TWITTERAPI_IO_API_KEY')
    if not api_key:
        raise ValueError("TWITTERAPI_IO_API_KEY environment variable not set")
    return TwitterAPIClient(api_key=api_key)

@dm_analytics_bp.route('/dm/overview', methods=['GET'])
@jwt_required()
def get_dm_overview():
    """
    Get DM analytics overview for the authenticated user
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    - campaign_id: Filter by specific campaign ID
    - twitter_account_id: Filter by specific Twitter account ID
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        campaign_id = request.args.get('campaign_id', type=int)
        twitter_account_id = request.args.get('twitter_account_id', type=int)
        
        # Validate days parameter
        if days < 1 or days > 365:
            return jsonify({
                'error': 'Days parameter must be between 1 and 365'
            }), 400
        
        # Validate campaign ownership if campaign_id provided
        if campaign_id:
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({
                    'error': 'Campaign not found or access denied'
                }), 404
        
        # Validate Twitter account ownership if twitter_account_id provided
        if twitter_account_id:
            account = TwitterAccount.query.filter_by(id=twitter_account_id, user_id=user_id).first()
            if not account:
                return jsonify({
                    'error': 'Twitter account not found or access denied'
                }), 404
        
        # Get analytics data
        client = get_twitter_client()
        analytics_data = client.get_dm_analytics(
            user_id=user_id,
            campaign_id=campaign_id,
            twitter_account_id=twitter_account_id,
            days=days
        )
        
        return jsonify({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get DM analytics: {str(e)}'
        }), 500

@dm_analytics_bp.route('/dm/performance', methods=['GET'])
@jwt_required()
def get_dm_performance():
    """
    Get DM performance summary for the last 24 hours
    
    Query Parameters:
    - twitter_account_id: Filter by specific Twitter account ID
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        twitter_account_id = request.args.get('twitter_account_id', type=int)
        
        # Validate Twitter account ownership if provided
        if twitter_account_id:
            account = TwitterAccount.query.filter_by(id=twitter_account_id, user_id=user_id).first()
            if not account:
                return jsonify({
                    'error': 'Twitter account not found or access denied'
                }), 404
        
        # Get performance summary
        client = get_twitter_client()
        performance_data = client.get_performance_summary(
            user_id=user_id,
            twitter_account_id=twitter_account_id
        )
        
        return jsonify({
            'success': True,
            'data': performance_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get performance summary: {str(e)}'
        }), 500

@dm_analytics_bp.route('/errors/trends', methods=['GET'])
@jwt_required()
def get_error_trends():
    """
    Get error trends analysis
    
    Query Parameters:
    - days: Number of days to analyze (default: 7)
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        days = request.args.get('days', 7, type=int)
        
        # Validate days parameter
        if days < 1 or days > 30:
            return jsonify({
                'error': 'Days parameter must be between 1 and 30'
            }), 400
        
        # Get error trends
        client = get_twitter_client()
        trends_data = client.get_error_trends(
            user_id=user_id,
            days=days
        )
        
        return jsonify({
            'success': True,
            'data': trends_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get error trends: {str(e)}'
        }), 500

@dm_analytics_bp.route('/campaigns/<int:campaign_id>/analytics', methods=['GET'])
@jwt_required()
def get_campaign_analytics(campaign_id):
    """
    Get detailed analytics for a specific campaign
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        
        # Validate campaign ownership
        campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
        if not campaign:
            return jsonify({
                'error': 'Campaign not found or access denied'
            }), 404
        
        # Validate days parameter
        if days < 1 or days > 365:
            return jsonify({
                'error': 'Days parameter must be between 1 and 365'
            }), 400
        
        # Get campaign analytics
        client = get_twitter_client()
        analytics_data = client.get_dm_analytics(
            user_id=user_id,
            campaign_id=campaign_id,
            days=days
        )
        
        # Add campaign-specific information
        campaign_info = {
            'id': campaign.id,
            'name': campaign.name,
            'status': campaign.status,
            'total_targets': campaign.total_targets,
            'messages_sent': campaign.messages_sent,
            'created_at': campaign.created_at.isoformat()
        }
        
        return jsonify({
            'success': True,
            'campaign': campaign_info,
            'analytics': analytics_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get campaign analytics: {str(e)}'
        }), 500

@dm_analytics_bp.route('/accounts/<int:account_id>/analytics', methods=['GET'])
@jwt_required()
def get_account_analytics(account_id):
    """
    Get detailed analytics for a specific Twitter account
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        
        # Validate account ownership
        account = TwitterAccount.query.filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return jsonify({
                'error': 'Twitter account not found or access denied'
            }), 404
        
        # Validate days parameter
        if days < 1 or days > 365:
            return jsonify({
                'error': 'Days parameter must be between 1 and 365'
            }), 400
        
        # Get account analytics
        client = get_twitter_client()
        analytics_data = client.get_dm_analytics(
            user_id=user_id,
            twitter_account_id=account_id,
            days=days
        )
        
        # Add account-specific information
        account_info = {
            'id': account.id,
            'username': account.username,
            'display_name': account.display_name,
            'connection_status': account.connection_status,
            'created_at': account.created_at.isoformat()
        }
        
        return jsonify({
            'success': True,
            'account': account_info,
            'analytics': analytics_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get account analytics: {str(e)}'
        }), 500

@dm_analytics_bp.route('/health', methods=['GET'])
@jwt_required()
def get_analytics_health():
    """
    Get overall analytics system health and status
    """
    try:
        user_id = get_jwt_identity()
        
        # Get basic health metrics
        client = get_twitter_client()
        
        # Get performance summary for health check
        performance = client.get_performance_summary(user_id=user_id)
        
        # Get error trends for health assessment
        error_trends = client.get_error_trends(user_id=user_id, days=1)
        
        # Calculate overall health status
        health_status = 'healthy'
        issues = []
        
        if 'error' in performance:
            health_status = 'degraded'
            issues.append('Performance metrics unavailable')
        else:
            health_score = performance.get('health_score', 0)
            if health_score < 50:
                health_status = 'unhealthy'
                issues.append('Low performance score')
            elif health_score < 70:
                health_status = 'degraded'
                issues.append('Performance could be improved')
        
        if 'error' in error_trends:
            issues.append('Error trend analysis unavailable')
        else:
            total_errors = error_trends.get('total_errors', 0)
            if total_errors > 50:
                health_status = 'degraded'
                issues.append('High error rate detected')
        
        return jsonify({
            'success': True,
            'health_status': health_status,
            'issues': issues,
            'performance_summary': performance if 'error' not in performance else None,
            'error_summary': {
                'total_errors_24h': error_trends.get('total_errors', 0) if 'error' not in error_trends else None,
                'recommendations': error_trends.get('recommendations', []) if 'error' not in error_trends else []
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get analytics health: {str(e)}'
        }), 500

@dm_analytics_bp.route('/export', methods=['POST'])
@jwt_required()
def export_analytics():
    """
    Export analytics data in various formats
    
    Request Body:
    {
        "format": "json|csv",
        "type": "dm_overview|error_trends|campaign|account",
        "filters": {
            "days": 30,
            "campaign_id": 123,
            "twitter_account_id": 456
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Request body is required'
            }), 400
        
        export_format = data.get('format', 'json')
        export_type = data.get('type', 'dm_overview')
        filters = data.get('filters', {})
        
        # Validate format
        if export_format not in ['json', 'csv']:
            return jsonify({
                'error': 'Format must be json or csv'
            }), 400
        
        # Validate type
        if export_type not in ['dm_overview', 'error_trends', 'campaign', 'account']:
            return jsonify({
                'error': 'Type must be dm_overview, error_trends, campaign, or account'
            }), 400
        
        # Get analytics data based on type
        client = get_twitter_client()
        
        if export_type == 'dm_overview':
            analytics_data = client.get_dm_analytics(
                user_id=user_id,
                campaign_id=filters.get('campaign_id'),
                twitter_account_id=filters.get('twitter_account_id'),
                days=filters.get('days', 30)
            )
        elif export_type == 'error_trends':
            analytics_data = client.get_error_trends(
                user_id=user_id,
                days=filters.get('days', 7)
            )
        else:
            return jsonify({
                'error': 'Export type not yet implemented'
            }), 501
        
        # Return data in requested format
        if export_format == 'json':
            return jsonify({
                'success': True,
                'data': analytics_data,
                'export_info': {
                    'format': export_format,
                    'type': export_type,
                    'generated_at': datetime.utcnow().isoformat(),
                    'user_id': user_id
                }
            })
        else:
            # CSV export would require additional implementation
            return jsonify({
                'error': 'CSV export not yet implemented'
            }), 501
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to export analytics: {str(e)}'
        }), 500