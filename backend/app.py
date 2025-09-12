"""
XReacher Flask Application
Migrated to use TwitterAPI.io SDK completely
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
from models import db, User, TwitterAccount, Campaign, CampaignTarget

# Import new TwitterAPI.io SDK
from twitterio import (
    TwitterAPIClient, TwitterAPIError, login_twitter_account,
    send_direct_message, create_tweet, LoginCredentials,
    get_user_info, follow_user, unfollow_user, upload_media
)

# Configure logging with enhanced detail for API debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('xreacher.log', mode='a')
    ]
)

# Set specific loggers for detailed API debugging
logging.getLogger('twitterapi_core').setLevel(logging.INFO)
logging.getLogger('twitterio.auth').setLevel(logging.INFO)
logging.getLogger('twitterio').setLevel(logging.INFO)

# Reduce noise from other libraries
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def extract_login_cookie(decrypted_cookie):
    """
    Extract the actual login cookie from various formats
    
    Args:
        decrypted_cookie: Decrypted cookie string (may be JSON response format or direct cookie)
        
    Returns:
        str: Actual cookie string to send to API
    """
    import json
    import base64
    
    try:
        # Try to parse as JSON first
        parsed_data = json.loads(decrypted_cookie)
        
        # Check if this is a response format with login_cookies field
        if isinstance(parsed_data, dict) and 'login_cookies' in parsed_data:
            login_cookies_str = parsed_data['login_cookies']
            
            # Return the base64-encoded format directly
            # The twitterapi.io API expects the login_cookies in base64 format
            return login_cookies_str
        else:
            # Direct cookie JSON format - convert to cookie string
            cookie_parts = []
            for key, value in parsed_data.items():
                cookie_parts.append(f"{key}={value}")
            return "; ".join(cookie_parts)
            
    except json.JSONDecodeError:
        # Not JSON, assume it's already in cookie string format
        pass
    
    # Return as-is if not JSON or other format
    return decrypted_cookie.strip()

def create_app(config_name=None):
    """Create Flask application"""
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Handle proxy headers (for production deployment)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Initialize extensions
    db.init_app(app)
    
    # CORS
    CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    
    # JWT
    jwt = JWTManager(app)
    
    # JWT Error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    )
    limiter.init_app(app)
    
    # Initialize services
    with app.app_context():
        # Create tables
        db.create_all()
    
    # Helper function for cookie decryption
    def decrypt_login_cookie(twitter_account):
        """
        Helper function to decrypt login cookie from TwitterAccount
        
        Args:
            twitter_account: TwitterAccount instance
            
        Returns:
            tuple: (decrypted_cookie, error_response)
            If successful: (cookie_string, None)
            If failed: (None, flask_response)
        """
        try:
            from services.cookie_encryption import CookieManager
            cookie_manager = CookieManager()
            decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
            
            if not decrypted_cookie:
                return None, jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
            
            return decrypted_cookie, None
        except Exception as e:
            logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
            return None, jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429
    
    # Health check
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    
    # ===============================
    # Authentication Routes
    # ===============================
    
    @app.route('/api/auth/register', methods=['POST'])
    @limiter.limit("3 per minute")
    def register():
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['email', 'username', 'password']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Validate email format
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Validate username
            username = data['username'].strip()
            if len(username) < 3:
                return jsonify({'error': 'Username must be at least 3 characters long'}), 400
            if len(username) > 30:
                return jsonify({'error': 'Username must be less than 30 characters'}), 400
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400
            
            # Validate password strength
            password = data['password']
            password_errors = []
            if len(password) < 8:
                password_errors.append('at least 8 characters')
            if not re.search(r'[A-Z]', password):
                password_errors.append('one uppercase letter')
            if not re.search(r'[a-z]', password):
                password_errors.append('one lowercase letter')
            if not re.search(r'\d', password):
                password_errors.append('one number')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                password_errors.append('one special character')
            
            if password_errors:
                return jsonify({
                    'error': f'Password must contain: {", ".join(password_errors)}'
                }), 400
            
            # Check if user already exists (case-insensitive email)
            if User.query.filter(User.email.ilike(data['email'])).first():
                return jsonify({'error': 'Email address is already registered'}), 400
            
            if User.query.filter(User.username.ilike(username)).first():
                return jsonify({'error': 'Username is already taken'}), 400
            
            # Create user
            user = User(
                email=data['email'].lower().strip(),
                username=username
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"User registered: {user.email}")
            
            return jsonify({
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    @limiter.limit("10 per minute")
    def login():
        try:
            data = request.get_json()
            
            if not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            user = User.query.filter_by(email=data['email']).first()
            
            if not user or not user.check_password(data['password']):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            if not user.is_active:
                return jsonify({'error': 'Account is deactivated'}), 401
            
            # Create access token
            access_token = create_access_token(identity=str(user.id))
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': user.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Login failed'}), 500
    
    @app.route('/api/auth/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({'user': user.to_dict()})
            
        except Exception as e:
            logger.error(f"Profile error: {str(e)}")
            return jsonify({'error': 'Failed to fetch profile'}), 500
    
    # ===============================
    # New TwitterAPI.io Authentication Routes
    # ===============================
    
    @app.route('/api/auth/twitter/login', methods=['POST'])
    @jwt_required()
    @limiter.limit("5 per minute")
    def twitter_login():
        """
        Login to Twitter account using TwitterAPI.io credentials with enhanced error handling
        """
        user_id = None
        username = None
        
        try:
            user_id = int(get_jwt_identity())
            
            # Safely get JSON data with error handling
            try:
                data = request.get_json(silent=True)
                if data is None and request.content_type and 'application/json' in request.content_type:
                    # JSON was expected but parsing failed
                    logger.warning(f"Authentication failed for user {user_id}: Invalid JSON data")
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON data',
                        'error_code': 'INVALID_JSON',
                        'details': 'The request must contain valid JSON data'
                    }), 400
            except Exception as json_error:
                logger.warning(f"Authentication failed for user {user_id}: JSON parsing error - {json_error}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data',
                    'error_code': 'INVALID_JSON',
                    'details': 'The request must contain valid JSON data'
                }), 400
            
            # Log authentication attempt (without sensitive data)
            logger.info(f"Twitter authentication attempt for user {user_id}")
            logger.debug(f"Request data keys: {list(data.keys()) if data else 'None'}")
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Authentication failed: User {user_id} not found")
                return jsonify({
                    'success': False,
                    'error': 'User not found',
                    'error_code': 'USER_NOT_FOUND',
                    'details': 'The authenticated user could not be found in the database'
                }), 404
            
            # Validate request data (only check for None, empty dict {} is valid)
            if data is None:
                logger.warning(f"Authentication failed for user {user_id}: No request data provided")
                return jsonify({
                    'success': False,
                    'error': 'Request data is required',
                    'error_code': 'MISSING_REQUEST_DATA',
                    'details': 'No JSON data was provided in the request'
                }), 400
            
            # Validate required fields with detailed error messages
            required_fields = {
                'username': 'Twitter username',
                'email': 'Twitter email address', 
                'password': 'Twitter password',
                'totp_secret': 'TOTP secret for two-factor authentication'
            }
            
            missing_fields = []
            for field, description in required_fields.items():
                if not data.get(field) or not str(data.get(field)).strip():
                    missing_fields.append(f"{field} ({description})")
            
            if missing_fields:
                logger.warning(f"Authentication failed for user {user_id}: Missing required fields: {missing_fields}")
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields',
                    'error_code': 'MISSING_REQUIRED_FIELDS',
                    'details': f"The following fields are required: {', '.join(missing_fields)}",
                    'missing_fields': list(required_fields.keys())
                }), 400
            
            username = data['username'].strip()
            logger.info(f"Attempting Twitter authentication for user {user_id}, Twitter username: {username}")
            
            # Create credentials object
            credentials = LoginCredentials(
                username=username,
                email=data['email'].strip(),
                password=data['password'],
                totp_secret=data['totp_secret'].strip(),
                proxy=data.get('proxy')  # Optional, will use default if not provided
            )
            
            # Attempt login using enhanced auth module
            try:
                logger.info(f"Initiating TwitterAPI.io login for {username}")
                session = login_twitter_account(
                    username=credentials.username,
                    email=credentials.email, 
                    password=credentials.password,
                    totp_secret=credentials.totp_secret,
                    proxy=credentials.proxy
                )
                
                logger.info(f"TwitterAPI.io login successful for {username}")
                logger.debug(f"Session status: {session.status}, message: {session.message}")
                
                # Store Twitter account info in database
                # First check if account already exists
                existing_account = TwitterAccount.query.filter_by(
                    user_id=user_id,
                    screen_name=session.username
                ).first()
                
                if existing_account:
                    logger.info(f"Updating existing Twitter account for user {user_id}, account {session.username}")
                    # Update existing account
                    existing_account.connection_status = 'connected'
                    existing_account.login_cookie = session.login_cookie
                    existing_account.updated_at = datetime.utcnow()
                    twitter_account = existing_account
                else:
                    logger.info(f"Creating new Twitter account for user {user_id}, account {session.username}")
                    # Create new account
                    twitter_account = TwitterAccount(
                        user_id=user_id,
                        twitter_user_id=f"twitterio_{session.username}",  # Placeholder
                        screen_name=session.username,
                        name=session.username,
                        connection_status='connected',
                        login_cookie=session.login_cookie
                    )
                    db.session.add(twitter_account)
                
                db.session.commit()
                
                logger.info(f"Twitter account connected successfully for user {user_id}, account {session.username}")
                
                return jsonify({
                    'success': True,
                    'message': 'Twitter account connected successfully',
                    'data': {
                        'twitter_account': {
                            'id': twitter_account.id,
                            'screen_name': twitter_account.screen_name,
                            'name': twitter_account.name,
                            'connection_status': twitter_account.connection_status,
                            'connected_at': twitter_account.updated_at.isoformat() if twitter_account.updated_at else None
                        },
                        'screen_name': session.username,
                        'method': 'twitterapi_io',
                        'session_status': session.status,
                        'session_message': session.message
                    }
                })
                
            except TwitterAPIError as e:
                error_message = str(e)
                logger.error(f"TwitterAPI.io login failed for user {user_id}, username {username}: {error_message}")
                
                # Parse specific error types for better user feedback
                error_code = 'TWITTER_API_ERROR'
                user_friendly_message = 'Twitter authentication failed'
                
                if 'invalid credentials' in error_message.lower():
                    error_code = 'INVALID_CREDENTIALS'
                    user_friendly_message = 'Invalid Twitter username, email, or password'
                elif 'totp' in error_message.lower() or '2fa' in error_message.lower():
                    error_code = 'INVALID_TOTP'
                    user_friendly_message = 'Invalid two-factor authentication code'
                elif 'rate limit' in error_message.lower():
                    error_code = 'RATE_LIMITED'
                    user_friendly_message = 'Too many login attempts. Please try again later'
                elif 'account locked' in error_message.lower() or 'suspended' in error_message.lower():
                    error_code = 'ACCOUNT_RESTRICTED'
                    user_friendly_message = 'Twitter account is locked or suspended'
                elif 'network' in error_message.lower() or 'connection' in error_message.lower():
                    error_code = 'NETWORK_ERROR'
                    user_friendly_message = 'Network connection error. Please try again'
                elif 'no login cookie' in error_message.lower():
                    error_code = 'NO_LOGIN_COOKIE'
                    user_friendly_message = 'Authentication succeeded but no login session was created'
                
                return jsonify({
                    'success': False,
                    'error': user_friendly_message,
                    'error_code': error_code,
                    'details': error_message,
                    'troubleshooting': {
                        'INVALID_CREDENTIALS': 'Please verify your Twitter username, email, and password are correct',
                        'INVALID_TOTP': 'Please check your two-factor authentication app and enter the current code',
                        'RATE_LIMITED': 'Please wait a few minutes before trying again',
                        'ACCOUNT_RESTRICTED': 'Please check your Twitter account status and resolve any restrictions',
                        'NETWORK_ERROR': 'Please check your internet connection and try again',
                        'NO_LOGIN_COOKIE': 'Please try logging in again or contact support if the issue persists'
                    }.get(error_code, 'Please check your credentials and try again')
                }), 400
                
        except ValueError as e:
            logger.error(f"Invalid user ID in JWT token: {e}")
            return jsonify({
                'success': False,
                'error': 'Invalid authentication token',
                'error_code': 'INVALID_TOKEN',
                'details': 'The authentication token contains invalid user information'
            }), 401
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Unexpected error during Twitter login for user {user_id}, username {username}: {error_message}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log stack trace for debugging
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            return jsonify({
                'success': False,
                'error': 'Twitter authentication failed',
                'error_code': 'INTERNAL_ERROR',
                'details': 'An unexpected error occurred during authentication. Please try again or contact support if the issue persists.'
            }), 500
    
    @app.route('/api/auth/twitter/disconnect', methods=['POST'])
    @jwt_required()
    def twitter_disconnect():
        """Disconnect Twitter account"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            twitter_account_id = data.get('twitter_account_id')
            if not twitter_account_id:
                return jsonify({'error': 'Twitter account ID is required'}), 400
            
            # Verify ownership
            twitter_account = TwitterAccount.query.filter_by(
                id=twitter_account_id,
                user_id=user_id
            ).first()
            
            if not twitter_account:
                return jsonify({'error': 'Twitter account not found'}), 404
            
            # Update account status (no API call needed for twitterapi.io logout)
            twitter_account.connection_status = 'disconnected'
            twitter_account.login_cookie = None
            twitter_account.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Twitter account disconnected for user {user_id}, account {twitter_account_id}")
            
            return jsonify({
                'message': 'Twitter account disconnected successfully',
                'twitter_account_id': twitter_account_id
            })
            
        except Exception as e:
            logger.error(f"Twitter disconnect error: {str(e)}")
            return jsonify({'error': 'Failed to disconnect Twitter account'}), 500
    
    # ===============================
    # Twitter API Routes (using TwitterAPI.io)
    # ===============================
    
    @app.route('/api/twitter/send-dm', methods=['POST'])
    @jwt_required()
    @limiter.limit("10 per hour")
    def send_dm():
        """Send direct message using TwitterAPI.io - supports both username and user_id"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Validate required fields - accept either recipient_id, recipient_username, or username
            recipient_id = data.get('recipient_id')
            recipient_username = data.get('recipient_username') or data.get('username')
            message = data.get('message')
            
            if not message:
                return jsonify({'error': 'message is required'}), 400
                
            if not recipient_id and not recipient_username:
                return jsonify({'error': 'Either recipient_id or recipient_username is required'}), 400
            
            # Get specific Twitter account if provided, otherwise use first connected account
            account_id = data.get('account_id')
            if account_id:
                twitter_account = TwitterAccount.query.filter_by(
                    id=account_id,
                    user_id=user_id,
                    connection_status='connected'
                ).first()
            else:
                twitter_account = TwitterAccount.query.filter_by(
                    user_id=user_id,
                    connection_status='connected'
                ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Decrypt the login cookie before using it
            try:
                from services.cookie_encryption import CookieManager
                cookie_manager = CookieManager()
                decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
                
                if not decrypted_cookie:
                    return jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
                
                # Extract actual cookie from response format if needed
                login_cookie = extract_login_cookie(decrypted_cookie)
            except Exception as e:
                logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
                return jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400
            
            # Convert username to user_id if needed using username resolver service
            if recipient_username and not recipient_id:
                try:
                    from services.username_resolver import get_username_resolver, UsernameResolverError
                    import asyncio
                    
                    # Use username resolver service with caching
                    resolver = get_username_resolver()
                    
                    # Run async function in sync context
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    user_resolution = loop.run_until_complete(resolver.resolve_username(recipient_username))
                    
                    if not user_resolution.exists:
                        return jsonify({'error': f'User @{recipient_username} not found'}), 400
                    
                    recipient_id = user_resolution.user_id
                    logger.info(f"Resolved username @{recipient_username} to user_id {recipient_id} (cached: {user_resolution.cached_at is not None})")
                    
                except UsernameResolverError as e:
                    logger.error(f"Username resolution failed for @{recipient_username}: {e.message}")
                    return jsonify({
                        'error': e.message,
                        'error_code': e.error_code,
                        'username': e.username
                    }), 400
                except Exception as e:
                    logger.error(f"Unexpected error resolving username @{recipient_username}: {str(e)}")
                    return jsonify({'error': f'Failed to resolve username @{recipient_username}'}), 500
            
            # Send DM using TwitterAPI.io SDK
            try:
                result = send_direct_message(
                    login_cookie=login_cookie,  # Use decrypted cookie
                    user_id=recipient_id,
                    text=message,
                    media_ids=data.get('media_ids'),
                    reply_to_message_id=data.get('reply_to_message_id')
                )
                
                return jsonify({
                    'message': 'Direct message sent successfully',
                    'message_id': result.message_id,
                    'status': result.status
                })
                
            except TwitterAPIError as e:
                logger.error(f"DM send failed: {str(e)}")
                return jsonify({'error': f'Failed to send DM: {str(e)}'}), 400
                
        except Exception as e:
            logger.error(f"Send DM error: {str(e)}")
            return jsonify({'error': 'Failed to send direct message'}), 500
    
    @app.route('/api/twitter/create-tweet', methods=['POST'])
    @jwt_required()
    @limiter.limit("20 per hour")
    def create_tweet_route():
        """Create tweet using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Validate required fields
            if not data.get('tweet_text'):
                return jsonify({'error': 'tweet_text is required'}), 400
            
            # Get user's Twitter account
            twitter_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                connection_status='connected'
            ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Decrypt the login cookie before using it
            try:
                from services.cookie_encryption import CookieManager
                cookie_manager = CookieManager()
                decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
                
                if not decrypted_cookie:
                    return jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
                
                # Extract actual cookie from response format if needed
                login_cookie = extract_login_cookie(decrypted_cookie)
            except Exception as e:
                logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
                return jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400
            
            # Create tweet using TwitterAPI.io SDK
            try:
                result = create_tweet(
                    login_cookie=login_cookie,
                    tweet_text=data['tweet_text'],
                    reply_to_tweet_id=data.get('reply_to_tweet_id'),
                    attachment_url=data.get('attachment_url'),
                    community_id=data.get('community_id'),
                    is_note_tweet=data.get('is_note_tweet', False),
                    media_ids=data.get('media_ids')
                )
                
                return jsonify({
                    'message': 'Tweet created successfully',
                    'tweet_id': result.tweet_id,
                    'status': result.status
                })
                
            except TwitterAPIError as e:
                logger.error(f"Tweet creation failed: {str(e)}")
                return jsonify({'error': f'Failed to create tweet: {str(e)}'}), 400
                
        except Exception as e:
            logger.error(f"Create tweet error: {str(e)}")
            return jsonify({'error': 'Failed to create tweet'}), 500
    
    @app.route('/api/twitter/upload-media', methods=['POST'])
    @jwt_required()
    @limiter.limit("20 per hour")
    def upload_media_route():
        """Upload media using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            
            # Check if file was uploaded
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Get user's Twitter account
            twitter_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                connection_status='connected'
            ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Decrypt the login cookie before using it
            try:
                from services.cookie_encryption import CookieManager
                cookie_manager = CookieManager()
                decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
                
                if not decrypted_cookie:
                    return jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
                
                # Extract actual cookie from response format if needed
                login_cookie = extract_login_cookie(decrypted_cookie)
            except Exception as e:
                logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
                return jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400
            
            # Save file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Upload using TwitterAPI.io SDK
                is_long_video = request.form.get('is_long_video', 'false').lower() == 'true'
                
                result = upload_media(
                    login_cookie=login_cookie,
                    file_path=temp_file_path,
                    is_long_video=is_long_video
                )
                
                return jsonify({
                    'message': 'Media uploaded successfully',
                    'media_id': result.media_id,
                    'status': result.status
                })
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except TwitterAPIError as e:
            logger.error(f"Media upload failed: {str(e)}")
            return jsonify({'error': f'Failed to upload media: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Upload media error: {str(e)}")
            return jsonify({'error': 'Failed to upload media'}), 500
    
    @app.route('/api/twitter/validate-username', methods=['POST'])
    @jwt_required()
    @limiter.limit("30 per minute")
    def validate_username():
        """Validate username and return user info using username resolver service"""
        try:
            data = request.get_json()
            username = data.get('username')
            
            if not username:
                return jsonify({'error': 'Username is required'}), 400
            
            from services.username_resolver import get_username_resolver, UsernameResolverError
            import asyncio
            
            # Use username resolver service
            resolver = get_username_resolver()
            
            # Run async function in sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            user_resolution = loop.run_until_complete(resolver.resolve_username(username))
            
            return jsonify({
                'valid': user_resolution.exists,
                'user_info': {
                    'user_id': user_resolution.user_id,
                    'username': user_resolution.username,
                    'name': user_resolution.name,
                    'profile_picture': user_resolution.profile_picture,
                    'can_dm': user_resolution.can_dm,
                    'verified': user_resolution.verified
                } if user_resolution.exists else None,
                'cached': user_resolution.cached_at is not None
            })
            
        except UsernameResolverError as e:
            return jsonify({
                'valid': False,
                'error': e.message,
                'error_code': e.error_code
            }), 400
        except Exception as e:
            logger.error(f"Username validation error: {str(e)}")
            return jsonify({'error': 'Failed to validate username'}), 500

    @app.route('/api/twitter/user-info/<username>', methods=['GET'])
    def get_user_info_route(username):
        """Get user information using TwitterAPI.io (no auth required)"""
        try:
            if not username:
                return jsonify({'error': 'Username is required'}), 400
            
            # Get user info using TwitterAPI.io SDK
            user_info = get_user_info(username)
            
            return jsonify({
                'user': {
                    'id': user_info.id,
                    'username': user_info.username,
                    'name': user_info.name,
                    'profile_picture': user_info.profile_picture,
                    'description': user_info.description,
                    'followers': user_info.followers,
                    'following': user_info.following,
                    'can_dm': user_info.can_dm,
                    'verified': user_info.verified,
                    'created_at': user_info.created_at
                }
            })
            
        except TwitterAPIError as e:
            logger.error(f"Get user info failed: {str(e)}")
            return jsonify({'error': f'Failed to get user info: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Get user info error: {str(e)}")
            return jsonify({'error': 'Failed to get user information'}), 500
    
    @app.route('/api/twitter/follow-user', methods=['POST'])
    @jwt_required()
    @limiter.limit("30 per hour")
    def follow_user_route():
        """Follow user using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            if not data.get('user_id'):
                return jsonify({'error': 'user_id is required'}), 400
            
            # Get user's Twitter account
            twitter_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                connection_status='connected'
            ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Decrypt the login cookie before using it
            try:
                from services.cookie_encryption import CookieManager
                cookie_manager = CookieManager()
                decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
                
                if not decrypted_cookie:
                    return jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
                
                # Extract actual cookie from response format if needed
                login_cookie = extract_login_cookie(decrypted_cookie)
            except Exception as e:
                logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
                return jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400
            
            # Follow user using TwitterAPI.io SDK
            try:
                result = follow_user(
                    login_cookie=login_cookie,
                    user_id=data['user_id']
                )
                
                return jsonify({
                    'message': 'User followed successfully',
                    'status': result.status
                })
                
            except TwitterAPIError as e:
                logger.error(f"Follow user failed: {str(e)}")
                return jsonify({'error': f'Failed to follow user: {str(e)}'}), 400
                
        except Exception as e:
            logger.error(f"Follow user error: {str(e)}")
            return jsonify({'error': 'Failed to follow user'}), 500
    
    @app.route('/api/twitter/unfollow-user', methods=['POST'])
    @jwt_required()
    @limiter.limit("30 per hour")
    def unfollow_user_route():
        """Unfollow user using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            if not data.get('user_id'):
                return jsonify({'error': 'user_id is required'}), 400
            
            # Get user's Twitter account
            twitter_account = TwitterAccount.query.filter_by(
                user_id=user_id,
                connection_status='connected'
            ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Decrypt the login cookie before using it
            try:
                from services.cookie_encryption import CookieManager
                cookie_manager = CookieManager()
                decrypted_cookie = cookie_manager.retrieve_cookie(twitter_account.login_cookie)
                
                if not decrypted_cookie:
                    return jsonify({'error': 'Login cookie has expired or is invalid. Please reconnect your account.'}), 400
                
                # Extract actual cookie from response format if needed
                login_cookie = extract_login_cookie(decrypted_cookie)
            except Exception as e:
                logger.error(f"Cookie decryption failed for account {twitter_account.id}: {str(e)}")
                return jsonify({'error': 'Failed to decrypt login cookie. Please reconnect your account.'}), 400
            
            # Unfollow user using TwitterAPI.io SDK
            try:
                result = unfollow_user(
                    login_cookie=login_cookie,
                    user_id=data['user_id']
                )
                
                return jsonify({
                    'message': 'User unfollowed successfully',
                    'status': result.status
                })
                
            except TwitterAPIError as e:
                logger.error(f"Unfollow user failed: {str(e)}")
                return jsonify({'error': f'Failed to unfollow user: {str(e)}'}), 400
                
        except Exception as e:
            logger.error(f"Unfollow user error: {str(e)}")
            return jsonify({'error': 'Failed to unfollow user'}), 500
    
    # ===============================
    # Manual Account Addition Routes
    # ===============================
    
    @app.route('/api/auth/twitter/add-manual', methods=['POST'])
    @jwt_required()
    @limiter.limit("3 per minute")
    def add_manual_twitter_account():
        """
        Add Twitter account manually using login cookie
        """
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Validate required fields
            if not data.get('login_cookie'):
                return jsonify({'error': 'login_cookie is required'}), 400
            
            # Import manual account service
            from services.manual_account_service import ManualAccountService
            manual_service = ManualAccountService()
            
            # Add account using the service
            success, result = manual_service.add_account_by_cookie(
                user_id=user_id,
                login_cookie=data['login_cookie'],
                account_name=data.get('account_name')
            )
            
            if success:
                logger.info(f"Manual Twitter account added successfully for user {user_id}")
                return jsonify({
                    'message': 'Twitter account added successfully',
                    'account': result
                }), 201
            else:
                logger.warning(f"Failed to add manual Twitter account for user {user_id}: {result.get('error')}")
                return jsonify({
                    'error': result.get('error', 'Failed to add account'),
                    'details': result.get('details')
                }), 400
                
        except Exception as e:
            logger.error(f"Manual account addition error: {str(e)}")
            return jsonify({
                'error': 'Failed to add Twitter account',
                'details': 'An unexpected error occurred'
            }), 500
    
    @app.route('/api/auth/twitter/validate-cookie', methods=['POST'])
    @jwt_required()
    @limiter.limit("10 per minute")
    def validate_twitter_cookie():
        """
        Validate Twitter login cookie format and extract information
        """
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('login_cookie'):
                return jsonify({'error': 'login_cookie is required'}), 400
            
            # Import manual account service
            from services.manual_account_service import ManualAccountService
            manual_service = ManualAccountService()
            
            # Validate cookie
            is_valid, validation_data = manual_service.validate_login_cookie(data['login_cookie'])
            
            if is_valid:
                # Extract account information
                account_info = manual_service.extract_account_info(data['login_cookie'])
                
                return jsonify({
                    'valid': True,
                    'validation_data': validation_data,
                    'account_info': account_info
                })
            else:
                return jsonify({
                    'valid': False,
                    'error': validation_data.get('error', 'Cookie validation failed'),
                    'details': validation_data.get('details')
                }), 400
                
        except Exception as e:
            logger.error(f"Cookie validation error: {str(e)}")
            return jsonify({
                'error': 'Failed to validate cookie',
                'details': 'An unexpected error occurred'
            }), 500
    
    # ===============================
    # Account Management Routes
    # ===============================
    
    @app.route('/api/accounts', methods=['GET'])
    @jwt_required()
    def get_accounts():
        """Get user's connected Twitter accounts"""
        try:
            user_id = int(get_jwt_identity())
            
            accounts = TwitterAccount.query.filter_by(user_id=user_id).all()
            
            return jsonify({
                'accounts': [account.to_dict() for account in accounts]
            })
            
        except Exception as e:
            logger.error(f"Get accounts error: {str(e)}")
            return jsonify({'error': 'Failed to fetch accounts'}), 500
    
    @app.route('/api/twitter/my-account-info', methods=['GET'])
    @jwt_required()
    @limiter.limit("30 per hour")
    def get_my_account_info():
        """Get comprehensive account information using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            
            # Get specific Twitter account if provided, otherwise use first connected account
            account_id = request.args.get('account_id')
            if account_id:
                twitter_account = TwitterAccount.query.filter_by(
                    id=account_id,
                    user_id=user_id,
                    connection_status='connected'
                ).first()
            else:
                twitter_account = TwitterAccount.query.filter_by(
                    user_id=user_id,
                    connection_status='connected'
                ).first()
            
            if not twitter_account or not twitter_account.login_cookie:
                return jsonify({'error': 'No connected Twitter account found'}), 400
            
            # Get comprehensive account info using TwitterAPI.io
            try:
                # Get user info using the account's own username (public endpoint, no login cookie needed)
                user_info = get_user_info(
                    username=twitter_account.username or twitter_account.screen_name
                )
                
                # Structure comprehensive response with all available data
                account_info = {
                    'basic_info': {
                        'user_id': user_info.user_id,
                        'username': user_info.username,
                        'screen_name': user_info.screen_name,
                        'name': user_info.name,
                        'description': user_info.description,
                        'profile_image_url': user_info.profile_image_url,
                        'profile_banner_url': getattr(user_info, 'profile_banner_url', None),
                        'location': getattr(user_info, 'location', None),
                        'url': getattr(user_info, 'url', None),
                        'verified': user_info.verified,
                        'protected': getattr(user_info, 'protected', False),
                        'created_at': user_info.created_at
                    },
                    'stats': {
                        'followers_count': user_info.followers_count,
                        'following_count': user_info.following_count,
                        'tweet_count': getattr(user_info, 'tweet_count', 0),
                        'listed_count': getattr(user_info, 'listed_count', 0),
                        'favourites_count': getattr(user_info, 'favourites_count', 0)
                    },
                    'account_status': {
                        'can_dm': getattr(user_info, 'can_dm', True),
                        'connection_status': twitter_account.connection_status,
                        'is_active': twitter_account.is_active,
                        'last_updated': twitter_account.updated_at.isoformat() if twitter_account.updated_at else None
                    }
                }
                
                # Update local database with fresh info
                twitter_account.name = user_info.name
                twitter_account.followers_count = user_info.followers_count
                twitter_account.following_count = user_info.following_count
                twitter_account.is_verified = user_info.verified
                twitter_account.profile_image_url = user_info.profile_image_url
                twitter_account.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Successfully fetched account info for @{twitter_account.username}")
                
                return jsonify({
                    'message': 'Account information retrieved successfully',
                    'account_info': account_info
                })
                
            except TwitterAPIError as e:
                logger.error(f"Failed to get account info: {str(e)}")
                return jsonify({'error': f'Failed to retrieve account information: {str(e)}'}), 400
                
        except Exception as e:
            logger.error(f"Get account info error: {str(e)}")
            return jsonify({'error': 'Failed to retrieve account information'}), 500
    
    return app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Test the new TwitterAPI.io SDK
    try:
        from twitterio import get_core_client
        core_client = get_core_client()
        
        if core_client.test_connection():
            print("✅ TwitterAPI.io connection test passed")
        else:
            print("⚠️  TwitterAPI.io connection test failed")
            
    except Exception as e:
        print(f"❌ TwitterAPI.io SDK error: {e}")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
