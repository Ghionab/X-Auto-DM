"""
DM Analytics and Logging Service for twitterapi.io integration
Provides comprehensive tracking, monitoring, and analytics for DM operations
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.exc import SQLAlchemyError
try:
    from ..models import db, APICallLog, DirectMessage, Campaign, TwitterAccount, User
except ImportError:
    # For direct execution/testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import db, APICallLog, DirectMessage, Campaign, TwitterAccount, User


class DMAnalyticsService:
    """
    Service for tracking DM delivery, analytics, and logging
    Provides comprehensive monitoring and error categorization
    """
    
    def __init__(self):
        """Initialize DM Analytics Service"""
        self.logger = logging.getLogger(__name__)
        
        # Error categories for classification
        self.error_categories = {
            'authentication': ['authentication', 'login', 'cookie', 'expired', 'unauthorized'],
            'rate_limit': ['rate_limit', 'rate limit', '429', 'too_many', 'limit_exceeded', 'exceeded'],
            'user_error': ['user_not_found', 'user not found', 'blocked', 'private', 'dm_failed', 'permission'],
            'network_error': ['timeout', 'connection', 'proxy', 'network'],
            'api_error': ['server_error', 'server error', '500', '502', '503', '504', 'internal'],
            'validation_error': ['invalid', 'validation', 'format', 'required']
        }
    
    def log_api_call(self, 
                    endpoint: str,
                    method: str,
                    status_code: Optional[int] = None,
                    response_time_ms: Optional[int] = None,
                    success: bool = False,
                    error_message: Optional[str] = None,
                    request_data: Optional[Dict] = None,
                    response_data: Optional[Dict] = None,
                    retry_count: int = 0,
                    proxy_used: Optional[str] = None,
                    user_id: Optional[int] = None,
                    twitter_account_id: Optional[int] = None,
                    campaign_id: Optional[int] = None) -> Optional[int]:
        """
        Log API call details to database for monitoring and analytics
        
        Args:
            endpoint: API endpoint called
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP response status code
            response_time_ms: Response time in milliseconds
            success: Whether the call was successful
            error_message: Error message if call failed
            request_data: Request parameters (sensitive data will be filtered)
            response_data: Response data (sensitive data will be filtered)
            retry_count: Number of retry attempts
            proxy_used: Proxy URL used (credentials will be filtered)
            user_id: User ID associated with the call
            twitter_account_id: Twitter account ID associated with the call
            campaign_id: Campaign ID associated with the call
            
        Returns:
            Log entry ID if successful, None if failed
        """
        try:
            # Categorize error if present
            error_category = None
            if error_message:
                error_category = self._categorize_error(error_message)
            
            # Filter sensitive data from request and response
            filtered_request = self._filter_sensitive_data(request_data) if request_data else None
            filtered_response = self._filter_sensitive_data(response_data) if response_data else None
            
            # Filter proxy credentials
            filtered_proxy = self._filter_proxy_credentials(proxy_used) if proxy_used else None
            
            # Create log entry
            log_entry = APICallLog(
                user_id=user_id,
                twitter_account_id=twitter_account_id,
                campaign_id=campaign_id,
                endpoint=endpoint,
                method=method.upper(),
                status_code=status_code,
                response_time_ms=response_time_ms,
                success=success,
                error_message=error_message,
                error_category=error_category,
                request_data=json.dumps(filtered_request) if filtered_request else None,
                response_data=json.dumps(filtered_response) if filtered_response else None,
                retry_count=retry_count,
                proxy_used=filtered_proxy,
                created_at=datetime.utcnow()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            self.logger.info(f"API call logged: {method} {endpoint} - Status: {status_code}, Success: {success}")
            return log_entry.id
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to log API call: {str(e)}")
            db.session.rollback()
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error logging API call: {str(e)}")
            return None
    
    def log_dm_delivery(self,
                       campaign_id: int,
                       target_username: str,
                       message_content: str,
                       success: bool,
                       twitter_message_id: Optional[str] = None,
                       error_message: Optional[str] = None,
                       response_time_ms: Optional[int] = None,
                       twitter_account_id: Optional[int] = None) -> Optional[int]:
        """
        Log DM delivery attempt with detailed tracking
        
        Args:
            campaign_id: Campaign ID
            target_username: Target user username
            message_content: Message content sent
            success: Whether delivery was successful
            twitter_message_id: Twitter's message ID if successful
            error_message: Error message if delivery failed
            response_time_ms: Response time for the delivery attempt
            twitter_account_id: Twitter account used for sending
            
        Returns:
            DirectMessage record ID if successful, None if failed
        """
        try:
            # Find or create campaign target
            from ..models import CampaignTarget
            target = CampaignTarget.query.filter_by(
                campaign_id=campaign_id,
                username=target_username
            ).first()
            
            if not target:
                self.logger.warning(f"Target {target_username} not found for campaign {campaign_id}")
                return None
            
            # Create DM record
            dm_record = DirectMessage(
                campaign_id=campaign_id,
                target_id=target.id,
                twitter_account_id=twitter_account_id,
                message_type='outbound',
                content=message_content,
                twitter_message_id=twitter_message_id,
                status='sent' if success else 'failed',
                error_message=error_message,
                sent_at=datetime.utcnow() if success else None,
                created_at=datetime.utcnow()
            )
            
            db.session.add(dm_record)
            
            # Update target status
            if success:
                target.status = 'sent'
                target.message_sent_at = datetime.utcnow()
            else:
                target.status = 'failed'
            
            # Update campaign metrics
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                if success:
                    campaign.messages_sent += 1
                campaign.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"DM delivery logged: Campaign {campaign_id}, Target {target_username}, Success: {success}")
            return dm_record.id
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to log DM delivery: {str(e)}")
            db.session.rollback()
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error logging DM delivery: {str(e)}")
            return None
    
    def get_dm_analytics(self, 
                        user_id: Optional[int] = None,
                        campaign_id: Optional[int] = None,
                        twitter_account_id: Optional[int] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive DM analytics and performance metrics
        
        Args:
            user_id: Filter by user ID
            campaign_id: Filter by campaign ID
            twitter_account_id: Filter by Twitter account ID
            start_date: Start date for analytics period
            end_date: End date for analytics period
            
        Returns:
            Analytics data with delivery rates, error analysis, and performance metrics
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Build base query for API call logs
            query = APICallLog.query.filter(
                APICallLog.endpoint.like('%dm%'),
                APICallLog.created_at >= start_date,
                APICallLog.created_at <= end_date
            )
            
            # Apply filters
            if user_id:
                query = query.filter(APICallLog.user_id == user_id)
            if campaign_id:
                query = query.filter(APICallLog.campaign_id == campaign_id)
            if twitter_account_id:
                query = query.filter(APICallLog.twitter_account_id == twitter_account_id)
            
            # Get all DM-related API calls
            api_calls = query.all()
            
            # Calculate basic metrics
            total_calls = len(api_calls)
            successful_calls = len([call for call in api_calls if call.success])
            failed_calls = total_calls - successful_calls
            
            success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Calculate average response time
            response_times = [call.response_time_ms for call in api_calls if call.response_time_ms]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Error analysis
            error_breakdown = {}
            for call in api_calls:
                if not call.success and call.error_category:
                    error_breakdown[call.error_category] = error_breakdown.get(call.error_category, 0) + 1
            
            # Get DM delivery metrics
            dm_query = DirectMessage.query.filter(
                DirectMessage.created_at >= start_date,
                DirectMessage.created_at <= end_date,
                DirectMessage.message_type == 'outbound'
            )
            
            if campaign_id:
                dm_query = dm_query.filter(DirectMessage.campaign_id == campaign_id)
            if twitter_account_id:
                dm_query = dm_query.filter(DirectMessage.twitter_account_id == twitter_account_id)
            
            dm_records = dm_query.all()
            
            # DM delivery metrics
            total_dms = len(dm_records)
            sent_dms = len([dm for dm in dm_records if dm.status == 'sent'])
            failed_dms = len([dm for dm in dm_records if dm.status == 'failed'])
            
            dm_success_rate = (sent_dms / total_dms * 100) if total_dms > 0 else 0
            
            # Daily breakdown
            daily_stats = {}
            for call in api_calls:
                date_key = call.created_at.date().isoformat()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {'total': 0, 'successful': 0, 'failed': 0}
                
                daily_stats[date_key]['total'] += 1
                if call.success:
                    daily_stats[date_key]['successful'] += 1
                else:
                    daily_stats[date_key]['failed'] += 1
            
            # Retry analysis
            retry_stats = {}
            for call in api_calls:
                retry_count = call.retry_count or 0
                retry_stats[retry_count] = retry_stats.get(retry_count, 0) + 1
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                },
                'api_metrics': {
                    'total_calls': total_calls,
                    'successful_calls': successful_calls,
                    'failed_calls': failed_calls,
                    'success_rate': round(success_rate, 2),
                    'average_response_time_ms': round(avg_response_time, 2)
                },
                'dm_metrics': {
                    'total_dms_attempted': total_dms,
                    'dms_sent': sent_dms,
                    'dms_failed': failed_dms,
                    'dm_success_rate': round(dm_success_rate, 2)
                },
                'error_analysis': error_breakdown,
                'daily_breakdown': daily_stats,
                'retry_analysis': retry_stats,
                'filters_applied': {
                    'user_id': user_id,
                    'campaign_id': campaign_id,
                    'twitter_account_id': twitter_account_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate DM analytics: {str(e)}")
            return {
                'error': f'Failed to generate analytics: {str(e)}',
                'period': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            }
    
    def get_error_trends(self, 
                        user_id: Optional[int] = None,
                        days: int = 7) -> Dict[str, Any]:
        """
        Analyze error trends over time for proactive monitoring
        
        Args:
            user_id: Filter by user ID
            days: Number of days to analyze
            
        Returns:
            Error trend analysis with recommendations
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = APICallLog.query.filter(
                APICallLog.created_at >= start_date,
                APICallLog.success == False
            )
            
            if user_id:
                query = query.filter(APICallLog.user_id == user_id)
            
            error_logs = query.all()
            
            # Analyze trends by day and error category
            daily_errors = {}
            category_trends = {}
            
            for log in error_logs:
                date_key = log.created_at.date().isoformat()
                category = log.error_category or 'unknown'
                
                # Daily error counts
                if date_key not in daily_errors:
                    daily_errors[date_key] = 0
                daily_errors[date_key] += 1
                
                # Category trends
                if category not in category_trends:
                    category_trends[category] = {}
                if date_key not in category_trends[category]:
                    category_trends[category][date_key] = 0
                category_trends[category][date_key] += 1
            
            # Generate recommendations
            recommendations = []
            
            # Check for authentication issues
            auth_errors = sum([count for date, count in category_trends.get('authentication', {}).items()])
            if auth_errors > 5:
                recommendations.append({
                    'type': 'authentication',
                    'message': 'High number of authentication errors detected. Consider refreshing login cookies.',
                    'priority': 'high'
                })
            
            # Check for rate limiting
            rate_limit_errors = sum([count for date, count in category_trends.get('rate_limit', {}).items()])
            if rate_limit_errors > 10:
                recommendations.append({
                    'type': 'rate_limit',
                    'message': 'Frequent rate limiting detected. Consider reducing request frequency or using multiple accounts.',
                    'priority': 'medium'
                })
            
            # Check for user errors
            user_errors = sum([count for date, count in category_trends.get('user_error', {}).items()])
            if user_errors > 20:
                recommendations.append({
                    'type': 'user_error',
                    'message': 'High number of user-related errors. Review target user lists for invalid accounts.',
                    'priority': 'medium'
                })
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'daily_error_counts': daily_errors,
                'category_trends': category_trends,
                'total_errors': len(error_logs),
                'recommendations': recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze error trends: {str(e)}")
            return {'error': f'Failed to analyze error trends: {str(e)}'}
    
    def _categorize_error(self, error_message: str) -> str:
        """
        Categorize error message into predefined categories
        
        Args:
            error_message: Error message to categorize
            
        Returns:
            Error category string
        """
        if not error_message:
            return 'unknown'
        
        error_lower = error_message.lower()
        
        for category, keywords in self.error_categories.items():
            if any(keyword in error_lower for keyword in keywords):
                return category
        
        return 'unknown'
    
    def _filter_sensitive_data(self, data: Dict) -> Dict:
        """
        Filter sensitive data from request/response data before logging
        
        Args:
            data: Data dictionary to filter
            
        Returns:
            Filtered data dictionary
        """
        if not isinstance(data, dict):
            return data
        
        sensitive_keys = [
            'login_cookies', 'password', 'totp_secret', 'access_token',
            'oauth_token', 'oauth_token_secret', 'api_key', 'secret'
        ]
        
        filtered = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered[key] = '[FILTERED]'
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            else:
                filtered[key] = value
        
        return filtered
    
    def _filter_proxy_credentials(self, proxy_url: str) -> str:
        """
        Filter credentials from proxy URL for logging
        
        Args:
            proxy_url: Proxy URL with potential credentials
            
        Returns:
            Filtered proxy URL
        """
        if not proxy_url:
            return proxy_url
        
        # Remove credentials from proxy URL (format: http://user:pass@host:port)
        import re
        pattern = r'(https?://)([^:]+):([^@]+)@(.+)'
        match = re.match(pattern, proxy_url)
        
        if match:
            protocol, user, password, host_port = match.groups()
            return f"{protocol}[USER]:[PASS]@{host_port}"
        
        return proxy_url


