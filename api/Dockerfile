# Dockerfile for Streamward AI Assistant API
# Build from the project root: docker build -f api/Dockerfile -t streamward-api .

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for cryptography package)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
# Note: The API depends on sibling modules (auth, chat_assistant, orchestrator_agent, etc.)
COPY api/ ./api/
COPY auth/ ./auth/
COPY chat_assistant/ ./chat_assistant/
COPY orchestrator_agent/ ./orchestrator_agent/
COPY a2a_agents/ ./a2a_agents/
COPY mcp_servers/ ./mcp_servers/
COPY rag/ ./rag/
COPY document_repository/ ./document_repository/

#If the user is on a corporate VPN that does SSL inspection, we need to provide a way to update the trust store of the container.
#This file is included in the python SSL_CERT_FILE environment variable as well.
COPY CATrust.pem* /usr/local/share/ca-certificates/CATrust.crt
RUN update-ca-certificates --verbose

# Expose the API port
EXPOSE 8000

# Run the FastAPI application with uvicorn
# Note: --reload is removed for production; add it back for development if needed
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
