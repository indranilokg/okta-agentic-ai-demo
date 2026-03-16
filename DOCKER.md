# Docker Deployment Guide

This guide explains how to run the Streamward AI Assistant using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start

### 1. Configure Environment Variables

Copy the example Docker Compose file and customize it with your credentials:

```bash
cp docker-compose-example.yaml docker-compose.yaml
```

Edit `docker-compose.yaml` and replace the placeholder values with your actual credentials.

### 2. Build and Run

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up --build -d
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Services

The Docker Compose setup includes two services:

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| `api` | streamward-api | 8000 | FastAPI backend with LLM orchestration |
| `frontend` | streamward-frontend | 3000 | Next.js web interface |

## Configuration

### Environment Variables

The `docker-compose.yaml` file contains all environment variables organized into sections:

#### Backend (API) Configuration

| Section | Variables | Purpose |
|---------|-----------|---------|
| **Core API** | `OPENAI_API_KEY` | OpenAI API access for LLM functionality |
| **Okta Auth** | `OKTA_DOMAIN`, `OKTA_MAIN_SERVER_ID`, `OKTA_MAIN_AUDIENCE` | Primary authentication |
| **Agent Credentials** | `OKTA_*_CLIENT_ID`, `OKTA_*_CLIENT_SECRET` | HR, Finance, Legal agent auth |
| **MCP Cross-App** | `OKTA_EMPLOYEE_MCP_*`, `OKTA_CHAT_ASSISTANT_AGENT_*` | ID-JAG token exchange |
| **FGA** | `FGA_*` | Fine-grained authorization |
| **RAG/Pinecone** | `PINECONE_*` | Document retrieval and embeddings |
| **Privacy** | `ALLOW_PII_IN_LLM_PROMPTS`, `ANONYMOUS_ID_SALT` | Data handling controls |

#### Frontend Configuration

| Variable | Purpose |
|----------|---------|
| `NEXTAUTH_URL` | NextAuth.js callback URL |
| `NEXTAUTH_SECRET` | Session encryption secret |
| `OKTA_CLIENT_ID` / `OKTA_CLIENT_SECRET` | Okta OAuth credentials |
| `OKTA_ISSUER` | Okta authorization server URL |
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL (internal Docker network) |

## Common Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f api
docker compose logs -f frontend

# Stop services
docker compose down

# Rebuild and restart
docker compose up --build -d

# Remove containers and volumes
docker compose down -v
```

## Building Individual Images

### Backend API

```bash
docker build -f api/Dockerfile -t streamward-api .
```

### Frontend

```bash
docker build -f frontend/Dockerfile -t streamward-frontend ./frontend
```

## Networking

Both services run on a shared Docker network (`streamward-network`) allowing internal communication:

- Frontend connects to the API using `http://api:8000` (container name resolution)
- External access uses the exposed ports on localhost

## Troubleshooting

### Container won't start

Check logs for errors:
```bash
docker compose logs api
docker compose logs frontend
```

### API connection issues from frontend

Ensure both containers are on the same network:
```bash
docker network inspect streamward-network
```

### Environment variable issues

Verify environment variables are set correctly:
```bash
docker compose exec api env | grep OKTA
docker compose exec frontend env | grep OKTA
```

### Rebuild after code changes

Force a fresh build:
```bash
docker compose build --no-cache
docker compose up -d
```

## Production Considerations

1. **Secrets Management**: Use Docker secrets or external secrets management instead of environment variables in the compose file
2. **HTTPS**: Configure a reverse proxy (nginx, Traefik) for SSL termination
3. **Health Checks**: Add health check configurations to the compose file
4. **Logging**: Configure centralized logging (ELK, Loki, etc.)
5. **Monitoring**: Add Prometheus/Grafana for metrics
6. **Resource Limits**: Set memory and CPU limits for containers

Example health check addition:
```yaml
api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Development Mode

For development with hot-reloading, you can mount source directories as volumes:

```yaml
api:
  volumes:
    - ./api:/app/api
    - ./auth:/app/auth
    - ./chat_assistant:/app/chat_assistant
  command: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Note: This requires rebuilding the container or ensuring dependencies are installed.
