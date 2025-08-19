import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///xreacher.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM') or 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_EXPIRATION_HOURS', 24)))
    
    # Twitter API
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
    TWITTER_API_BASE_URL = os.environ.get('TWITTER_API_BASE_URL', 'https://api.twitterapi.io')
    
    # Gemini AI
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # Anti-bot Protection
    USER_AGENT = os.environ.get('USER_AGENT', 
                               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    MIN_DELAY_BETWEEN_REQUESTS = int(os.environ.get('MIN_DELAY_BETWEEN_REQUESTS', 2))
    MAX_DELAY_BETWEEN_REQUESTS = int(os.environ.get('MAX_DELAY_BETWEEN_REQUESTS', 5))
    
    # Warmup Configuration
    WARMUP_LIKES_PER_DAY = int(os.environ.get('WARMUP_LIKES_PER_DAY', 50))
    WARMUP_RETWEETS_PER_DAY = int(os.environ.get('WARMUP_RETWEETS_PER_DAY', 20))
    WARMUP_REPLIES_PER_DAY = int(os.environ.get('WARMUP_REPLIES_PER_DAY', 10))
    WARMUP_DURATION_DAYS = int(os.environ.get('WARMUP_DURATION_DAYS', 7))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
