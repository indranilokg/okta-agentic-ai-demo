# Demo Execution Scripts

This folder contains utility scripts for running and testing the Streamward AI Assistant demo.

## Scripts

### `start_backend.sh`
Starts the FastAPI backend server with environment checks and dependency installation.

**Usage:**
```bash
# From project root
./scripts/start_backend.sh

# Or from scripts directory
cd scripts && ./start_backend.sh
```

**What it does:**
- Checks Python version
- Verifies `.env` file exists
- Creates/activates virtual environment
- Installs dependencies
- Tests OpenAI connection
- Starts FastAPI server on `http://localhost:8000`

### `upload_security_doc.py`
Uploads a sample security policy document to Pinecone and adds FGA relations for testing.

**Usage:**
```bash
# From project root
python scripts/upload_security_doc.py

# Or from scripts directory
cd scripts && python upload_security_doc.py
```

**What it does:**
- Uploads a sample security policy document
- Adds FGA "owner" and "viewer" relations for the configured user email
- Verifies document can be retrieved
- Prints document ID and testing instructions

**Configuration:**
Edit `TEST_USER_EMAIL` in the script to use your Okta email address.

### `clear_pinecone.py`
Clears all documents from Pinecone (with confirmation).

**Usage:**
```bash
# From project root
python scripts/clear_pinecone.py

# Or from scripts directory
cd scripts && python clear_pinecone.py
```

**What it does:**
- Lists all documents in Pinecone
- Prompts for confirmation (type "DELETE ALL")
- Deletes all documents from Pinecone
- Attempts to clean up FGA relations
- Prints summary of deletions

**⚠️ Warning:** This will permanently delete all documents. Use with caution!

### `test_token_exchange.py`
Tests the RFC 8693 Token Exchange functionality using the Okta AI SDK.

**Usage:**
```bash
# From project root
python scripts/test_token_exchange.py

# Or from scripts directory
cd scripts && python test_token_exchange.py
```

**What it does:**
- Verifies access tokens using SDK's verify_token method
- Tests token exchange for different agent audiences (HR, Finance, Legal)
- Simulates A2A (Agent-to-Agent) token exchange chains
- Tests cross-agent token exchanges (Finance → HR, Finance → Legal)
- Tests exchanging different token types (access_token, id_token)

**Requirements:**
- Valid Okta configuration in `.env` file
- A valid Okta access token (obtained from frontend login, Postman, or OAuth2 flow)

**Getting a test token:**
1. Log in through the frontend and copy the access token from browser DevTools
2. Use Postman/OAuth2 flow to obtain a token
3. Set `TEST_ACCESS_TOKEN` environment variable before running
4. Or enter token interactively when prompted

## Prerequisites

1. `.env` file configured in project root
2. Backend dependencies installed (`pip install -r requirements.txt`)
3. Pinecone and FGA credentials configured in `.env`

## Notes

- All scripts can be run from the project root or from the `scripts` directory
- Scripts automatically detect and navigate to the project root
- Make sure the backend server is running when testing with `upload_security_doc.py`

