from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)
    subscription_plan = db.Column(db.String(50), default='free')  # free, basic, pro, enterprise
    stripe_customer_id = db.Column(db.String(100))
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    twitter_accounts = db.relationship('TwitterAccount', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    campaigns = db.relationship('Campaign', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'is_active': self.is_active,
            'is_premium': self.is_premium,
            'subscription_plan': self.subscription_plan,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TwitterAccount(db.Model):
    """Twitter account model for connecting user's X accounts"""
    __tablename__ = 'twitter_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100))
    profile_image_url = db.Column(db.String(500))
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    warmup_status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    warmup_started_at = db.Column(db.DateTime)
    oauth_tokens_id = db.Column(db.Integer, db.ForeignKey('x_oauth_tokens.id'))
    connection_status = db.Column(db.String(20), default='pending')  # pending, connected, expired, revoked
    login_cookie = db.Column(db.Text)  # TwitterAPI.io login cookie for authentication
    twitter_user_id = db.Column(db.String(50))  # Twitter user ID from API
    screen_name = db.Column(db.String(50))  # Twitter screen name
    name = db.Column(db.String(100))  # Display name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.screen_name or self.username,
            'display_name': self.name or self.display_name,
            'profile_image_url': self.profile_image_url,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'warmup_status': self.warmup_status,
            'connection_status': self.connection_status,
            'created_at': self.created_at.isoformat()
        }

class XOAuthTokens(db.Model):
    """X OAuth tokens model for secure token storage"""
    __tablename__ = 'x_oauth_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'))
    access_token_encrypted = db.Column(db.Text, nullable=False)
    access_token_secret_encrypted = db.Column(db.Text, nullable=False)
    twitter_user_id = db.Column(db.String(50))  # X user ID
    screen_name = db.Column(db.String(50))  # X username
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # For future token expiration handling
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='oauth_tokens')
    twitter_account = db.relationship('TwitterAccount', foreign_keys=[twitter_account_id], backref='oauth_tokens')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'twitter_account_id': self.twitter_account_id,
            'twitter_user_id': self.twitter_user_id,
            'screen_name': self.screen_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class Campaign(db.Model):
    """DM Campaign model"""
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Target Configuration
    target_type = db.Column(db.String(50), nullable=False)  # user_followers, list_members, manual_list, csv_upload
    target_identifier = db.Column(db.String(255), nullable=False)  # username or list_id
    
    # Message Configuration
    message_template = db.Column(db.Text, nullable=False)
    personalization_enabled = db.Column(db.Boolean, default=True)
    ai_rules = db.Column(db.Text)  # JSON string of AI rules and instructions
    preview_message = db.Column(db.Text)
    
    # Campaign Settings
    daily_limit = db.Column(db.Integer, default=50)
    delay_min = db.Column(db.Integer, default=30)  # Minutes between messages
    delay_max = db.Column(db.Integer, default=120)
    status = db.Column(db.String(20), default='draft', index=True)  # draft, active, paused, completed, failed
    
    # Campaign metrics
    total_targets = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    replies_received = db.Column(db.Integer, default=0)
    positive_replies = db.Column(db.Integer, default=0)
    negative_replies = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    twitter_account = db.relationship('TwitterAccount', backref='campaigns')
    targets = db.relationship('CampaignTarget', backref='campaign', cascade='all, delete-orphan')
    messages = db.relationship('DirectMessage', backref='campaign', cascade='all, delete-orphan')
    campaign_messages = db.relationship('CampaignMessage', backref='campaign', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'target_type': self.target_type,
            'target_identifier': self.target_identifier,
            'ai_rules': json.loads(self.ai_rules) if self.ai_rules else {},
            'message_template': self.message_template,
            'personalization_enabled': self.personalization_enabled,
            'total_targets': self.total_targets,
            'messages_sent': self.messages_sent,
            'replies_received': self.replies_received,
            'positive_replies': self.positive_replies,
            'negative_replies': self.negative_replies,
            'daily_limit': self.daily_limit,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class CampaignTarget(db.Model):
    """Target users for campaigns"""
    __tablename__ = 'campaign_targets'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    
    # Target User Data
    twitter_user_id = db.Column(db.String(50), nullable=True, index=True)  # May be null for CSV uploads until enriched
    username = db.Column(db.String(255), nullable=False, index=True)
    display_name = db.Column(db.String(255))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(500))
    follower_count = db.Column(db.Integer, index=True)
    following_count = db.Column(db.Integer)
    is_verified = db.Column(db.Boolean, default=False, index=True)
    can_dm = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.String(50))  # Additional user_id field for enhanced tracking
    profile_data = db.Column(db.JSON)  # Store complete profile data from TwitterAPI.io
    notes = db.Column(db.Text)  # For CSV upload notes column
    source = db.Column(db.String(20), default='scraped')  # scraped, csv_upload
    
    # Processing Status
    status = db.Column(db.String(20), default='pending', index=True)  # pending, sent, failed, replied
    error_message = db.Column(db.Text)
    message_sent_at = db.Column(db.DateTime)
    reply_received_at = db.Column(db.DateTime)
    reply_sentiment = db.Column(db.String(20))  # positive, negative, neutral
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'twitter_user_id': self.twitter_user_id,
            'username': self.username,
            'display_name': self.display_name,
            'bio': self.bio,
            'profile_picture': self.profile_picture,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'is_verified': self.is_verified,
            'can_dm': self.can_dm,
            'user_id': self.user_id,
            'profile_data': self.profile_data,
            'notes': self.notes,
            'source': self.source,
            'status': self.status,
            'error_message': self.error_message,
            'message_sent_at': self.message_sent_at.isoformat() if self.message_sent_at else None,
            'reply_received_at': self.reply_received_at.isoformat() if self.reply_received_at else None,
            'reply_sentiment': self.reply_sentiment,
            'created_at': self.created_at.isoformat()
        }

