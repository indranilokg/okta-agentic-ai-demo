#!/bin/bash
# Backend startup script that properly sets environment variables

# Set the test user email (customize as needed)
export TEST_USER_EMAIL="${TEST_USER_EMAIL:-indranil.jha@okta.com}"

echo "Starting backend with TEST_USER_EMAIL=$TEST_USER_EMAIL"
echo "Backend will use this email for test tokens"
echo ""

# Run uvicorn with the environment variable set
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

