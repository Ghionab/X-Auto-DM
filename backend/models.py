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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    twitter_account_id = db.Column(db.Integer, db.ForeignKey('twitter_accounts.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, active, paused, completed, failed
    target_type = db.Column(db.String(50))  # followers_scrape, manual_list, csv_upload
    target_username = db.Column(db.String(50))  # For follower scraping
    ai_rules = db.Column(db.Text)  # JSON string of AI rules and instructions
    message_template = db.Column(db.Text)
    personalization_enabled = db.Column(db.Boolean, default=True)
    preview_message = db.Column(db.Text)
    
    # Campaign metrics
    total_targets = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    replies_received = db.Column(db.Integer, default=0)
    positive_replies = db.Column(db.Integer, default=0)
    negative_replies = db.Column(db.Integer, default=0)
    
    # Scheduling
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    daily_limit = db.Column(db.Integer, default=50)
    delay_min = db.Column(db.Integer, default=30)  # Minutes between messages
    delay_max = db.Column(db.Integer, default=120)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    twitter_account = db.relationship('TwitterAccount', backref='campaigns')
    targets = db.relationship('CampaignTarget', backref='campaign', cascade='all, delete-orphan')
    messages = db.relationship('DirectMessage', backref='campaign', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'target_type': self.target_type,
            'target_username': self.target_username,
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
            'updated_at': self.updated_at.isoformat()
        }

class CampaignTarget(db.Model):
    """Target users for campaigns"""
    __tablename__ = 'campaign_targets'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    followers_count = db.Column(db.Integer)
    following_count = db.Column(db.Integer)
    profile_image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # pending, sent, replied, failed
    message_sent_at = db.Column(db.DateTime)
    reply_received_at = db.Column(db.DateTime)
    reply_sentiment = db.Column(db.String(20))  # positive, negative, neutral
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'bio': self.bio,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'status': self.status,
            'message_sent_at': self.message_sent_at.isoformat() if self.message_sent_at else None,
            'reply_received_at': self.reply_received_at.isoformat() if self.reply_received_at else None,
            'reply_sentiment': self.reply_sentiment
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
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    target = db.relationship('CampaignTarget', backref='messages')
    twitter_account = db.relationship('TwitterAccount')
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_type': self.message_type,
            'content': self.content,
            'status': self.status,
            'sentiment': self.sentiment,
            'ai_generated': self.ai_generated,
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
