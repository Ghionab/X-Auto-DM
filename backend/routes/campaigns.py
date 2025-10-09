from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import logging

from models import db, User, TwitterAccount, Campaign, CampaignTarget, CampaignMessage
from services.campaign_service import CampaignService, CampaignValidationError, CampaignNotFoundError, CampaignPermissionError
from services.target_scraper_service import TargetScraperService
from services.bulk_dm_service import BulkDMService
from services.campaign_analytics_service import CampaignAnalyticsService
from services.csv_upload_service import CSVUploadService

campaigns_bp = Blueprint('campaigns', __name__, url_prefix='/api/campaigns')
logger = logging.getLogger(__name__)

def init_limiter(app_limiter):
    """Initialize rate limiting for campaign routes"""
    pass

@campaigns_bp.route('', methods=['GET'])
@jwt_required()
def get_campaigns():
    """Get all campaigns for the current user"""
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int, default=0)
        
        # Build query
        query = Campaign.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Apply ordering first, then pagination
        query = query.order_by(Campaign.created_at.desc())
        
        # Apply pagination
        if limit:
            query = query.limit(limit)
        query = query.offset(offset)
        
        campaigns = query.all()
        
        return jsonify({
            'success': True,
            'campaigns': [campaign.to_dict() for campaign in campaigns]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('', methods=['POST'])
@jwt_required()
def create_campaign():
    """Create a new campaign"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'target_type', 'message_template', 'sender_account_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate sender account belongs to user
        account = TwitterAccount.query.filter_by(
            id=data['sender_account_id'],
            user_id=user_id
        ).first()
        
        if not account:
            return jsonify({
                'success': False,
                'error': 'Invalid sender account'
            }), 400
        
        # Create campaign using service
        campaign_service = CampaignService()
        campaign = campaign_service.create_campaign(user_id, data)
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict()
        }), 201
        
    except CampaignValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>', methods=['GET'])
@jwt_required()
def get_campaign(campaign_id):
    """Get a specific campaign"""
    try:
        user_id = get_jwt_identity()
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>', methods=['PUT'])
@jwt_required()
def update_campaign(campaign_id):
    """Update a campaign"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        campaign_service = CampaignService()
        campaign = campaign_service.update_campaign(user_id, campaign_id, data)
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict()
        })
        
    except CampaignNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Campaign not found'
        }), 404
    except CampaignPermissionError:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    except CampaignValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>', methods=['DELETE'])
@jwt_required()
def delete_campaign(campaign_id):
    """Delete a campaign"""
    try:
        user_id = get_jwt_identity()
        
        campaign_service = CampaignService()
        campaign_service.delete_campaign(user_id, campaign_id)
        
        return jsonify({
            'success': True,
            'message': 'Campaign deleted successfully'
        })
        
    except CampaignNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Campaign not found'
        }), 404
    except CampaignPermissionError:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/start', methods=['POST'])
@jwt_required()
def start_campaign(campaign_id):
    """Start a campaign"""
    try:
        user_id = get_jwt_identity()
        
        campaign_service = CampaignService()
        result = campaign_service.start_campaign(user_id, campaign_id)
        
        return jsonify({
            'success': True,
            'message': 'Campaign started successfully',
            'target_count': result.get('target_count', 0)
        })
        
    except CampaignNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Campaign not found'
        }), 404
    except CampaignPermissionError:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    except CampaignValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/pause', methods=['POST'])
@jwt_required()
def pause_campaign(campaign_id):
    """Pause a campaign"""
    try:
        user_id = get_jwt_identity()
        
        campaign_service = CampaignService()
        campaign_service.pause_campaign(user_id, campaign_id)
        
        return jsonify({
            'success': True,
            'message': 'Campaign paused successfully'
        })
        
    except CampaignNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Campaign not found'
        }), 404
    except CampaignPermissionError:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/analytics', methods=['GET'])
