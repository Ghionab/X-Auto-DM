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
from services.twitter_service import TwitterService
from services.gemini_service import GeminiService
from services.scraper_service import ScraperService
from services.campaign_service import CampaignService
from services.stripe_service import StripeService
from services.warmup_service import WarmupService
from services.x_oauth_service import XOAuthService
from services.token_storage_service import TokenStorageService

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
            
            # Create user (no auto-login as per requirements)
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
    # New X Authentication Routes (Hybrid System)
    # ===============================
    
    @app.route('/api/auth/twitter/cookie-login', methods=['POST'])
    @jwt_required()
    def twitter_cookie_login():
        """Authenticate using X/Twitter cookies from user's browser"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Validate required cookies
            cookies = data.get('cookies')
            if not cookies:
                return jsonify({'error': 'Cookies are required'}), 400
            
            # Ensure we have essential Twitter cookies
            required_cookies = ['auth_token', 'ct0']
            for cookie_name in required_cookies:
                if not cookies.get(cookie_name):
                    return jsonify({
                        'error': f'Missing required cookie: {cookie_name}',
                        'fallback_to_oauth': True
                    }), 400
            
            try:
                # Use X API to verify the cookies and get user info
                from x_auth import create_x_auth
                x_auth = create_x_auth()
                
                # Create a session using the cookies to verify they're valid
                # This is a placeholder - actual implementation would need to use the cookies
                # to make an authenticated request to X API
                
                # For now, we'll simulate user data extraction from cookies
                # In a real implementation, you'd use the cookies to make API calls
                user_info = {
                    'id': '123456789',  # Extract from cookies or API call
                    'username': 'placeholder_user',  # Extract from cookies or API call
                    'name': 'Placeholder User',
                    'profile_image_url': '',
                    'public_metrics': {
                        'followers_count': 0,
                        'following_count': 0
                    },
                    'verified': False
                }
                
                # Store the authentication info
                token_storage = TokenStorageService()
                
                # For cookie auth, we store a placeholder token with the cookie data
                # In production, you'd want to store the cookies securely
                store_success, store_result = token_storage.store_oauth_tokens(
                    user_id=user_id,
                    access_token='cookie_auth_placeholder',
                    access_token_secret='cookie_auth_placeholder',
                    twitter_user_id=user_info['id'],
                    screen_name=user_info['username']
                )
                
                if not store_success:
                    logger.error(f"Token storage failed: {store_result}")
                    return jsonify({
                        'error': 'Failed to store authentication data',
                        'fallback_to_oauth': True
                    }), 500
                
                # Create or update Twitter account
                account_success, account_result = token_storage.create_or_update_twitter_account(
                    user_id=user_id,
                    user_data=user_info,
                    oauth_tokens_id=store_result['token_id']
                )
                
                if not account_success:
                    logger.error(f"Twitter account creation failed: {account_result}")
                    return jsonify({
                        'error': 'Failed to create Twitter account',
                        'fallback_to_oauth': True
                    }), 500
                
                logger.info(f"Cookie authentication successful for user {user_id}, account {user_info['username']}")
                
                return jsonify({
                    'message': 'X account connected successfully via cookies',
                    'twitter_account': account_result['twitter_account'],
                    'screen_name': user_info['username'],
                    'method': 'cookie'
                })
                
            except Exception as cookie_error:
                logger.error(f"Cookie authentication failed: {str(cookie_error)}")
                # Graceful fallback - tell frontend to use OAuth
                return jsonify({
                    'error': 'Cookie authentication failed - cookies may be expired or invalid',
                    'fallback_to_oauth': True
                }), 400
                
        except Exception as e:
            logger.error(f"Cookie login error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'fallback_to_oauth': True
            }), 500
    
    @app.route('/api/auth/twitter/oauth-login', methods=['POST'])
    @jwt_required()
    def twitter_oauth_login():
        """Initiate X OAuth flow for account connection"""
        try:
            user_id = int(get_jwt_identity())
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            from x_auth import create_x_auth, XAuthError
            
            # Create X Auth instance
            x_auth = create_x_auth()
            
            # Generate PKCE pair and state
            code_verifier, code_challenge = x_auth.generate_pkce_pair()
            state = x_auth.generate_state()
            
            # Get authorization URL
            authorization_url = x_auth.get_authorization_url(state, code_challenge)
            
            logger.info(f"Generated X OAuth URL for user {user_id}")
            
            return jsonify({
                'authorization_url': authorization_url,
                'state': state,
                'code_verifier': code_verifier,
                'method': 'oauth'
            })
            
        except XAuthError as e:
            logger.error(f"X Auth error: {str(e)}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"OAuth initiation error: {str(e)}")
            return jsonify({'error': 'Failed to initiate OAuth'}), 500
    
    @app.route('/api/auth/twitter/oauth-callback', methods=['POST'])
    @jwt_required()
    def twitter_oauth_callback():
        """Handle OAuth callback and complete authentication"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get required parameters
            authorization_code = data.get('code')
            code_verifier = data.get('code_verifier')
            state = data.get('state')
            
            if not authorization_code or not code_verifier:
                return jsonify({'error': 'Missing authorization code or code verifier'}), 400
            
            from x_auth import create_x_auth, XAuthError
            
            # Create X Auth instance
            x_auth = create_x_auth()
            
            # Exchange code for tokens
            token_data = x_auth.exchange_code_for_tokens(authorization_code, code_verifier)
            
            # Get user info
            access_token = token_data.get('access_token')
            user_info = x_auth.get_user_info(access_token)
            
            if 'data' not in user_info:
                return jsonify({'error': 'Failed to get user information'}), 400
            
            user_data = user_info['data']
            
            # Store tokens securely
            token_storage = TokenStorageService()
            
            # Store encrypted tokens
            store_success, store_result = token_storage.store_oauth_tokens(
                user_id=user_id,
                access_token=access_token,
                access_token_secret=token_data.get('refresh_token', ''),
                twitter_user_id=user_data.get('id'),
                screen_name=user_data.get('username')
            )
            
            if not store_success:
                logger.error(f"Token storage failed: {store_result}")
                return jsonify({'error': 'Failed to store tokens'}), 500
            
            # Create or update Twitter account
            account_success, account_result = token_storage.create_or_update_twitter_account(
                user_id=user_id,
                user_data={
                    'screen_name': user_data.get('username'),
                    'name': user_data.get('name'),
                    'followers_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                    'following_count': user_data.get('public_metrics', {}).get('following_count', 0),
                    'verified': user_data.get('verified', False),
                    'profile_image_url': user_data.get('profile_image_url', '')
                },
                oauth_tokens_id=store_result['token_id']
            )
            
            if not account_success:
                logger.error(f"Twitter account creation failed: {account_result}")
                return jsonify({'error': 'Failed to create Twitter account'}), 500
            
            logger.info(f"OAuth authentication completed successfully for user {user_id}, account {user_data.get('username')}")
            
            return jsonify({
                'message': 'X account connected successfully via OAuth',
                'twitter_account': account_result['twitter_account'],
                'screen_name': user_data.get('username'),
                'method': 'oauth'
            })
            
        except XAuthError as e:
            logger.error(f"X Auth error: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return jsonify({'error': 'OAuth callback failed'}), 500
    
    # ===============================
    # Legacy X OAuth Routes (Keep for compatibility)
    # ===============================
    
    @app.route('/api/auth/x/initiate', methods=['POST'])
    @jwt_required()
    def initiate_x_oauth():
        """Initiate X OAuth flow"""
        try:
            user_id = int(get_jwt_identity())
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Initialize OAuth service
            oauth_service = XOAuthService()
            
            # Get request token and authorization URL
            success, result = oauth_service.initiate_oauth()
            
            if success:
                # Store request token temporarily (you might want to use Redis for this in production)
                # For now, we'll return it to the frontend to pass back in the callback
                return jsonify({
                    'authorization_url': result['authorization_url'],
                    'oauth_token': result['oauth_token'],
                    'oauth_token_secret': result['oauth_token_secret']
                })
            else:
                logger.error(f"OAuth initiation failed: {result}")
                return jsonify({'error': result.get('error', 'Failed to initiate OAuth')}), 400
                
        except Exception as e:
            logger.error(f"OAuth initiation error: {str(e)}")
            return jsonify({'error': 'Failed to initiate OAuth'}), 500
    
    @app.route('/api/auth/x/callback', methods=['POST'])
    @jwt_required()
    def handle_x_oauth_callback():
        """Handle X OAuth callback"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Validate required parameters
            required_params = ['oauth_token', 'oauth_verifier', 'oauth_token_secret']
            for param in required_params:
                if not data.get(param):
                    return jsonify({'error': f'Missing parameter: {param}'}), 400
            
            # Initialize services
            oauth_service = XOAuthService()
            token_storage = TokenStorageService()
            
            # Exchange request token for access token
            success, result = oauth_service.handle_callback(
                data['oauth_token'],
                data['oauth_verifier'],
                data['oauth_token_secret']
            )
            
            if not success:
                logger.error(f"OAuth callback failed: {result}")
                return jsonify({'error': result.get('error', 'OAuth callback failed')}), 400
            
            access_token = result['access_token']
            access_token_secret = result['access_token_secret']
            twitter_user_id = result['user_id']
            screen_name = result['screen_name']
            
            # Verify credentials and get user info
            verify_success, user_data = oauth_service.verify_credentials(access_token, access_token_secret)
            
            if not verify_success:
                logger.error(f"Credentials verification failed: {user_data}")
                return jsonify({'error': 'Failed to verify credentials'}), 400
            
            # Store encrypted tokens
            store_success, store_result = token_storage.store_oauth_tokens(
                user_id=user_id,
                access_token=access_token,
                access_token_secret=access_token_secret,
                twitter_user_id=twitter_user_id,
                screen_name=screen_name
            )
            
            if not store_success:
                logger.error(f"Token storage failed: {store_result}")
                return jsonify({'error': 'Failed to store tokens'}), 500
            
            # Create or update Twitter account
            account_success, account_result = token_storage.create_or_update_twitter_account(
                user_id=user_id,
                user_data=user_data,
                oauth_tokens_id=store_result['token_id']
            )
            
            if not account_success:
                logger.error(f"Twitter account creation failed: {account_result}")
                return jsonify({'error': 'Failed to create Twitter account'}), 500
            
            logger.info(f"X OAuth completed successfully for user {user_id}, account {screen_name}")
            
            return jsonify({
                'message': 'X account connected successfully',
                'twitter_account': account_result['twitter_account'],
                'screen_name': screen_name
            })
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return jsonify({'error': 'OAuth callback processing failed'}), 500
    
    @app.route('/api/auth/x/disconnect', methods=['POST'])
    @jwt_required()
    def disconnect_x_account():
        """Disconnect X account by revoking tokens"""
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
            
            # Initialize token storage service
            token_storage = TokenStorageService()
            
            # Revoke tokens
            success, result = token_storage.revoke_oauth_tokens(
                user_id=user_id,
                twitter_account_id=twitter_account_id
            )
            
            if success:
                # Update account connection status
                twitter_account.connection_status = 'revoked'
                twitter_account.oauth_tokens_id = None
                twitter_account.updated_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"X account disconnected for user {user_id}, account {twitter_account_id}")
                
                return jsonify({
                    'message': 'X account disconnected successfully',
                    'twitter_account_id': twitter_account_id
                })
            else:
                return jsonify({'error': result.get('error', 'Failed to disconnect account')}), 500
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Account disconnection error: {str(e)}")
            return jsonify({'error': 'Failed to disconnect account'}), 500
    

    @app.route('/api/auth/x/login', methods=['GET'])
    @jwt_required()
    def start_x_oauth():
        """Start X OAuth 2.0 flow - returns authorization URL"""
        try:
            user_id = int(get_jwt_identity())
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            from x_auth import create_x_auth, XAuthError
            
            # Create X Auth instance
            x_auth = create_x_auth()
            
            # Generate PKCE pair and state
            code_verifier, code_challenge = x_auth.generate_pkce_pair()
            state = x_auth.generate_state()
            
            # Store PKCE verifier and state in session (you might want to use Redis in production)
            # For now, we'll return them to be stored client-side temporarily
            authorization_url = x_auth.get_authorization_url(state, code_challenge)
            
            logger.info(f"Generated X OAuth URL for user {user_id}")
            
            return jsonify({
                'authorization_url': authorization_url,
                'state': state,
                'code_verifier': code_verifier  # In production, store this server-side
            })
            
        except XAuthError as e:
            logger.error(f"X Auth error: {str(e)}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"OAuth initiation error: {str(e)}")
            return jsonify({'error': 'Failed to initiate OAuth'}), 500
    
    @app.route('/api/auth/x/callback', methods=['GET'])
    def handle_x_oauth_callback_redirect():
        """Handle X OAuth callback and exchange code for tokens"""
        try:
            # Get parameters from callback
            authorization_code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            
            if error:
                logger.error(f"OAuth error: {error}")
                return jsonify({'error': f'OAuth error: {error}'}), 400
            
            if not authorization_code or not state:
                return jsonify({'error': 'Missing authorization code or state'}), 400
            
            # In a real implementation, you'd validate the state against stored value
            # For now, we'll accept it and let the frontend handle validation
            
            from x_auth import create_x_auth, XAuthError
            
            # This endpoint will be called by X, so we need to handle it differently
            # We'll redirect to frontend with the code and state
            frontend_callback_url = f"http://localhost:3000/auth/x/callback?code={authorization_code}&state={state}"
            
            return f'''
            <html>
                <head><title>X Authentication</title></head>
                <body>
                    <script>
                        // Redirect to frontend callback
                        window.location.href = "{frontend_callback_url}";
                    </script>
                    <p>Redirecting...</p>
                </body>
            </html>
            '''
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return jsonify({'error': 'OAuth callback failed'}), 500
    
    @app.route('/api/auth/x/exchange', methods=['POST'])
    @jwt_required()
    def exchange_x_oauth_code():
        """Exchange authorization code for access tokens"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get required parameters
            authorization_code = data.get('code')
            code_verifier = data.get('code_verifier')
            state = data.get('state')
            
            if not authorization_code or not code_verifier:
                return jsonify({'error': 'Missing authorization code or code verifier'}), 400
            
            from x_auth import create_x_auth, XAuthError
            
            # Create X Auth instance
            x_auth = create_x_auth()
            
            # Exchange code for tokens
            token_data = x_auth.exchange_code_for_tokens(authorization_code, code_verifier)
            
            # Get user info
            access_token = token_data.get('access_token')
            user_info = x_auth.get_user_info(access_token)
            
            if 'data' not in user_info:
                return jsonify({'error': 'Failed to get user information'}), 400
            
            user_data = user_info['data']
            
            # Store tokens securely
            token_storage = TokenStorageService()
            
            # Store encrypted tokens
            store_success, store_result = token_storage.store_oauth_tokens(
                user_id=user_id,
                access_token=access_token,
                access_token_secret=token_data.get('refresh_token', ''),
                twitter_user_id=user_data.get('id'),
                screen_name=user_data.get('username')
            )
            
            if not store_success:
                logger.error(f"Token storage failed: {store_result}")
                return jsonify({'error': 'Failed to store tokens'}), 500
            
            # Create or update Twitter account
            account_success, account_result = token_storage.create_or_update_twitter_account(
                user_id=user_id,
                user_data={
                    'screen_name': user_data.get('username'),
                    'name': user_data.get('name'),
                    'followers_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                    'following_count': user_data.get('public_metrics', {}).get('following_count', 0),
                    'verified': user_data.get('verified', False),
                    'profile_image_url': user_data.get('profile_image_url', '')
                },
                oauth_tokens_id=store_result['token_id']
            )
            
            if not account_success:
                logger.error(f"Twitter account creation failed: {account_result}")
                return jsonify({'error': 'Failed to create Twitter account'}), 500
            
            logger.info(f"X OAuth completed successfully for user {user_id}, account {user_data.get('username')}")
            
            return jsonify({
                'message': 'X account connected successfully',
                'twitter_account': account_result['twitter_account'],
                'screen_name': user_data.get('username')
            })
            
        except XAuthError as e:
            logger.error(f"X Auth error: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return jsonify({'error': 'Token exchange failed'}), 500

    @app.route('/api/auth/x/status', methods=['GET'])
    @jwt_required()
    def get_x_oauth_status():
        """Get OAuth connection status for user's X accounts"""
        try:
            user_id = int(get_jwt_identity())
            
            # Initialize token storage service
            token_storage = TokenStorageService()
            
            # Get connected accounts
            success, result = token_storage.get_user_connected_accounts(user_id)
            
            if success:
                return jsonify({
                    'connected_accounts': result['accounts'],
                    'count': result['count']
                })
            else:
                return jsonify({'error': result.get('error', 'Failed to get connection status')}), 500
                
        except Exception as e:
            logger.error(f"OAuth status error: {str(e)}")
            return jsonify({'error': 'Failed to get OAuth status'}), 500
    
    # ===============================
    # Twitter Account Routes
    # ===============================
    
    @app.route('/api/twitter-accounts', methods=['GET'])
    @jwt_required()
    def get_twitter_accounts():
        try:
            user_id = int(get_jwt_identity())
            accounts = TwitterAccount.query.filter_by(user_id=user_id).all()
            
            return jsonify({
                'accounts': [account.to_dict() for account in accounts]
            })
            
        except Exception as e:
            logger.error(f"Error fetching Twitter accounts: {str(e)}")
            return jsonify({'error': 'Failed to fetch accounts'}), 500
    
    @app.route('/api/twitter-accounts', methods=['POST'])
    @jwt_required()
    def add_twitter_account():
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            if not data.get('username'):
                return jsonify({'error': 'Username is required'}), 400
            
            # Check if account already exists
            existing = TwitterAccount.query.filter_by(
                user_id=user_id, 
                username=data['username']
            ).first()
            
            if existing:
                return jsonify({'error': 'Account already added'}), 400
            
            # Get account info from Twitter API
            twitter_service = TwitterService()
            success, profile_data = twitter_service.get_user_profile(data['username'])
            
            if not success:
                return jsonify({'error': 'Failed to fetch Twitter profile'}), 400
            
            # Create Twitter account
            account = TwitterAccount(
                user_id=user_id,
                username=profile_data['username'],
                display_name=profile_data['name'],
                profile_image_url=profile_data['profile_image_url'],
                followers_count=profile_data['followers_count'],
                following_count=profile_data['following_count'],
                is_verified=profile_data['verified']
            )
            
            db.session.add(account)
            db.session.commit()
            
            return jsonify({
                'message': 'Twitter account added successfully',
                'account': account.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding Twitter account: {str(e)}")
            return jsonify({'error': 'Failed to add account'}), 500
    
    # ===============================
    # Campaign Routes
    # ===============================
    
    @app.route('/api/campaigns', methods=['GET'])
    @jwt_required()
    def get_campaigns():
        try:
            user_id = int(get_jwt_identity())
            status = request.args.get('status')
            
            campaign_service = CampaignService()
            campaigns = campaign_service.get_user_campaigns(user_id, status)
            
            return jsonify({'campaigns': campaigns})
            
        except Exception as e:
            logger.error(f"Error fetching campaigns: {str(e)}")
            return jsonify({'error': 'Failed to fetch campaigns'}), 500
    
    @app.route('/api/campaigns', methods=['POST'])
    @jwt_required()
    def create_campaign():
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'twitter_account_id', 'target_type']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            campaign_service = CampaignService()
            success, result = campaign_service.create_campaign(user_id, data)
            
            if success:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            return jsonify({'error': 'Failed to create campaign'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
    @jwt_required()
    def get_campaign(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            return jsonify({'campaign': campaign.to_dict()})
            
        except Exception as e:
            logger.error(f"Error fetching campaign: {str(e)}")
            return jsonify({'error': 'Failed to fetch campaign'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>/start', methods=['POST'])
    @jwt_required()
    def start_campaign(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            
            # Verify ownership
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            campaign_service = CampaignService()
            success, result = campaign_service.start_campaign(campaign_id)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error starting campaign: {str(e)}")
            return jsonify({'error': 'Failed to start campaign'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>/pause', methods=['POST'])
    @jwt_required()
    def pause_campaign(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            
            # Verify ownership
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            campaign_service = CampaignService()
            success, result = campaign_service.pause_campaign(campaign_id)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error pausing campaign: {str(e)}")
            return jsonify({'error': 'Failed to pause campaign'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>/preview', methods=['POST'])
    @jwt_required()
    def preview_campaign_message(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json() or {}
            
            # Verify ownership
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            campaign_service = CampaignService()
            success, result = campaign_service.preview_campaign_message(
                campaign_id, 
                data.get('target_username')
            )
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            return jsonify({'error': 'Failed to generate preview'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>/analytics', methods=['GET'])
    @jwt_required()
    def get_campaign_analytics(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            
            # Verify ownership
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            campaign_service = CampaignService()
            success, result = campaign_service.get_campaign_analytics(campaign_id)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error fetching analytics: {str(e)}")
            return jsonify({'error': 'Failed to fetch analytics'}), 500
    
    # ===============================
    # Scraping Routes
    # ===============================
    
    @app.route('/api/scrape/followers', methods=['POST'])
    @jwt_required()
    def scrape_followers():
        try:
            data = request.get_json()
            
            if not data.get('username'):
                return jsonify({'error': 'Username is required'}), 400
            
            max_followers = min(data.get('max_followers', 100), 1000)  # Cap at 1000
            
            scraper_service = ScraperService()
            success, followers = scraper_service.scrape_followers_api(
                data['username'], 
                max_followers
            )
            
            if success:
                return jsonify({
                    'followers': followers,
                    'count': len(followers)
                })
            else:
                return jsonify({'error': 'Failed to scrape followers'}), 400
                
        except Exception as e:
            logger.error(f"Error scraping followers: {str(e)}")
            return jsonify({'error': 'Failed to scrape followers'}), 500
    
    @app.route('/api/scrape/upload-csv', methods=['POST'])
    @jwt_required()
    def upload_csv():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be CSV format'}), 400
            
            # Read CSV content
            csv_content = file.read().decode('utf-8')
            
            scraper_service = ScraperService()
            success, users = scraper_service.process_csv_upload(csv_content)
            
            if success:
                return jsonify({
                    'users': users,
                    'count': len(users)
                })
            else:
                return jsonify({'error': 'Failed to process CSV'}), 400
                
        except Exception as e:
            logger.error(f"Error processing CSV upload: {str(e)}")
            return jsonify({'error': 'Failed to process CSV'}), 500
    
    @app.route('/api/campaigns/<int:campaign_id>/targets', methods=['POST'])
    @jwt_required()
    def add_campaign_targets(campaign_id):
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            # Verify ownership
            campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found'}), 404
            
            if not data.get('targets'):
                return jsonify({'error': 'No targets provided'}), 400
            
            campaign_service = CampaignService()
            success, result = campaign_service.add_targets_to_campaign(
                campaign_id, 
                data['targets']
            )
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error adding targets: {str(e)}")
            return jsonify({'error': 'Failed to add targets'}), 500
    
    # ===============================
    # Warmup Routes
    # ===============================
    
    @app.route('/api/warmup/<int:account_id>/start', methods=['POST'])
    @jwt_required()
    def start_warmup(account_id):
        try:
            user_id = int(get_jwt_identity())
            
            # Verify ownership
            account = TwitterAccount.query.filter_by(id=account_id, user_id=user_id).first()
            if not account:
                return jsonify({'error': 'Twitter account not found'}), 404
            
            warmup_service = WarmupService()
            success, result = warmup_service.start_warmup(account_id)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error starting warmup: {str(e)}")
            return jsonify({'error': 'Failed to start warmup'}), 500
    
    @app.route('/api/warmup/<int:account_id>/status', methods=['GET'])
    @jwt_required()
    def get_warmup_status(account_id):
        try:
            user_id = int(get_jwt_identity())
            
            # Verify ownership
            account = TwitterAccount.query.filter_by(id=account_id, user_id=user_id).first()
            if not account:
                return jsonify({'error': 'Twitter account not found'}), 404
            
            warmup_service = WarmupService()
            success, result = warmup_service.get_warmup_status(account_id)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error fetching warmup status: {str(e)}")
            return jsonify({'error': 'Failed to fetch warmup status'}), 500
    
    # ===============================
    # Payment Routes
    # ===============================
    
    @app.route('/api/stripe/plans', methods=['GET'])
    def get_pricing_plans():
        try:
            stripe_service = StripeService()
            plans = stripe_service.get_pricing_plans()
            return jsonify(plans)
            
        except Exception as e:
            logger.error(f"Error fetching plans: {str(e)}")
            return jsonify({'error': 'Failed to fetch plans'}), 500
    
    @app.route('/api/stripe/create-subscription', methods=['POST'])
    @jwt_required()
    def create_subscription():
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            if not data.get('price_id'):
                return jsonify({'error': 'Price ID is required'}), 400
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            stripe_service = StripeService()
            success, result = stripe_service.create_subscription(user, data['price_id'])
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return jsonify({'error': 'Failed to create subscription'}), 500
    
    @app.route('/api/stripe/webhook', methods=['POST'])
    def stripe_webhook():
        try:
            payload = request.get_data()
            sig_header = request.headers.get('Stripe-Signature')
            
            stripe_service = StripeService()
            success, result = stripe_service.handle_webhook(payload, sig_header)
            
            if success:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return jsonify({'error': 'Webhook processing failed'}), 400
    
    # ===============================
    # Analytics Routes
    # ===============================
    
    @app.route('/api/analytics/dashboard', methods=['GET'])
    @jwt_required()
    def get_dashboard_analytics():
        try:
            user_id = int(get_jwt_identity())
            
            # Get user's campaigns
            campaigns = Campaign.query.filter_by(user_id=user_id).all()
            
            # Calculate overall stats
            total_campaigns = len(campaigns)
            active_campaigns = len([c for c in campaigns if c.status == 'active'])
            total_messages_sent = sum(c.messages_sent for c in campaigns)
            total_replies_received = sum(c.replies_received for c in campaigns)
            
            reply_rate = (total_replies_received / total_messages_sent * 100) if total_messages_sent > 0 else 0
            
            # Recent activity
            recent_campaigns = sorted(campaigns, key=lambda c: c.updated_at, reverse=True)[:5]
            
            return jsonify({
                'overview': {
                    'total_campaigns': total_campaigns,
                    'active_campaigns': active_campaigns,
                    'total_messages_sent': total_messages_sent,
                    'total_replies_received': total_replies_received,
                    'overall_reply_rate': round(reply_rate, 2)
                },
                'recent_campaigns': [c.to_dict() for c in recent_campaigns],
                'chart_data': {
                    'campaign_performance': [
                        {
                            'name': c.name,
                            'messages_sent': c.messages_sent,
                            'replies_received': c.replies_received,
                            'positive_replies': c.positive_replies
                        } for c in campaigns[-10:]  # Last 10 campaigns
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching dashboard analytics: {str(e)}")
            return jsonify({'error': 'Failed to fetch analytics'}), 500
    
    @app.route('/api/dashboard/analytics', methods=['GET'])
    @jwt_required()
    def get_dashboard_analytics_alt():
        """Alternative endpoint for dashboard analytics with consistent empty state structure"""
        try:
            user_id = int(get_jwt_identity())
            
            # Get user's campaigns
            campaigns = Campaign.query.filter_by(user_id=user_id).all()
            
            # Calculate overall stats or return empty structure
            if campaigns:
                total_campaigns = len(campaigns)
                active_campaigns = len([c for c in campaigns if c.status == 'active'])
                total_messages_sent = sum(c.messages_sent for c in campaigns)
                total_replies_received = sum(c.replies_received for c in campaigns)
                reply_rate = (total_replies_received / total_messages_sent * 100) if total_messages_sent > 0 else 0
                recent_campaigns = sorted(campaigns, key=lambda c: c.updated_at, reverse=True)[:5]
                chart_data = [
                    {
                        'name': c.name,
                        'messages_sent': c.messages_sent,
                        'replies_received': c.replies_received,
                        'positive_replies': c.positive_replies
                    } for c in campaigns[-10:]
                ]
            else:
                # Return empty structure when no data exists
                total_campaigns = 0
                active_campaigns = 0
                total_messages_sent = 0
                total_replies_received = 0
                reply_rate = 0
                recent_campaigns = []
                chart_data = []
            
            return jsonify({
                'overview': {
                    'total_campaigns': total_campaigns,
                    'active_campaigns': active_campaigns,
                    'total_messages_sent': total_messages_sent,
                    'total_replies_received': total_replies_received,
                    'overall_reply_rate': round(reply_rate, 2)
                },
                'recent_campaigns': [c.to_dict() for c in recent_campaigns],
                'chart_data': {
                    'campaign_performance': chart_data
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching dashboard analytics: {str(e)}")
            return jsonify({'error': 'Failed to fetch analytics'}), 500
    
    @app.route('/api/user/dms', methods=['GET'])
    @jwt_required()
    def get_user_dms():
        """Get user's DM data or return empty array for empty state"""
        try:
            user_id = int(get_jwt_identity())
            
            # For now, return empty array as there's no DM data model yet
            # This can be updated later when DM functionality is implemented
            return jsonify([])
            
        except Exception as e:
            logger.error(f"Error fetching user DMs: {str(e)}")
            return jsonify({'error': 'Failed to fetch DMs'}), 500
    
    return app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
