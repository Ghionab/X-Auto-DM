import stripe
import logging
from typing import Dict, Optional, Tuple
from flask import current_app
from models import db, User

logger = logging.getLogger(__name__)

class StripeService:
    """Service for handling Stripe payments and subscriptions"""
    
    def __init__(self):
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    def create_customer(self, user: User, payment_method_id: str = None) -> Tuple[bool, Dict]:
        """Create a Stripe customer for a user"""
        try:
            customer_data = {
                'email': user.email,
                'name': user.username,
                'metadata': {
                    'user_id': user.id,
                    'username': user.username
                }
            }
            
            if payment_method_id:
                customer_data['payment_method'] = payment_method_id
            
            customer = stripe.Customer.create(**customer_data)
            
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            db.session.commit()
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            
            return True, {
                'customer_id': customer.id,
                'email': customer.email,
                'created': customer.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating Stripe customer: {str(e)}")
            return False, {'error': str(e)}
    
    def create_subscription(self, user: User, price_id: str) -> Tuple[bool, Dict]:
        """Create a subscription for a user"""
        try:
            # Ensure user has a Stripe customer ID
            if not user.stripe_customer_id:
                success, result = self.create_customer(user)
                if not success:
                    return False, result
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            
            # Update user subscription status
            plan_mapping = {
                'price_basic_monthly': 'basic',
                'price_pro_monthly': 'pro', 
                'price_enterprise_monthly': 'enterprise'
            }
            
            user.subscription_plan = plan_mapping.get(price_id, 'basic')
            user.is_premium = True
            db.session.commit()
            
            logger.info(f"Created subscription {subscription.id} for user {user.id}")
            
            return True, {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret,
                'status': subscription.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating subscription: {str(e)}")
            return False, {'error': str(e)}
    
    def cancel_subscription(self, user: User) -> Tuple[bool, Dict]:
        """Cancel a user's subscription"""
        try:
            if not user.stripe_customer_id:
                return False, {'error': 'User has no Stripe customer ID'}
            
            # Get active subscriptions
            subscriptions = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                status='active'
            )
            
            if not subscriptions.data:
                return False, {'error': 'No active subscription found'}
            
            # Cancel the first active subscription
            subscription = subscriptions.data[0]
            cancelled_sub = stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True
            )
            
            logger.info(f"Cancelled subscription {subscription.id} for user {user.id}")
            
            return True, {
                'subscription_id': cancelled_sub.id,
                'cancel_at': cancelled_sub.cancel_at,
                'current_period_end': cancelled_sub.current_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return False, {'error': str(e)}
    
    def get_subscription_details(self, user: User) -> Tuple[bool, Dict]:
        """Get subscription details for a user"""
        try:
            if not user.stripe_customer_id:
                return False, {'error': 'User has no Stripe customer ID'}
            
            # Get subscriptions
            subscriptions = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                limit=1
            )
            
            if not subscriptions.data:
                return True, {'subscription': None}
            
            subscription = subscriptions.data[0]
            
            return True, {
                'subscription': {
                    'id': subscription.id,
                    'status': subscription.status,
                    'current_period_start': subscription.current_period_start,
                    'current_period_end': subscription.current_period_end,
                    'cancel_at_period_end': subscription.cancel_at_period_end,
                    'plan': subscription.items.data[0].price.id if subscription.items.data else None,
                    'amount': subscription.items.data[0].price.unit_amount if subscription.items.data else None,
                    'currency': subscription.items.data[0].price.currency if subscription.items.data else None
                }
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Error getting subscription: {str(e)}")
            return False, {'error': str(e)}
    
    def create_payment_intent(self, amount: int, currency: str = 'usd', 
                             customer_id: str = None) -> Tuple[bool, Dict]:
        """Create a payment intent for one-time payments"""
        try:
            intent_data = {
                'amount': amount,
                'currency': currency,
                'automatic_payment_methods': {'enabled': True},
            }
            
            if customer_id:
                intent_data['customer'] = customer_id
            
            intent = stripe.PaymentIntent.create(**intent_data)
            
            return True, {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            return False, {'error': str(e)}
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Tuple[bool, Dict]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
            )
            
            if event['type'] == 'invoice.payment_succeeded':
                return self._handle_payment_succeeded(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.updated':
                return self._handle_subscription_updated(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.deleted':
                return self._handle_subscription_deleted(event['data']['object'])
            
            else:
                logger.info(f"Unhandled webhook event: {event['type']}")
                return True, {'message': 'Event received but not processed'}
            
        except ValueError as e:
            logger.error(f"Invalid payload in webhook: {str(e)}")
            return False, {'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature in webhook: {str(e)}")
            return False, {'error': 'Invalid signature'}
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return False, {'error': str(e)}
    
    def _handle_payment_succeeded(self, invoice) -> Tuple[bool, Dict]:
        """Handle successful payment"""
        try:
            customer_id = invoice['customer']
            
            # Find user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if not user:
                logger.warning(f"No user found for Stripe customer {customer_id}")
                return False, {'error': 'User not found'}
            
            # Update user premium status
            user.is_premium = True
            db.session.commit()
            
            logger.info(f"Payment succeeded for user {user.id}")
            return True, {'message': 'Payment processed successfully'}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling payment succeeded: {str(e)}")
            return False, {'error': str(e)}
    
    def _handle_payment_failed(self, invoice) -> Tuple[bool, Dict]:
        """Handle failed payment"""
        try:
            customer_id = invoice['customer']
            
            # Find user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if not user:
                logger.warning(f"No user found for Stripe customer {customer_id}")
                return False, {'error': 'User not found'}
            
            logger.info(f"Payment failed for user {user.id}")
            # You might want to send an email notification here
            
            return True, {'message': 'Payment failure processed'}
            
        except Exception as e:
            logger.error(f"Error handling payment failed: {str(e)}")
            return False, {'error': str(e)}
    
    def _handle_subscription_updated(self, subscription) -> Tuple[bool, Dict]:
        """Handle subscription updates"""
        try:
            customer_id = subscription['customer']
            
            # Find user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if not user:
                logger.warning(f"No user found for Stripe customer {customer_id}")
                return False, {'error': 'User not found'}
            
            # Update user subscription status based on Stripe subscription status
            if subscription['status'] == 'active':
                user.is_premium = True
            elif subscription['status'] in ['canceled', 'incomplete_expired', 'unpaid']:
                user.is_premium = False
                user.subscription_plan = 'free'
            
            db.session.commit()
            
            logger.info(f"Subscription updated for user {user.id}: {subscription['status']}")
            return True, {'message': 'Subscription update processed'}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling subscription update: {str(e)}")
            return False, {'error': str(e)}
    
    def _handle_subscription_deleted(self, subscription) -> Tuple[bool, Dict]:
        """Handle subscription cancellation"""
        try:
            customer_id = subscription['customer']
            
            # Find user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if not user:
                logger.warning(f"No user found for Stripe customer {customer_id}")
                return False, {'error': 'User not found'}
            
            # Downgrade user to free plan
            user.is_premium = False
            user.subscription_plan = 'free'
            db.session.commit()
            
            logger.info(f"Subscription cancelled for user {user.id}")
            return True, {'message': 'Subscription cancellation processed'}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling subscription deletion: {str(e)}")
            return False, {'error': str(e)}
    
    def get_pricing_plans(self) -> Dict:
        """Get available pricing plans"""
        return {
            'plans': [
                {
                    'id': 'free',
                    'name': 'Free',
                    'price': 0,
                    'currency': 'usd',
                    'interval': 'month',
                    'features': [
                        '10 DMs per month',
                        'Basic analytics',
                        '1 Twitter account',
                        'Manual target upload'
                    ],
                    'stripe_price_id': None
                },
                {
                    'id': 'basic',
                    'name': 'Basic',
                    'price': 2900,  # $29.00
                    'currency': 'usd',
                    'interval': 'month',
                    'features': [
                        '500 DMs per month',
                        'Advanced analytics',
                        '3 Twitter accounts',
                        'Follower scraping',
                        'AI personalization',
                        'Basic warmup'
                    ],
                    'stripe_price_id': 'price_basic_monthly'
                },
                {
                    'id': 'pro',
                    'name': 'Pro',
                    'price': 9900,  # $99.00
                    'currency': 'usd',
                    'interval': 'month',
                    'features': [
                        '2,000 DMs per month',
                        'Premium analytics',
                        '10 Twitter accounts',
                        'Advanced scraping',
                        'Advanced AI features',
                        'Full warmup automation',
                        'Priority support'
                    ],
                    'stripe_price_id': 'price_pro_monthly'
                },
                {
                    'id': 'enterprise',
                    'name': 'Enterprise',
                    'price': 29900,  # $299.00
                    'currency': 'usd',
                    'interval': 'month',
                    'features': [
                        'Unlimited DMs',
                        'Enterprise analytics',
                        'Unlimited Twitter accounts',
                        'White-label solution',
                        'Custom AI training',
                        'Dedicated support',
                        'API access'
                    ],
                    'stripe_price_id': 'price_enterprise_monthly'
                }
            ]
        }
    
    def get_usage_limits(self, subscription_plan: str) -> Dict:
        """Get usage limits for a subscription plan"""
        limits = {
            'free': {
                'monthly_dms': 10,
                'twitter_accounts': 1,
                'campaigns': 1,
                'targets_per_campaign': 50,
                'ai_features': False,
                'analytics': 'basic',
                'support': 'community'
            },
            'basic': {
                'monthly_dms': 500,
                'twitter_accounts': 3,
                'campaigns': 5,
                'targets_per_campaign': 1000,
                'ai_features': True,
                'analytics': 'advanced',
                'support': 'email'
            },
            'pro': {
                'monthly_dms': 2000,
                'twitter_accounts': 10,
                'campaigns': 20,
                'targets_per_campaign': 5000,
                'ai_features': True,
                'analytics': 'premium',
                'support': 'priority'
            },
            'enterprise': {
                'monthly_dms': -1,  # Unlimited
                'twitter_accounts': -1,
                'campaigns': -1,
                'targets_per_campaign': -1,
                'ai_features': True,
                'analytics': 'enterprise',
                'support': 'dedicated'
            }
        }
        
        return limits.get(subscription_plan, limits['free'])