class RetryHandler:
    """
    Enhanced retry handler with exponential backoff and comprehensive logging
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 analytics_service: Optional[DMAnalyticsService] = None):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            analytics_service: Analytics service for logging retry attempts
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.analytics_service = analytics_service or DMAnalyticsService()
        self.logger = logging.getLogger(__name__)
    
    def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry logic and comprehensive logging
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            attempt_start = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful execution if there were previous failures
                if attempt > 0:
                    total_time = int((time.time() - start_time) * 1000)
                    self.logger.info(f"Function succeeded on attempt {attempt + 1} after {total_time}ms")
                
                return result
                
            except Exception as e:
                last_exception = e
                attempt_time = int((time.time() - attempt_start) * 1000)
                
                # Log the retry attempt
                self.logger.warning(f"Attempt {attempt + 1} failed after {attempt_time}ms: {str(e)}")
                
                # Don't retry for certain types of errors
                if self._is_non_retryable_error(e):
                    self.logger.error(f"Non-retryable error encountered: {str(e)}")
                    break
                
                # If this was the last attempt, don't wait
                if attempt == self.max_retries:
                    total_time = int((time.time() - start_time) * 1000)
                    self.logger.error(f"All {self.max_retries + 1} attempts failed after {total_time}ms")
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)
                self.logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # Log final failure
        total_time = int((time.time() - start_time) * 1000)
        self.logger.error(f"Function failed after {self.max_retries + 1} attempts and {total_time}ms")
        
        raise last_exception
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error should not be retried
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should not be retried
        """
        error_str = str(error).lower()
        
        # Don't retry validation errors, authentication errors (except expired), or user errors
        non_retryable_patterns = [
            'invalid', 'validation', 'required', 'format',
            'user_not_found', 'blocked', 'private', 'permission',
            'unauthorized', 'forbidden'
        ]
        
        return any(pattern in error_str for pattern in non_retryable_patterns)
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        import random
        
        # Exponential backoff: base_delay * (2 ^ attempt)
        exponential_delay = self.base_delay * (2 ** attempt)
        
        # Add jitter (±25% of the delay)
        jitter = exponential_delay * 0.25 * (2 * random.random() - 1)
        
        # Ensure minimum delay and cap maximum delay
        delay = max(0.1, exponential_delay + jitter)
        return min(delay, 60.0)  # Cap at 60 seconds