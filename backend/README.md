# XReacher Backend

A comprehensive Python backend for X (Twitter) DM automation, featuring AI-powered message personalization, account warmup, and advanced analytics.

## Features

- 🤖 **AI-Powered DM Generation**: Personalized messages using Google Gemini AI
- 📊 **Advanced Analytics**: Detailed campaign performance metrics and sentiment analysis
- 🔄 **Account Warmup**: Automated account warming to avoid bot detection
- 💳 **Stripe Integration**: Subscription management with multiple pricing tiers
- 🎯 **Smart Targeting**: Follower scraping and CSV/JSON import for target lists
- 🛡️ **Anti-Bot Protection**: Human-like delays and randomized activities
- 📈 **Real-time Monitoring**: Live campaign tracking and performance insights

## Tech Stack

- **Backend**: Flask, SQLAlchemy, JWT Authentication
- **AI**: Google Gemini Pro for message generation and sentiment analysis
- **Scraping**: Playwright for advanced Twitter data collection
- **Payment**: Stripe for subscription management
- **Database**: SQLite (development) / PostgreSQL (production)
- **Queue**: Redis + Celery for background tasks
- **Rate Limiting**: Flask-Limiter with Redis backend

## Installation

### Prerequisites

- Python 3.9+
- Node.js 18+ (for frontend)
- Redis server (for rate limiting and caching)

### Backend Setup

1. **Clone and navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers:**
```bash
playwright install
```

5. **Environment configuration:**
```bash
cp .env.example .env
```

Edit `.env` file with your API keys:

```env
# Twitter API Configuration (twitterapi.io)
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_BASE_URL=https://api.twitterapi.io

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./xreacher.db

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key_here

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Redis Configuration
REDIS_URL=redis://localhost:6379
```

6. **Initialize database:**
```bash
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

## API Keys Setup

### 1. Twitter API (twitterapi.io)

1. Visit [twitterapi.io](https://twitterapi.io)
2. Create an account and get your API key
3. Add it to your `.env` file

### 2. Google Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create an API key for Gemini Pro
3. Add it to your `.env` file

### 3. Stripe (for payments)

1. Create a Stripe account at [stripe.com](https://stripe.com)
2. Get your publishable and secret keys from the dashboard
3. Set up webhook endpoint for subscription events
4. Add keys to your `.env` file

## Running the Application

### Development Mode

1. **Start Redis server:**
```bash
redis-server
```

2. **Start Flask backend:**
```bash
python app.py
```

3. **Start background scheduler (in separate terminal):**
```bash
python scheduler.py
```

4. **Start frontend (in separate terminal):**
```bash
cd ../
npm install
npm run dev
```

The backend will be available at `http://localhost:5000`
The frontend will be available at `http://localhost:3000`

### Production Deployment

1. **Set environment variables:**
```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost/xreacher
```

2. **Use a production WSGI server:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. **Set up reverse proxy (Nginx example):**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;  # Frontend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;  # Backend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API Documentation

### Authentication

#### Register User
```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123"
}
```

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

### Twitter Accounts

#### Add Twitter Account
```bash
POST /api/twitter-accounts
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "twitter_username"
}
```

#### Get Twitter Accounts
```bash
GET /api/twitter-accounts
Authorization: Bearer <token>
```

### Campaigns

#### Create Campaign
```bash
POST /api/campaigns
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Campaign",
  "twitter_account_id": 1,
  "target_type": "followers_scrape",
  "target_username": "target_user",
  "message_template": "Hi {name}, I noticed your work in {industry}...",
  "ai_rules": {
    "tone": "professional",
    "purpose": "networking",
    "call_to_action": "connect"
  },
  "personalization_enabled": true,
  "daily_limit": 50
}
```

#### Start Campaign
```bash
POST /api/campaigns/{id}/start
Authorization: Bearer <token>
```

#### Get Campaign Analytics
```bash
GET /api/campaigns/{id}/analytics
Authorization: Bearer <token>
```

### Scraping

#### Scrape Followers
```bash
POST /api/scrape/followers
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "target_user",
  "max_followers": 100
}
```

#### Upload CSV
```bash
POST /api/scrape/upload-csv
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: users.csv
```

### Warmup

#### Start Account Warmup
```bash
POST /api/warmup/{account_id}/start
Authorization: Bearer <token>
```

#### Get Warmup Status
```bash
GET /api/warmup/{account_id}/status
Authorization: Bearer <token>
```

### Payments

#### Get Pricing Plans
```bash
GET /api/stripe/plans
```

#### Create Subscription
```bash
POST /api/stripe/create-subscription
Authorization: Bearer <token>
Content-Type: application/json

{
  "price_id": "price_basic_monthly"
}
```

## Architecture

### Services

- **TwitterService**: Handles Twitter API interactions
- **GeminiService**: AI message generation and sentiment analysis
- **ScraperService**: Data collection and file processing
- **CampaignService**: Campaign management and message sending
- **StripeService**: Payment processing and subscription management
- **WarmupService**: Account warming automation

### Background Tasks

The scheduler handles:
- Campaign message processing (every 30 minutes)
- Warmup activity execution (every 15 minutes)
- Daily cleanup tasks (2 AM daily)
- Analytics aggregation (every 6 hours)

### Anti-Bot Features

- Random delays between requests
- Human-like typing patterns
- Rotating user agents
- Gradual activity ramping
- Break simulation
- Rate limiting compliance

## Security Features

- JWT authentication
- Rate limiting
- Input validation
- SQL injection protection
- CORS configuration
- Secure password hashing
- Environment variable configuration

## Database Schema

### Key Tables

- **users**: User accounts and subscriptions
- **twitter_accounts**: Connected Twitter accounts
- **campaigns**: DM campaigns
- **campaign_targets**: Target users for campaigns
- **direct_messages**: Sent/received messages
- **warmup_activities**: Account warming activities
- **analytics**: Performance metrics

## Monitoring and Logging

- Comprehensive logging throughout the application
- Error tracking and reporting
- Performance metrics
- Campaign success rates
- API usage tracking

## Troubleshooting

### Common Issues

1. **Twitter API Rate Limits**
   - The app includes automatic rate limit handling
   - Requests are spaced out automatically
   - Use the built-in retry mechanisms

2. **Gemini AI Quota**
   - Monitor your Google AI Studio usage
   - The app includes fallback message templates
   - Consider implementing message caching

3. **Database Connections**
   - Ensure your database URL is correct
   - For SQLite, check file permissions
   - For PostgreSQL, verify connection parameters

4. **Redis Connection**
   - Make sure Redis server is running
   - Check Redis connection URL in environment

### Debugging

Enable debug logging:
```bash
export FLASK_DEBUG=True
python app.py
```

Check logs for specific services:
```python
import logging
logging.getLogger('services.twitter_service').setLevel(logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the API documentation

## Disclaimer

This software is for educational and research purposes. Users are responsible for complying with Twitter's Terms of Service and applicable laws. The developers are not responsible for any misuse of this software.
