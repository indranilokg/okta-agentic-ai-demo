#!/usr/bin/env python3
"""
Test script for Token Exchange functionality

This script demonstrates how to test the RFC 8693 Token Exchange implementation
using the Okta AI SDK.

Usage:
    python scripts/test_token_exchange.py

Requirements:
    - Valid Okta configuration in .env file
    - A valid Okta access token (can be obtained from frontend login or Postman)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.okta_auth import OktaAuth
from auth.okta_scopes import OKTA_SCOPES, get_default_hr_scopes, get_default_finance_scopes, get_default_legal_scopes, get_cross_agent_scope


async def test_token_verification(okta_auth: OktaAuth, access_token: str):
    """Test token verification using SDK"""
    print("\n" + "="*60)
    print("TEST 1: Token Verification")
    print("="*60)
    print("Verifying user access token from main authorization server")
    
    try:
        # Verify the initial access token (from main server)
        # Try different issuers to find the correct one
        possible_issuers = [
            f"{okta_auth.okta_domain}/oauth2/{okta_auth.main_server_id}",
            f"{okta_auth.okta_domain}/oauth2/default",
        ]
        
        # Also check audience - could be client_id or api://streamward-chat
        possible_audiences = [
            okta_auth.client_id,
            okta_auth.main_audience,
            "api://default"
        ]
        
        verified = False
        for issuer in possible_issuers:
            for audience in possible_audiences:
                try:
                    result = okta_auth.verify_token(
                        token=access_token,
                        issuer=issuer,
                        audience=audience
                    )
                    if result.get('valid'):
                        print(f"✅ Token verification successful!")
                        print(f"   Subject: {result.get('sub')}")
                        print(f"   Email: {result.get('email')}")
                        print(f"   Audience: {result.get('aud')}")
                        print(f"   Issuer: {result.get('iss')}")
                        print(f"   Scopes: {result.get('scope', 'N/A')}")
                        verified = True
                        break
                except:
                    continue
            if verified:
                break
        
        if not verified:
            print(f"❌ Token verification failed with all issuer/audience combinations")
            print(f"   Tried issuers: {possible_issuers}")
            print(f"   Tried audiences: {possible_audiences}")
            print(f"   Please verify the token was issued by the correct authorization server")
            return False
        
        return True
            
    except Exception as e:
        print(f"❌ Error during token verification: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_token_exchange_single(
    okta_auth: OktaAuth, 
    access_token: str, 
    audience: str, 
    agent_name: str,
    source_agent: Optional[str] = None,
    expected_scope: Optional[str] = None
):
    """Test exchanging token for a single audience"""
    print(f"\n📋 Testing token exchange for {agent_name}")
    print(f"   Target Audience: {audience}")
    if source_agent:
        print(f"   Source Agent: {source_agent} (cross-agent exchange)")
    else:
        print(f"   Source: Chat Assistant (user-to-agent exchange)")
    
    try:
        # Map audiences to appropriate scopes for their servers
        # Use centralized scope constants from okta_scopes
        scope_map = {
            okta_auth.hr_audience: get_default_hr_scopes(),
            okta_auth.finance_audience: get_default_finance_scopes(),
            okta_auth.legal_audience: get_default_legal_scopes()
        }
        
        # Use provided scope or get from map
        scope = expected_scope or scope_map.get(audience, "read write")
        
        # Exchange token for the target audience
        exchanged_token = await okta_auth.exchange_token(
            token=access_token,
            target_audience=audience,
            scope=scope,
            source_agent=source_agent
        )
        
        print(f"✅ Token exchange successful!")
        print(f"   Requested scope: {scope}")
        print(f"   Exchanged token (first 50 chars): {exchanged_token[:50]}...")
        
        # Determine authorization server ID for verification
        server_id = okta_auth.audience_to_server_map.get(audience, "default")
        issuer = f"{okta_auth.okta_domain}/oauth2/{server_id}"
        
        # Verify the exchanged token
        print(f"\n   Verifying exchanged token...")
        print(f"   Expected issuer: {issuer}")
        verify_result = okta_auth.verify_token(
            token=exchanged_token,
            issuer=issuer,
            audience=audience
        )
        
        if verify_result.get('valid'):
            print(f"   ✅ Exchanged token verified!")
            print(f"      Audience: {verify_result.get('aud')}")
            print(f"      Issuer: {verify_result.get('iss')}")
            print(f"      Subject: {verify_result.get('sub')}")
            return exchanged_token
        else:
            print(f"   ⚠️ Exchanged token verification failed: {verify_result.get('error')}")
            return exchanged_token
            
    except Exception as e:
        print(f"❌ Token exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_token_exchange_chain(okta_auth: OktaAuth, access_token: str):
    """Test chaining token exchanges (like in A2A flow - User → Agents)"""
    print("\n" + "="*60)
    print("TEST 2: Token Exchange Chain (User → Agents)")
    print("="*60)
    print("Simulating Orchestrator exchanging user token for each agent token")
    
    # Define agent audiences (using configurable values from OktaAuth)
    agent_audiences = {
        "HR Agent": okta_auth.hr_audience,
        "Finance Agent": okta_auth.finance_audience,
        "Legal Agent": okta_auth.legal_audience
    }
    
    exchanged_tokens = {}
    
    # Exchange original user token for each agent (using Chat Assistant credentials)
    for agent_name, audience in agent_audiences.items():
        exchanged_token = await test_token_exchange_single(
            okta_auth, 
            access_token, 
            audience, 
            agent_name,
            source_agent=None  # Chat Assistant initiates (user-to-agent)
        )
        if exchanged_token:
            exchanged_tokens[agent_name] = exchanged_token
        else:
            print(f"⚠️ Failed to exchange token for {agent_name}")
            return False
    
    print(f"\n✅ All token exchanges completed!")
    print(f"   Exchanged tokens for {len(exchanged_tokens)} agents")
    
    return True


async def test_cross_agent_exchange(okta_auth: OktaAuth, access_token: str):
    """Test Finance agent exchanging tokens with HR and Legal agents"""
    print("\n" + "="*60)
    print("TEST 3: Cross-Agent Token Exchange (Finance → HR & Legal)")
    print("="*60)
    print("This tests agent-to-agent exchanges using agent service app credentials")
    
    try:
        # Step 1: Exchange original user token for Finance agent token
        print("\n📋 Step 1: Exchange user token for Finance Agent token")
        finance_token = await test_token_exchange_single(
            okta_auth,
            access_token,
            okta_auth.finance_audience,
            "Finance Agent",
            source_agent=None  # Chat Assistant initiates
        )
        
        if not finance_token:
            print("❌ Failed to get Finance agent token")
            return False
        
        # Step 2: Finance agent exchanges its token for HR agent
        # Finance → HR: Uses Finance service app credentials, requests HR scopes
        print("\n📋 Step 2: Finance agent exchanges token for HR agent")
        print("   Using Finance Service App credentials")
        print(f"   Requesting HR server scopes ({OKTA_SCOPES.HR.EMPLOYEES_READ})")
        hr_token = await test_token_exchange_single(
            okta_auth,
            finance_token,
            okta_auth.hr_audience,
            "HR Agent (from Finance)",
            source_agent="finance",  # Finance agent initiates
            expected_scope=get_cross_agent_scope("finance", "hr")  # HR server scope
        )
        
        if hr_token:
            print(f"✅ Finance → HR token exchange successful")
        
        # Step 3: Finance agent exchanges its token for Legal agent
        # Finance → Legal: Uses Finance service app credentials, requests Legal scopes
        print("\n📋 Step 3: Finance agent exchanges token for Legal agent")
        print("   Using Finance Service App credentials")
        print(f"   Requesting Legal server scopes ({OKTA_SCOPES.LEGAL.COMPLIANCE_VERIFY})")
        legal_token = await test_token_exchange_single(
            okta_auth,
            finance_token,
            okta_auth.legal_audience,
            "Legal Agent (from Finance)",
            source_agent="finance",  # Finance agent initiates
            expected_scope=OKTA_SCOPES.LEGAL.COMPLIANCE_VERIFY  # Legal server scope
        )
        
        if legal_token:
            print(f"✅ Finance → Legal token exchange successful")
        
        print(f"\n✅ Cross-agent token exchange test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Cross-agent exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_different_token_types(okta_auth: OktaAuth, access_token: str, id_token: str = None):
    """Test exchanging different token types"""
    print("\n" + "="*60)
    print("TEST 4: Token Exchange with Different Token Types")
    print("="*60)
    
    # Test 1: Exchange access token (default)
    print("\n📋 Test 4.1: Exchange Access Token")
    try:
        result1 = await okta_auth.exchange_token(
            token=access_token,
            target_audience=okta_auth.hr_audience,
            scope=OKTA_SCOPES.HR.EMPLOYEES_READ  # HR server scope
        )
        print(f"✅ Access token exchange successful")
    except Exception as e:
        print(f"❌ Access token exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Exchange ID token (if provided)
    if id_token:
        print("\n📋 Test 4.2: Exchange ID Token")
        try:
            result2 = await okta_auth.exchange_token(
                token=id_token,
                target_audience=okta_auth.finance_audience,
                scope=OKTA_SCOPES.FINANCE.TRANSACTIONS_READ,  # Finance server scope
                subject_token_type="urn:ietf:params:oauth:token-type:id_token"
            )
            print(f"✅ ID token exchange successful")
        except Exception as e:
            print(f"❌ ID token exchange failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


async def main():
    """Main test function"""
    print("\n" + "="*60)
    print("Token Exchange Test Suite")
    print("="*60)
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"\n✅ Loaded environment from: {env_path}")
    else:
        print(f"\n⚠️ No .env file found at {env_path}")
        print("   Please ensure OKTA_DOMAIN, OKTA_CLIENT_ID, and OKTA_CLIENT_SECRET are set")
    
    # Check required environment variables
    required_vars = ["OKTA_DOMAIN"]
    
    # Check for Chat Assistant credentials (or legacy fallback)
    chat_client_id = os.getenv("OKTA_CHAT_ASSISTANT_CLIENT_ID") or os.getenv("OKTA_CLIENT_ID")
    chat_client_secret = os.getenv("OKTA_CHAT_ASSISTANT_CLIENT_SECRET") or os.getenv("OKTA_CLIENT_SECRET")
    
    if not chat_client_id or not chat_client_secret:
        required_vars.append("OKTA_CHAT_ASSISTANT_CLIENT_ID or OKTA_CLIENT_ID")
        required_vars.append("OKTA_CHAT_ASSISTANT_CLIENT_SECRET or OKTA_CLIENT_SECRET")
    
    missing_vars = []
    if not os.getenv("OKTA_DOMAIN"):
        missing_vars.append("OKTA_DOMAIN")
    if not chat_client_id:
        missing_vars.append("OKTA_CHAT_ASSISTANT_CLIENT_ID (or OKTA_CLIENT_ID)")
    if not chat_client_secret:
        missing_vars.append("OKTA_CHAT_ASSISTANT_CLIENT_SECRET (or OKTA_CLIENT_SECRET)")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these in your .env file:")
        print("  OKTA_DOMAIN=your-okta-domain.okta.com")
        print("  OKTA_CHAT_ASSISTANT_CLIENT_ID=your-chat-assistant-service-app-id")
        print("  OKTA_CHAT_ASSISTANT_CLIENT_SECRET=your-chat-assistant-service-app-secret")
        print("\nOptional (for full cross-agent testing):")
        print("  OKTA_HR_SERVICE_CLIENT_ID=your-hr-service-app-id")
        print("  OKTA_HR_SERVICE_CLIENT_SECRET=your-hr-service-app-secret")
        print("  OKTA_FINANCE_SERVICE_CLIENT_ID=your-finance-service-app-id")
        print("  OKTA_FINANCE_SERVICE_CLIENT_SECRET=your-finance-service-app-secret")
        print("  OKTA_LEGAL_SERVICE_CLIENT_ID=your-legal-service-app-id")
        print("  OKTA_LEGAL_SERVICE_CLIENT_SECRET=your-legal-service-app-secret")
        print("\nAuthorization Server IDs (optional, have defaults):")
        print("  OKTA_MAIN_SERVER_ID=default")
        print("  OKTA_HR_SERVER_ID=streamward-hr-server")
        print("  OKTA_FINANCE_SERVER_ID=streamward-finance-server")
        print("  OKTA_LEGAL_SERVER_ID=streamward-legal-server")
        return
    
    # Initialize OktaAuth
    try:
        okta_auth = OktaAuth()
        print(f"\n✅ OktaAuth initialized")
        print(f"   Domain: {okta_auth.okta_domain}")
        print(f"   Chat Assistant Client ID: {okta_auth.client_id}")
        print(f"   Main Auth Server: {okta_auth.main_server_id}")
        
        # Show authorization server mappings
        print(f"\n   Authorization Server Mappings:")
        for audience, server_id in okta_auth.audience_to_server_map.items():
            print(f"      {audience} → {server_id}")
        
        # Show service app configuration status
        print(f"\n   Service App Credentials:")
        print(f"      HR Service App: {'✅ Configured' if okta_auth.hr_service_client_id else '⚠️ Using Chat Assistant'}")
        print(f"      Finance Service App: {'✅ Configured' if okta_auth.finance_service_client_id else '⚠️ Using Chat Assistant'}")
        print(f"      Legal Service App: {'✅ Configured' if okta_auth.legal_service_client_id else '⚠️ Using Chat Assistant'}")
        if not all([okta_auth.hr_service_client_id, okta_auth.finance_service_client_id, okta_auth.legal_service_client_id]):
            print(f"\n   ⚠️ Note: Some agent service apps not configured.")
            print(f"      Cross-agent exchanges will use Chat Assistant credentials as fallback.")
            
    except Exception as e:
        print(f"\n❌ Failed to initialize OktaAuth: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get access token from user or environment
    access_token = os.getenv("TEST_ACCESS_TOKEN")
    id_token = os.getenv("TEST_ID_TOKEN")
    
    if not access_token:
        print("\n" + "="*60)
        print("Access Token Required")
        print("="*60)
        print("\nTo test token exchange, you need a valid Okta access token.")
        print("\nYou can obtain one by:")
        print("  1. Logging in through the frontend and copying the access token")
        print("  2. Using Postman/OAuth2 flow to get a token")
        print("  3. Setting TEST_ACCESS_TOKEN environment variable")
        print("\nEnter your access token (or press Enter to skip token exchange tests):")
        user_token = input().strip()
        if user_token:
            access_token = user_token
        else:
            print("\n⚠️ Skipping token exchange tests (no token provided)")
            print("   You can test token verification separately if you have a token")
            return
    
    # Run tests
    results = []
    
    # Test 1: Token Verification
    if access_token:
        result1 = await test_token_verification(okta_auth, access_token)
        results.append(("Token Verification", result1))
    
    # Test 2: Token Exchange Chain
    if access_token:
        result2 = await test_token_exchange_chain(okta_auth, access_token)
        results.append(("Token Exchange Chain", result2))
    
    # Test 3: Cross-Agent Exchange
    if access_token:
        result3 = await test_cross_agent_exchange(okta_auth, access_token)
        results.append(("Cross-Agent Exchange", result3))
    
    # Test 4: Different Token Types
    if access_token:
        result4 = await test_with_different_token_types(okta_auth, access_token, id_token)
        results.append(("Different Token Types", result4))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())