class CampaignMessage(db.Model):
    """Campaign message tracking model"""
    __tablename__ = 'campaign_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    target_id = db.Column(db.Integer, db.ForeignKey('campaign_targets.id'), nullable=False, index=True)
    
    # Message Data
    message_content = db.Column(db.Text, nullable=False)
    twitter_message_id = db.Column(db.String(50), index=True)
    
    # Status Tracking
    status = db.Column(db.String(20), default='pending', index=True)  # pending, sent, delivered, failed, replied
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    replied_at = db.Column(db.DateTime)
    
    # Relationships
    target = db.relationship('CampaignTarget', backref='campaign_messages')
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'target_id': self.target_id,
            'message_content': self.message_content,
            'twitter_message_id': self.twitter_message_id,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None
        }

class DirectMessage(db.Model):
    """Direct messages sent and received"""
    __tablename__ = 'direct_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('campaign_targets.id'), nullable=False)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'), nullable=False)
    message_type = db.Column(db.String(20), default='outbound')  # outbound, inbound
    content = db.Column(db.Text, nullable=False)
    twitter_message_id = db.Column(db.String(100))  # Twitter's message ID
    status = db.Column(db.String(20), default='pending')  # pending, sent, delivered, failed
    error_message = db.Column(db.Text)
    sentiment = db.Column(db.String(20))  # For inbound messages: positive, negative, neutral
    ai_generated = db.Column(db.Boolean, default=True)
    recipient_username = db.Column(db.String(50))
    recipient_display_name = db.Column(db.String(100))
    response_time_ms = db.Column(db.Integer)
    retry_count = db.Column(db.Integer, default=0)
    api_call_log_id = db.Column(db.Integer, db.ForeignKey('api_call_logs.id'))
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    target = db.relationship('CampaignTarget', backref='messages')
    twitter_account = db.relationship('TwitterAccount')
    api_call_log = db.relationship('APICallLog', backref='direct_messages')
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_type': self.message_type,
            'content': self.content,
            'status': self.status,
            'sentiment': self.sentiment,
            'ai_generated': self.ai_generated,
            'recipient_username': self.recipient_username,
            'recipient_display_name': self.recipient_display_name,
            'response_time_ms': self.response_time_ms,
            'retry_count': self.retry_count,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat()
        }

