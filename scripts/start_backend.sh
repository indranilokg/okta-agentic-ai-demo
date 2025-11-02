#!/bin/bash

# Streamward AI Assistant Startup Script
# Run this from the project root or from the scripts directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

echo "🚀 Starting Streamward AI Assistant"
echo "=================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "🐍 Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    echo "⚠️  Python 3.13 detected - this may cause compilation issues"
    echo "   Consider using Python 3.11 for better compatibility:"
    echo "   brew install python@3.11"
    echo "   python3.11 -m venv venv"
    echo ""
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "   Please copy env.template to .env and configure your API keys:"
    echo "   cp env.template .env"
    echo "   # Then edit .env with your OpenAI API key"
    exit 1
fi

# Load environment variables
source .env

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not set in .env file!"
    echo "   Please add your OpenAI API key to the .env file"
    exit 1
fi

echo "✅ Environment configured"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🧪 Testing OpenAI connection..."
python -c "
import os
from dotenv import load_dotenv
import openai

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print('❌ OPENAI_API_KEY not set!')
    exit(1)

client = openai.OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Hello!'}],
    max_tokens=10
)
print('✅ OpenAI connection working!')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Backend test passed! Starting FastAPI server..."
    echo "   Backend will be available at: http://localhost:8000"
    echo "   API docs will be available at: http://localhost:8000/docs"
    echo ""
    echo "   In another terminal, start the frontend:"
    echo "   cd frontend && npm run dev"
    echo ""
    
    # Start the FastAPI server
    python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "❌ Backend test failed. Please check your configuration."
    exit 1
fi

