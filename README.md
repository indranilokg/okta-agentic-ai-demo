# Streamward AI Assistant

A comprehensive end-to-end agentic AI demo showcasing advanced security features and multi-agent coordination for Streamward Corporation.

## Project Overview

Streamward Corporation operates across multiple departments with an intelligent AI assistant that handles:
- **HR Department**: Employee management, payroll, benefits
- **Finance Department**: Budgeting, expense management, financial reporting  
- **Legal Department**: Contract management, compliance, risk assessment
- **IT Department**: System administration, security, infrastructure

##  Key Features

1. **Multi-Provider Authentication**: Okta + Auth0 integration
2. **Cross-App Access**: ID-JAG tokens between identity providers
3. **Agent-to-Agent Communication**: Google A2A protocol using token exchange
4. **RAG with Fine-Grained Authorization**: Document access control
5. **Human-in-the-Loop**: CIBA flow for sensitive transaction approval
6. **Token Protection**: DPOP (Demonstrating Proof-of-Possession)
7. **LangGraph Orchestration**: Multi-agent workflow management

##  Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- OpenAI API Key (Required)
- Okta Developer Account (Optional for authentication)

### Backend Setup

**Option A: Using the startup script (Recommended)**
```bash
# Copy environment template
cp env.template .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your-openai-api-key-here

# Run the startup script
./start_backend.sh
```

**Option B: Manual setup**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test OpenAI connection
python -c "import os; from dotenv import load_dotenv; import openai; load_dotenv(); client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY')); print(' OpenAI working!')"

# Start the server
python -m uvicorn api.main:app --reload
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp env.template .env.local
# Edit .env.local with your Okta configuration (optional)

# Start frontend
npm run dev
```

## Testing

### Test Full Stack
1. Start backend: `./start_backend.sh`
2. Start frontend: `cd frontend && npm run dev`
3. Visit: `http://localhost:3000`
4. Test conversation context by asking follow-up questions

##  Development URLs

- **Backend**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

## Project Structure

```
okta-agentic-ai-demo/
├── api/                    # FastAPI backend
├── chat_assistant/         # Main chat interface
├── mcp_servers/            # MCP server implementations
├── orchestrator_agent/     # Multi-agent workflow coordinator
├── a2a_agents/            # Agent-to-agent communication
├── auth/                  # Authentication components
├── document_repository/    # RAG tool with DPOP protection
├── frontend/              # React frontend
└── deployment/            # Deployment configurations
```

##  Demo Scenarios

1. **Employee Onboarding**: Multi-department workflow coordination
2. **Partner Information Lookup**: Direct MCP query with Auth0
3. **Financial Transaction**: Orchestrator workflow with human approval
4. **Company Policy Lookup**: DPOP-protected document search
5. **Compliance Audit**: Multi-agent audit coordination

## Technology Stack

- **Backend**: FastAPI + Python + LangGraph
- **Frontend**: React + TypeScript + NextAuth.js
- **Vector DB**: Pinecone
- **Identity**: Okta + Auth0
- **Deployment**: Vercel (frontend) + Render (backend)
