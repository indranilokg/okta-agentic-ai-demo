# Streamward AI Assistant - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Okta Developer Account
- Auth0 Developer Account
- OpenAI API Key
- Pinecone Account

### Backend Deployment (FastAPI)

#### Option 1: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env

# Edit .env with your configuration
# Run the backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Render (Recommended)
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.template`

#### Option 3: Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login

# Deploy
fly launch
fly deploy
```

### Frontend Deployment (React)

#### Option 1: Local Development
```bash
cd frontend
npm install
cp env.template .env
# Edit .env with your configuration
npm run dev
```

#### Option 2: Vercel (Recommended)
1. Connect your GitHub repository to Vercel
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Add environment variables from `env.template`

#### Option 3: Netlify
1. Connect your GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variables

## 🔧 Configuration

### Required Environment Variables

#### Backend (.env)
```bash
# Okta Configuration
OKTA_DOMAIN=your-okta-domain.okta.com
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
OKTA_REDIRECT_URI=http://localhost:3000/auth/callback

# Auth0 Configuration
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=your-auth0-audience

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=streamward-documents

# Application Configuration
SECRET_KEY=your-secret-key-here
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

#### Frontend (.env)
```bash
VITE_OKTA_ISSUER=https://your-okta-domain.okta.com/oauth2/default
VITE_OKTA_CLIENT_ID=your-okta-client-id
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 🏗️ Architecture

### Production Architecture
```
┌────────────────────────────────────────┐
│       Frontend (React/Vercel)          │
│  ┌──────────────────────────────────┐   │
│  │  Chat UI + Dashboard + Settings  │   │
│  │  Okta Login + WebSocket          │   │
│  └────────────┬─────────────────────┘   │
└───────────────┼────────────────────────┘
                │ HTTPS/WSS
┌───────────────▼────────────────────────┐
│      Backend (FastAPI/Render)           │
│  ┌──────────────────────────────────┐   │
│  │  LangGraph Orchestrator          │   │
│  │  ├─ Orchestrator Agent           │   │
│  │  ├─ HR A2A Agent                 │   │
│  │  ├─ Finance A2A Agent            │   │
│  │  └─ Legal A2A Agent              │   │
│  │                                  │   │
│  │  REST API + WebSocket            │   │
│  │  DPOP Protection                 │   │
│  └──────────────────────────────────┘   │
└────────────────────────────────────────┘
         │
    ├────┼────┐
    │    │    │
    ▼    ▼    ▼
  Okta Auth0 Pinecone
```

## 🔒 Security Considerations

### Production Security Checklist
- [ ] Use HTTPS for all communications
- [ ] Implement proper CORS policies
- [ ] Use environment variables for secrets
- [ ] Enable DPOP protection for all API calls
- [ ] Implement rate limiting
- [ ] Use secure WebSocket connections (WSS)
- [ ] Enable Okta MFA
- [ ] Implement proper logging and monitoring

### DPOP Implementation
The system uses DPOP (Demonstrating Proof-of-Possession) for protecting document search requests:

1. **Key Generation**: Generate RSA key pair for DPOP
2. **Proof Creation**: Create JWT with DPOP claims
3. **Verification**: Verify DPOP proof on server side
4. **Protection**: All document searches require valid DPOP proof

## 📊 Monitoring

### Health Checks
- Backend: `GET /health`
- Agent Status: `GET /api/agents/status`
- WebSocket: Connection status in frontend

### Logging
- Application logs: Structured logging with timestamps
- Error tracking: Exception handling and reporting
- Performance monitoring: Response times and throughput

## 🚀 Scaling

### Horizontal Scaling
- Multiple backend instances behind load balancer
- Stateless design for easy scaling
- WebSocket sticky sessions for real-time features

### Database Scaling
- Pinecone handles vector database scaling automatically
- Consider Redis for session storage at scale
- Implement caching for frequently accessed data

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy Streamward AI

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        # Add Render deployment step

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        # Add Vercel deployment step
```

## 📝 Troubleshooting

### Common Issues
1. **CORS Errors**: Check frontend URL in backend CORS settings
2. **WebSocket Connection**: Verify WSS URLs in production
3. **Token Validation**: Check Okta/Auth0 configuration
4. **Pinecone Connection**: Verify API keys and index name

### Debug Mode
Set `DEBUG=true` in environment variables for detailed logging.
