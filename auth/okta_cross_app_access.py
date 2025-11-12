"""
Okta Cross-App Access (ID-JAG) Manager

Enables secure token exchange for MCP access using the new Okta AI SDK.
Implements the 4-step ID-JAG flow:
1. Exchange ID token for ID-JAG token
2. Verify ID-JAG token (optional, for logging)
3. Exchange ID-JAG for authorization server token
4. Verify authorization server token

This module bridges the chat assistant and MCP servers with ID-JAG security.
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from okta_ai_sdk import OktaAISDK, OktaAIConfig, AuthServerTokenRequest
except ImportError as e:
    raise ImportError(
        f"okta-ai-sdk-proto>=1.0.0a6 is required. "
        f"Install with: pip install --upgrade --extra-index-url https://test.pypi.org/simple/ okta-ai-sdk-proto\n"
        f"Error details: {e}"
    )

logger = logging.getLogger(__name__)


class OktaCrossAppAccessManager:
    """
    Manages ID-JAG token exchange for MCP server access.
    
    Usage:
        manager = OktaCrossAppAccessManager()
        mcp_token = await manager.exchange_id_to_mcp_token(user_id_token)
        is_valid = await manager.verify_mcp_token(mcp_token)
    """
    
    def __init__(self):
        """Initialize the Cross-App Access Manager with SDK configuration"""
        self.okta_domain = os.getenv("OKTA_DOMAIN", "").strip()
        if not self.okta_domain:
            raise ValueError("OKTA_DOMAIN environment variable is required")
        
        # Get agent credentials (used for BOTH ID-JAG exchange and MCP token exchange)
        agent_id = os.getenv("OKTA_CHAT_ASSISTANT_AGENT_ID")
        agent_private_key_str = os.getenv("OKTA_CHAT_ASSISTANT_AGENT_PRIVATE_KEY")
        
        if not agent_id or not agent_private_key_str:
            logger.warning(" Chat Assistant Agent credentials not fully configured. ID-JAG exchange will be disabled.")
            self.main_config = None
            self.mcp_config = None
        else:
            try:
                agent_private_key = json.loads(agent_private_key_str) if isinstance(agent_private_key_str, str) else agent_private_key_str
                
                # STEP 1 Config: ID token → ID-JAG token exchange
                # Uses JWT bearer assertion with agent credentials
                # Note: authorization_server_id is "default" because we POST to /oauth2/v1/token
                self.main_config = OktaAIConfig(
                    oktaDomain=self.okta_domain,
                    clientId=agent_id.strip(),  # Required by SDK, actual auth uses JWT bearer
                    clientSecret="",  # Not used with JWT bearer
                    authorizationServerId="default",  # POST to /oauth2/v1/token (default auth server)
                    principalId=agent_id.strip(),  # Service account for JWT assertion
                    privateJWK=agent_private_key  # Key for signing JWT
                )
                logger.info(" Main config loaded for ID-JAG exchange (JWT Bearer)")
                
                # STEP 3 Config: ID-JAG → MCP auth server token exchange
                # Uses JWT bearer assertion with agent credentials
                self.mcp_config = OktaAIConfig(
                    oktaDomain=self.okta_domain,
                    clientId=agent_id.strip(),  # Required by SDK, actual auth uses JWT bearer
                    clientSecret="",  # Not used with JWT bearer
                    authorizationServerId=os.getenv("OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID", "employee-mcp-server").strip(),
                    principalId=agent_id.strip(),  # Service account for JWT assertion
                    privateJWK=agent_private_key  # Key for signing JWT
                )
                logger.info(" MCP config loaded for MCP token exchange (JWT Bearer)")
            except json.JSONDecodeError as e:
                logger.error(f" Failed to parse OKTA_CHAT_ASSISTANT_AGENT_PRIVATE_KEY: {e}")
                self.main_config = None
                self.mcp_config = None
        
        # MCP audience for token targeting
        self.mcp_audience = os.getenv("OKTA_CHAT_ASSISTANT_AGENT_AUDIENCE", "https://employee-mcp-resource-server").strip()
        
        # Initialize SDKs
        self.sdk_main = OktaAISDK(self.main_config)
        self.sdk_mcp = OktaAISDK(self.mcp_config) if self.mcp_config else None
        
        logger.debug(f"[ID-JAG] Initialized: main_org={self.okta_domain}, has_mcp_config={bool(self.mcp_config)}")
    
    async def exchange_id_to_mcp_token(self, user_id_token: str) -> Optional[Dict[str, Any]]:
        """
        Exchange user's ID token for MCP access token using ID-JAG.
        
        4-step process:
        1. ID token → ID-JAG token (org audience)
        2. ID-JAG token verification (optional, for logging)
        3. ID-JAG → MCP auth server token
        4. MCP token verification (in calling code)
        
        Args:
            user_id_token: User's ID token from Okta
            
        Returns:
            Dict with access_token, expires_in, and token_type, or None if failed
        """
        try:
            if not self.sdk_mcp:
                logger.error(" MCP SDK not configured. ID-JAG exchange not available.")
                return None
            
            logger.debug("[ID-JAG] Starting token exchange")
            
            # STEP 1: Exchange ID token for ID-JAG token
            id_jag_audience = f"{self.okta_domain}/oauth2/{self.mcp_config.authorization_server_id}"
            logger.debug(f"[ID-JAG] STEP 1: Exchanging to {id_jag_audience}")
            
            try:
                id_jag_result = self.sdk_main.cross_app_access.exchange_id_token(
                    id_token=user_id_token,
                    audience=id_jag_audience,
                    scope="mcp:read"
                )
                logger.info(f"[ID-JAG] STEP 1 SUCCESS: expires_in={id_jag_result.expires_in}s")
                logger.debug(f"[ID-JAG] ID-JAG token (first 50): {id_jag_result.access_token[:50]}...")
                logger.debug(f"[ID-JAG] Full ID-JAG token: {id_jag_result.access_token}")
            except Exception as e:
                logger.error(f"[ID-JAG] STEP 1 FAILED: {str(e)}", exc_info=True)
                return None
            
            # STEP 2: Verify ID-JAG token (optional, for audit trail)
            logger.debug("[ID-JAG] STEP 2: Verifying ID-JAG token")
            try:
                verification_result = self.sdk_main.cross_app_access.verify_id_jag_token(
                    token=id_jag_result.access_token,
                    audience=id_jag_audience
                )
                
                if verification_result.valid:
                    logger.debug(f"[ID-JAG] STEP 2 SUCCESS: sub={verification_result.sub}")
                else:
                    logger.warning(f"[ID-JAG] STEP 2 verification warning: {verification_result.error}")
            except Exception as e:
                logger.debug(f"[ID-JAG] STEP 2 verification skipped: {e}")
            
            # STEP 3: Exchange ID-JAG for authorization server token (MCP access token)
            logger.debug("[ID-JAG] STEP 3: Exchanging ID-JAG for MCP token")
            mcp_auth_server_id = self.mcp_config.authorization_server_id
            
            try:
                auth_server_request = AuthServerTokenRequest(
                    id_jag_token=id_jag_result.access_token,
                    authorization_server_id=mcp_auth_server_id,
                    principal_id=self.mcp_config.principal_id,
                    private_jwk=self.mcp_config.private_jwk
                )
                
                mcp_token_result = self.sdk_mcp.cross_app_access.exchange_id_jag_for_auth_server_token(
                    auth_server_request
                )
                logger.info(f"[ID-JAG] STEP 3 SUCCESS: MCP_token expires_in={mcp_token_result.expires_in}s, scope={getattr(mcp_token_result, 'scope', 'N/A')}")
                logger.debug(f"[ID-JAG] MCP token (first 50): {mcp_token_result.access_token[:50]}...")
                logger.debug(f"[ID-JAG] Full MCP token: {mcp_token_result.access_token}")
            except Exception as e:
                error_msg = str(e)
                # Check for timeout errors
                if "Read timed out" in error_msg or "timeout" in error_msg.lower():
                    logger.error(f"[ID-JAG] STEP 3 TIMEOUT: Okta server is not responding. Please try again.", exc_info=False)
                else:
                    logger.error(f"[ID-JAG] STEP 3 FAILED: {error_msg}", exc_info=True)
                return None
            
            # Return token info for MCP tool context (including ID-JAG token for frontend display)
            return {
                "access_token": mcp_token_result.access_token,
                "id_jag_token": id_jag_result.access_token,  # Intermediate ID-JAG token for display
                "token_type": getattr(mcp_token_result, "token_type", "Bearer"),
                "expires_in": mcp_token_result.expires_in,
                "scope": getattr(mcp_token_result, "scope", None),
                "id_jag_subject": verification_result.sub if 'verification_result' in locals() and verification_result.valid else None,
                "exchanged_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f" ID-JAG exchange failed: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def verify_mcp_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify MCP authorization server token.
        
        STEP 4: Verify the token is valid before granting MCP access
        
        Args:
            access_token: The MCP access token from exchange_id_to_mcp_token
            
        Returns:
            Dict with token claims if valid, None if invalid
        """
        try:
            if not self.sdk_mcp:
                logger.error(" MCP SDK not configured. Token verification not available.")
                return None
            
            logger.debug("[ID-JAG] STEP 4: Verifying MCP token")
            
            mcp_auth_server_id = self.mcp_config.authorization_server_id
            
            try:
                verification_result = self.sdk_mcp.cross_app_access.verify_auth_server_token(
                    token=access_token,
                    authorization_server_id=mcp_auth_server_id,
                    audience=self.mcp_audience
                )
                
                if verification_result.valid:
                    logger.info(f"[ID-JAG] STEP 4 SUCCESS: sub={verification_result.sub}, scope={verification_result.scope}")
                    logger.debug(f"[ID-JAG] Token claims: aud={verification_result.aud}, iss={verification_result.iss}")
                    
                    return {
                        "valid": True,
                        "sub": verification_result.sub,
                        "aud": verification_result.aud,
                        "iss": verification_result.iss,
                        "scope": verification_result.scope,
                        "exp": verification_result.exp,
                        "payload": verification_result.payload
                    }
                else:
                    logger.error(f"[ID-JAG] STEP 4 FAILED: Token verification error: {verification_result.error}")
                    return None
                    
            except Exception as e:
                logger.error(f"[ID-JAG] STEP 4 FAILED: {str(e)}", exc_info=True)
                return None
                
        except Exception as e:
            logger.error(f" Token verification failed: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_mcp_bearer_token(self, access_token: str) -> str:
        """
        Get the Bearer token header format for HTTP requests to MCP
        
        Args:
            access_token: The MCP access token
            
        Returns:
            Formatted Bearer token header value
        """
        return f"Bearer {access_token}"