class WarmupActivity(db.Model):
    """Track warmup activities for Twitter accounts"""
    __tablename__ = 'warmup_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'), nullable=False)
    activity_type = db.Column(db.String(20), nullable=False)  # like, retweet, reply, follow
    target_tweet_id = db.Column(db.String(100))
    target_username = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    error_message = db.Column(db.Text)
    executed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    twitter_account = db.relationship('TwitterAccount', backref='warmup_activities')

class Analytics(db.Model):
    """Analytics data storage"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # campaign_performance, reply_rate, etc.
    metric_data = db.Column(db.Text)  # JSON string of metric data
    date_period = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='analytics')

class APIUsage(db.Model):
    """Track API usage for rate limiting and billing"""
    __tablename__ = 'api_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    api_type = db.Column(db.String(50), nullable=False)  # twitter, gemini, stripe
    endpoint = db.Column(db.String(100))
    request_count = db.Column(db.Integer, default=1)
    tokens_used = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    date_period = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='api_usage')

class APICallLog(db.Model):
    """Log all twitterapi.io API calls for monitoring and analytics"""
    __tablename__ = 'api_call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    endpoint = db.Column(db.String(100), nullable=False)
    method = db.Column(db.String(10), nullable=False)  # GET, POST, etc.
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    error_category = db.Column(db.String(50))  # authentication, rate_limit, user_error, api_error
    request_data = db.Column(db.Text)  # JSON string of request parameters (excluding sensitive data)
    response_data = db.Column(db.Text)  # JSON string of response data (excluding sensitive data)
    retry_count = db.Column(db.Integer, default=0)
    proxy_used = db.Column(db.String(200))  # Proxy URL used (without credentials)
    endpoint_category = db.Column(db.String(50))  # user_info, dm_send, followers, etc.
    cache_hit = db.Column(db.Boolean, default=False)
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='api_call_logs')
    twitter_account = db.relationship('TwitterAccount', backref='api_call_logs')
    campaign = db.relationship('Campaign', backref='api_call_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'twitter_account_id': self.twitter_account_id,
            'campaign_id': self.campaign_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'success': self.success,
            'error_message': self.error_message,
            'error_category': self.error_category,
            'retry_count': self.retry_count,
            'endpoint_category': self.endpoint_category,
            'cache_hit': self.cache_hit,
            'created_at': self.created_at.isoformat()
        }

class UserInfoCache(db.Model):
    """Cache for user information from TwitterAPI.io"""
    __tablename__ = 'user_info_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    user_id = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100))
    profile_picture_url = db.Column(db.Text)
    follower_count = db.Column(db.Integer)
    following_count = db.Column(db.Integer)
    verified = db.Column(db.Boolean, default=False)
    can_dm = db.Column(db.Boolean, default=True)
    is_private = db.Column(db.Boolean, default=False)
    raw_data = db.Column(db.JSON)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'user_id': self.user_id,
            'display_name': self.display_name,
            'profile_picture_url': self.profile_picture_url,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'verified': self.verified,
            'can_dm': self.can_dm,
            'is_private': self.is_private,
            'cached_at': self.cached_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    def is_expired(self):
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.expires_at

class ConnectedAccountCache(db.Model):
    """Cache for connected account information"""
    __tablename__ = 'connected_account_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'), nullable=False)
    username = db.Column(db.String(50))
    display_name = db.Column(db.String(100))
    profile_picture_url = db.Column(db.Text)
    follower_count = db.Column(db.Integer)
    following_count = db.Column(db.Integer)
    verified = db.Column(db.Boolean, default=False)
    raw_data = db.Column(db.JSON)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    twitter_account = db.relationship('TwitterAccount', backref='account_cache')
    
    def to_dict(self):
        return {
            'id': self.id,
            'twitter_account_id': self.twitter_account_id,
            'username': self.username,
            'display_name': self.display_name,
            'profile_picture_url': self.profile_picture_url,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'verified': self.verified,
            'cached_at': self.cached_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    def is_expired(self):
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.expires_at

# AI Generation Infrastructure Models

class AIGenerationHistory(db.Model):
    """AI generation history for tracking all generated DMs"""
    __tablename__ = 'ai_generation_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_username = db.Column(db.String(50), nullable=False, index=True)
    generated_content = db.Column(db.Text, nullable=False)
    generation_options = db.Column(db.JSON, nullable=False)
    recipient_analysis = db.Column(db.JSON, nullable=False)
    quality_score = db.Column(db.Float)
    personalization_score = db.Column(db.Float)
    user_rating = db.Column(db.Integer)  # 1-5 stars
    was_sent = db.Column(db.Boolean, default=False)
    was_edited = db.Column(db.Boolean, default=False)
    edited_content = db.Column(db.Text)
    generation_time_ms = db.Column(db.Integer)
    ai_model_used = db.Column(db.String(50), default='gemini-pro')
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='ai_generation_history')
    feedback = db.relationship('AIGenerationFeedback', backref='generation_history', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'recipient_username': self.recipient_username,
            'generated_content': self.generated_content,
            'generation_options': self.generation_options,
            'recipient_analysis': self.recipient_analysis,
            'quality_score': self.quality_score,
            'personalization_score': self.personalization_score,
            'user_rating': self.user_rating,
            'was_sent': self.was_sent,
            'was_edited': self.was_edited,
            'edited_content': self.edited_content,
            'generation_time_ms': self.generation_time_ms,
            'ai_model_used': self.ai_model_used,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }

class RecipientAnalysisCache(db.Model):
    """Cache for recipient analysis data"""
    __tablename__ = 'recipient_analysis_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    analysis_data = db.Column(db.JSON, nullable=False)
    analysis_depth = db.Column(db.String(20), nullable=False, default='standard')
    cache_version = db.Column(db.String(10), default='1.0')
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'analysis_data': self.analysis_data,
            'analysis_depth': self.analysis_depth,
            'cache_version': self.cache_version,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    def is_expired(self):
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.expires_at

class AIGenerationMetrics(db.Model):
    """Daily metrics for AI generation performance"""
    __tablename__ = 'ai_generation_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    generation_date = db.Column(db.Date, nullable=False, index=True)
    total_generations = db.Column(db.Integer, default=0)
    successful_generations = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    average_quality_score = db.Column(db.Float)
    average_personalization_score = db.Column(db.Float)
    average_user_rating = db.Column(db.Float)
    average_generation_time_ms = db.Column(db.Integer)
    total_api_calls = db.Column(db.Integer, default=0)
    total_tokens_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='ai_generation_metrics')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'generation_date': self.generation_date.isoformat(),
            'total_generations': self.total_generations,
            'successful_generations': self.successful_generations,
            'messages_sent': self.messages_sent,
            'average_quality_score': self.average_quality_score,
            'average_personalization_score': self.average_personalization_score,
            'average_user_rating': self.average_user_rating,
            'average_generation_time_ms': self.average_generation_time_ms,
            'total_api_calls': self.total_api_calls,
            'total_tokens_used': self.total_tokens_used,
            'created_at': self.created_at.isoformat()
        }

class AIGenerationFeedback(db.Model):
    """User feedback for AI generation improvement"""
    __tablename__ = 'ai_generation_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    generation_history_id = db.Column(db.Integer, db.ForeignKey('ai_generation_history.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    improvement_suggestions = db.Column(db.JSON)
    was_regenerated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='ai_generation_feedback')
    
    def to_dict(self):
        return {
            'id': self.id,
            'generation_history_id': self.generation_history_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'feedback_text': self.feedback_text,
            'improvement_suggestions': self.improvement_suggestions,
            'was_regenerated': self.was_regenerated,
            'created_at': self.created_at.isoformat()
        }
