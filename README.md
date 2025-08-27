# XReacher - Twitter DM Automation Platform

A comprehensive Twitter/X DM automation platform for outreach campaigns with AI-powered personalization and analytics.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ 
- Node.js 18+
- NPM or Yarn

### 1. Backend Setup (Flask API)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the backend server
python run.py
```

The backend will run on http://localhost:5000

### 2. Frontend Setup (Next.js)

Open a new terminal and:

```bash
# Navigate to project root
cd .

# Install dependencies (if not already done)
npm install

# Start the development server
npm run dev
```

The frontend will run on http://localhost:3000

## 🔧 Configuration

### Backend Configuration
The backend uses environment variables from `backend/.env`:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key

# Database (SQLite used by default)
DATABASE_URL=sqlite:///xreacher.db

# External APIs
TWITTER_API_KEY=your-twitterapi-key
GEMINI_API_KEY=your-gemini-api-key

# Optional: Redis for task queue
REDIS_URL=redis://localhost:6379

# Optional: Stripe for payments
STRIPE_SECRET_KEY=sk_test_your_stripe_secret
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_public
```

### Frontend Configuration
The frontend uses `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## 🏗️ Architecture

### Backend (Flask)
- **RESTful API** with JWT authentication
- **SQLAlchemy** ORM with SQLite database
- **Twitter API Integration** via twitterapi.io
- **AI Personalization** using Google Gemini
- **Campaign Management** with automated scheduling
- **Analytics Dashboard** with performance metrics

### Frontend (Next.js 14)
- **React 18** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **Shadcn/UI** components
- **Real-time** API integration
- **Responsive** mobile-first design

## 📋 Features

### ✅ Completed Features
- **User Authentication** (login/register)
- **Twitter Account Management**
- **Campaign Creation & Management**
- **Follower Scraping** from competitor accounts
- **AI-Powered Message Personalization**
- **Real-time Dashboard Analytics**
- **Account Warmup System**
- **Stripe Payment Integration**
- **Comprehensive API Documentation**

### 🔄 API Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/profile` - Get user profile

#### Twitter Accounts
- `GET /api/twitter-accounts` - List connected accounts
- `POST /api/twitter-accounts` - Connect new account

#### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns/{id}` - Get campaign details
- `POST /api/campaigns/{id}/start` - Start campaign
- `POST /api/campaigns/{id}/pause` - Pause campaign

#### Scraping
- `POST /api/scrape/followers` - Scrape followers
- `POST /api/scrape/upload-csv` - Upload CSV targets

#### Analytics
- `GET /api/analytics/dashboard` - Dashboard metrics

## 🎯 Usage

### 1. Register/Login
- Visit http://localhost:3000/login
- Create an account or login with existing credentials

### 2. Connect Twitter Account
- Go to "My Accounts" tab
- Add your Twitter username (requires twitterapi.io integration)

### 3. Create Campaign
- Navigate to "New Campaign" tab
- Build target list by:
  - Adding usernames manually
  - Scraping followers from competitor accounts
- Configure message template with personalization
- Select source Twitter account
- Create and start campaign

### 4. Monitor Performance
- View real-time analytics in Dashboard
- Track message delivery, reply rates, and engagement
- Monitor campaign performance metrics

## 🛠️ Development

### Backend Development
```bash
# Run backend in development mode
cd backend
python run.py

# Database operations
flask db init    # Initialize database
flask db migrate # Create migrations
flask db upgrade # Apply migrations
```

### Frontend Development
```bash
# Run frontend in development mode
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check
```

## 📊 Database Schema

The application uses SQLite with the following main tables:
- `users` - User accounts and authentication
- `twitter_accounts` - Connected Twitter profiles
- `campaigns` - DM campaign configurations
- `campaign_targets` - Target users for campaigns
- `messages` - Sent message logs
- `analytics` - Performance metrics

## 🔐 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting on API endpoints
- CORS protection
- Input validation and sanitization
- Secure environment variable handling

## 🚀 Deployment

### Backend Deployment
1. Set production environment variables
2. Use a production WSGI server (gunicorn)
3. Configure reverse proxy (nginx)
4. Set up SSL/TLS certificates

### Frontend Deployment
1. Build the application: `npm run build`
2. Deploy to Vercel, Netlify, or similar platform
3. Configure API_URL environment variable

## 📄 License

This project is for demonstration purposes. Please ensure compliance with Twitter's Terms of Service and applicable laws when using for outreach campaigns.

## 🤝 Support

For issues or questions:
1. Check the console logs for error details
2. Verify API keys are correctly configured
3. Ensure both backend and frontend servers are running
4. Review the network requests in browser dev tools
