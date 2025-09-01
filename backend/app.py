"""
XReacher Flask Application
Migrated to use TwitterAPI.io SDK completely
"""

import os
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            email_pattern = r'^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$'
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
            if not re.search(r'\\d', password):
                password_errors.append('one number')
            if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
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
        Login to Twitter account using TwitterAPI.io credentials
        """
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Validate required fields
            required_fields = ['username', 'email', 'password', 'totp_secret']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Create credentials object
            credentials = LoginCredentials(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                totp_secret=data['totp_secret'],
                proxy=data.get('proxy')  # Optional, will use default if not provided
            )
            
            # Attempt login using new SDK
            try:
                session = login_twitter_account(
                    username=credentials.username,
                    email=credentials.email, 
                    password=credentials.password,
                    totp_secret=credentials.totp_secret,
                    proxy=credentials.proxy
                )
                
                # Store Twitter account info in database
                # First check if account already exists
                existing_account = TwitterAccount.query.filter_by(
                    user_id=user_id,
                    screen_name=session.username
                ).first()
                
                if existing_account:
                    # Update existing account
                    existing_account.connection_status = 'connected'
                    existing_account.login_cookie = session.login_cookie
                    existing_account.updated_at = datetime.utcnow()
                    twitter_account = existing_account
                else:
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
                    'message': 'Twitter account connected successfully',
                    'twitter_account': {
                        'id': twitter_account.id,
                        'screen_name': twitter_account.screen_name,
                        'connection_status': twitter_account.connection_status
                    },
                    'screen_name': session.username,
                    'method': 'twitterapi_io'
                })
                
            except TwitterAPIError as e:
                logger.error(f"TwitterAPI.io login failed: {str(e)}")
                return jsonify({
                    'error': f'Twitter login failed: {str(e)}'
                }), 400
                
        except Exception as e:
            logger.error(f"Twitter login error: {str(e)}")
            return jsonify({'error': 'Twitter authentication failed'}), 500
    
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
        """Send direct message using TwitterAPI.io"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Validate required fields
            if not data.get('recipient_id') or not data.get('message'):
                return jsonify({'error': 'recipient_id and message are required'}), 400
            
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
            
            # Send DM using TwitterAPI.io SDK
            try:
                result = send_direct_message(
                    login_cookie=twitter_account.login_cookie,
                    user_id=data['recipient_id'],
                    text=data['message'],
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
            
            # Create tweet using TwitterAPI.io SDK
            try:
                result = create_tweet(
                    login_cookie=twitter_account.login_cookie,
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
            
            # Save file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Upload using TwitterAPI.io SDK
                is_long_video = request.form.get('is_long_video', 'false').lower() == 'true'
                
                result = upload_media(
                    login_cookie=twitter_account.login_cookie,
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
            
            # Follow user using TwitterAPI.io SDK
            try:
                result = follow_user(
                    login_cookie=twitter_account.login_cookie,
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
            
            # Unfollow user using TwitterAPI.io SDK
            try:
                result = unfollow_user(
                    login_cookie=twitter_account.login_cookie,
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