@jwt_required()
def get_campaign_analytics(campaign_id):
    """Get campaign analytics"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        analytics_service = CampaignAnalyticsService()
        metrics = analytics_service.calculate_campaign_metrics(campaign_id)
        demographics = analytics_service.get_target_demographics(campaign_id)
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict(),
            'metrics': metrics,
            'demographics': demographics
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/upload-csv', methods=['POST'])
@jwt_required()
def upload_csv():
    """Upload CSV file for campaign targets"""
    try:
        user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        campaign_id = request.form.get('campaign_id')
        
        if not campaign_id:
            return jsonify({
                'success': False,
                'error': 'Campaign ID is required'
            }), 400
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=int(campaign_id),
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        csv_service = CSVUploadService()
        result = csv_service.process_csv_upload(file, int(campaign_id))
        
        return jsonify({
            'success': True,
            'targets_added': result.targets_added,
            'total_rows': result.total_rows,
            'errors': result.errors
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/scrape-followers', methods=['POST'])
@jwt_required()
def scrape_followers():
    """Scrape followers for campaign targets"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['campaign_id', 'username']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=data['campaign_id'],
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        scraper_service = TargetScraperService()
        result = scraper_service.scrape_user_followers(
            username=data['username'],
            campaign_id=data['campaign_id'],
            verified_only=data.get('verified_only', False),
            max_followers=data.get('max_followers', 1000)
        )
        
        return jsonify({
            'success': True,
            'total_scraped': result.total_scraped,
            'valid_targets': result.valid_targets,
            'filtered_out': result.filtered_out
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/scrape-list-members', methods=['POST'])
@jwt_required()
def scrape_list_members():
    """Scrape list members for campaign targets"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['campaign_id', 'list_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=data['campaign_id'],
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        scraper_service = TargetScraperService()
        result = scraper_service.scrape_list_members(
            list_id=data['list_id'],
            campaign_id=data['campaign_id']
        )
        
        return jsonify({
            'success': True,
            'total_scraped': result.total_scraped,
            'valid_targets': result.valid_targets,
            'filtered_out': result.filtered_out
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/targets', methods=['GET'])
@jwt_required()
def get_campaign_targets(campaign_id):
    """Get campaign targets with filtering and pagination"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Get query parameters
        status = request.args.get('status')
        verified_only = request.args.get('verified_only', type=bool)
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        
        # Build query
        query = CampaignTarget.query.filter_by(campaign_id=campaign_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if verified_only:
            query = query.filter_by(is_verified=True)
        
        # Apply ordering first, then pagination
        query = query.order_by(CampaignTarget.created_at.desc())
        
        # Apply pagination
        total_count = query.count()
        targets = query.offset(offset).limit(limit).all()
        
        return jsonify({
            'success': True,
            'targets': [target.to_dict() for target in targets],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/status', methods=['GET'])
@jwt_required()
def get_campaign_status(campaign_id):
    """Get real-time campaign status and progress"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Get target status breakdown
        target_stats = db.session.query(
            CampaignTarget.status,
            db.func.count(CampaignTarget.id).label('count')
        ).filter_by(campaign_id=campaign_id).group_by(CampaignTarget.status).all()
        
        status_breakdown = {stat.status: stat.count for stat in target_stats}
        
        # Get message status breakdown
        message_stats = db.session.query(
            CampaignMessage.status,
            db.func.count(CampaignMessage.id).label('count')
        ).filter_by(campaign_id=campaign_id).group_by(CampaignMessage.status).all()
        
        message_breakdown = {stat.status: stat.count for stat in message_stats}
        
        # Calculate progress
        total_targets = campaign.total_targets
        sent_count = status_breakdown.get('sent', 0)
        failed_count = status_breakdown.get('failed', 0)
        pending_count = status_breakdown.get('pending', 0)
        
        progress_percentage = 0
        if total_targets > 0:
            progress_percentage = ((sent_count + failed_count) / total_targets) * 100
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict(),
            'status_breakdown': status_breakdown,
            'message_breakdown': message_breakdown,
            'progress': {
                'percentage': round(progress_percentage, 2),
                'total_targets': total_targets,
                'sent': sent_count,
                'failed': failed_count,
                'pending': pending_count,
                'replies': campaign.replies_received
            },
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/retry-failed', methods=['POST'])
@jwt_required()
def retry_failed_targets(campaign_id):
    """Retry sending to failed targets"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Get failed targets
        failed_targets = CampaignTarget.query.filter_by(
            campaign_id=campaign_id,
            status='failed'
        ).all()
        
        if not failed_targets:
            return jsonify({
                'success': False,
                'error': 'No failed targets to retry'
            }), 400
        
        # Reset failed targets to pending
        for target in failed_targets:
            target.status = 'pending'
            target.error_message = None
        
        db.session.commit()
        
        # Start bulk DM service for retry
        bulk_dm_service = BulkDMService()
        result = bulk_dm_service.start_campaign_sending(campaign_id)
        
        return jsonify({
            'success': True,
            'message': f'Retrying {len(failed_targets)} failed targets',
            'retry_count': len(failed_targets)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_campaigns():
    """Compare multiple campaigns"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        campaign_ids = data.get('campaign_ids', [])
        if not campaign_ids or len(campaign_ids) < 2:
            return jsonify({
                'success': False,
                'error': 'At least 2 campaign IDs are required for comparison'
            }), 400
        
        # Verify all campaigns belong to the user
        campaigns = Campaign.query.filter(
            Campaign.id.in_(campaign_ids),
            Campaign.user_id == user_id
        ).all()
        
        if len(campaigns) != len(campaign_ids):
            return jsonify({
                'success': False,
                'error': 'One or more campaigns not found or access denied'
            }), 404
        
        analytics_service = CampaignAnalyticsService()
        comparison_result = analytics_service.compare_campaigns(campaign_ids)
        
        return jsonify({
            'success': True,
            **comparison_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/export', methods=['GET'])
@jwt_required()
def export_campaign_data(campaign_id):
    """Export campaign data as CSV"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        analytics_service = CampaignAnalyticsService()
        csv_data = analytics_service.export_campaign_data(campaign_id, format='csv')
        
        # Create response with CSV data
        from flask import Response
        response = Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=campaign_{campaign_id}_data.csv'
            }
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/export-comparison', methods=['POST'])
@jwt_required()
def export_campaign_comparison():
    """Export campaign comparison data as CSV"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        campaign_ids = data.get('campaign_ids', [])
        if not campaign_ids:
            return jsonify({
                'success': False,
                'error': 'Campaign IDs are required'
            }), 400
        
        # Verify all campaigns belong to the user
        campaigns = Campaign.query.filter(
            Campaign.id.in_(campaign_ids),
            Campaign.user_id == user_id
        ).all()
        
        if len(campaigns) != len(campaign_ids):
            return jsonify({
                'success': False,
                'error': 'One or more campaigns not found or access denied'
            }), 404
        
        analytics_service = CampaignAnalyticsService()
        comparison_result = analytics_service.compare_campaigns(campaign_ids)
        
        # Convert comparison data to CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'Campaign ID', 'Campaign Name', 'Total Targets', 'Delivery Rate (%)',
            'Response Rate (%)', 'Positive Rate (%)', 'Avg Followers',
            'Verification Rate (%)', 'Duration (hours)', 'Created At'
        ]
        writer.writerow(headers)
        
        # Write data rows
        for campaign_data in comparison_result['campaigns']:
            row = [
                campaign_data['campaign_id'],
                campaign_data['campaign_name'],
                campaign_data['total_targets'],
                campaign_data['delivery_rate'],
                campaign_data['response_rate'],
                campaign_data['positive_rate'],
                campaign_data['avg_followers'],
                campaign_data['verification_rate'],
                campaign_data['campaign_duration_hours'] or 'N/A',
                campaign_data['created_at']
            ]
            writer.writerow(row)
        
        csv_data = output.getvalue()
        
        # Create response with CSV data
        from flask import Response
        response = Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=campaign_comparison_{len(campaign_ids)}_campaigns.csv'
            }
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/<int:campaign_id>/report', methods=['GET'])
@jwt_required()
def get_campaign_report(campaign_id):
    """Get comprehensive campaign report"""
    try:
        user_id = get_jwt_identity()
        
        # Verify campaign ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            user_id=user_id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        analytics_service = CampaignAnalyticsService()
        report = analytics_service.generate_campaign_report(campaign_id)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@campaigns_bp.route('/preview-followers', methods=['POST'])
@jwt_required()
def preview_followers():
    """Preview followers for a username before creating campaign"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        username = data.get('username')
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username is required'
            }), 400
        
        # Remove @ symbol if present
        username = username.lstrip('@')
        
        # Use TwitterAPI client to get user info and follower preview
        from services.twitterapi_client import TwitterAPIClient
        
        api_client = TwitterAPIClient()
        
        # Get user info first
        user_info = api_client.get_user_info(username)
        if not user_info:
            return jsonify({
                'success': False,
                'error': f'User @{username} not found'
            }), 404
        
        # Get follower preview (first 20 followers)
        try:
            followers_generator = api_client.get_user_followers(
                username=username,
                max_followers=20,
                page_size=20
            )
            
            # Get the first page of results
            followers_preview = next(followers_generator, None)
            
            if not followers_preview or not followers_preview.items:
                return jsonify({
                    'success': False,
                    'error': f'Could not retrieve followers for @{username}'
                }), 400
                
        except Exception as e:
            logger.error(f"Error fetching followers for {username}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Could not retrieve followers for @{username}: {str(e)}'
            }), 400
        
        # Format the response
        preview_data = {
            'user_info': {
                'username': user_info.username,
                'display_name': user_info.name,
                'follower_count': user_info.followers_count,
                'following_count': user_info.following_count,
                'is_verified': user_info.is_verified or user_info.is_blue_verified,
                'profile_image_url': user_info.profile_picture or '',
                'description': user_info.description or ''
            },
            'followers_preview': [
                {
                    'username': follower.username,
                    'display_name': follower.name,
                    'follower_count': follower.followers_count,
                    'is_verified': follower.is_verified or follower.is_blue_verified,
                    'profile_image_url': follower.profile_picture or '',
                    'description': (follower.description or '')[:100] + ('...' if len(follower.description or '') > 100 else '')
                }
                for follower in followers_preview.items
            ],
            'total_followers': user_info.followers_count,
            'preview_count': len(followers_preview.items),
            'has_more': followers_preview.has_next_page
        }
        
        return jsonify({
            'success': True,
            **preview_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500