import httpx
import jwt
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
from urllib.parse import urljoin

# Okta AI SDK imports
from okta_ai_sdk import OktaAISDK, OktaAIConfig, TokenExchangeRequest
from okta_ai_sdk.types.token_exchange import TokenVerificationOptions
from auth.okta_scopes import OKTA_SCOPES, get_default_hr_scopes, get_default_finance_scopes

logger = logging.getLogger(__name__)

class OktaAuth:
    """
    Okta authentication handler for ID token validation and user management
    Supports multiple authorization servers for agent-to-agent token exchange
    """
    
    def __init__(self):
        self.domain = os.getenv("OKTA_DOMAIN")
        
        # Main authorization server (for user authentication)
        self.main_server_id = os.getenv("OKTA_MAIN_SERVER_ID", "default")
        
        # Service app credentials for Chat Assistant (used for token exchanges)
        self.client_id = os.getenv("OKTA_CHAT_ASSISTANT_CLIENT_ID") or os.getenv("OKTA_CLIENT_ID")
        self.client_secret = os.getenv("OKTA_CHAT_ASSISTANT_CLIENT_SECRET") or os.getenv("OKTA_CLIENT_SECRET")
        
        # Agent-specific service app credentials
        self.hr_service_client_id = os.getenv("OKTA_HR_SERVICE_CLIENT_ID")
        self.hr_service_client_secret = os.getenv("OKTA_HR_SERVICE_CLIENT_SECRET")
        self.finance_service_client_id = os.getenv("OKTA_FINANCE_SERVICE_CLIENT_ID")
        self.finance_service_client_secret = os.getenv("OKTA_FINANCE_SERVICE_CLIENT_SECRET")
        self.legal_service_client_id = os.getenv("OKTA_LEGAL_SERVICE_CLIENT_ID")
        self.legal_service_client_secret = os.getenv("OKTA_LEGAL_SERVICE_CLIENT_SECRET")
        
        self.redirect_uri = os.getenv("OKTA_REDIRECT_URI")
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Missing required Okta configuration (domain, client_id, client_secret)")
        
        # Handle domain format (with or without https://)
        if self.domain.startswith("http://") or self.domain.startswith("https://"):
            self.okta_domain = self.domain
        else:
            self.okta_domain = f"https://{self.domain}"
        
        self.base_url = self.okta_domain
        self.jwks_url = f"{self.base_url}/oauth2/default/v1/keys"
        
        # Cache for JWKS
        self._jwks_cache = None
        self._jwks_cache_expiry = None
        
        # Map audiences to authorization server IDs
        # Each authorization server has one audience
        # Audiences are configurable via environment variables
        hr_server_id = os.getenv("OKTA_HR_SERVER_ID", "streamward-hr-server")
        finance_server_id = os.getenv("OKTA_FINANCE_SERVER_ID", "streamward-finance-server")
        legal_server_id = os.getenv("OKTA_LEGAL_SERVER_ID", "streamward-legal-server")
        
        # Configurable audiences (defaults to match Okta setup)
        main_audience = os.getenv("OKTA_MAIN_AUDIENCE", "api://streamward-chat")
        hr_audience = os.getenv("OKTA_HR_AUDIENCE", "hr-agent-audience")
        finance_audience = os.getenv("OKTA_FINANCE_AUDIENCE", "finance-agent-audience")
        legal_audience = os.getenv("OKTA_LEGAL_AUDIENCE", "legal-agent-audience")
        
        # Store audiences for reference
        self.main_audience = main_audience
        self.hr_audience = hr_audience
        self.finance_audience = finance_audience
        self.legal_audience = legal_audience
        
        self.audience_to_server_map = {
            main_audience: self.main_server_id,
            hr_audience: hr_server_id,
            finance_audience: finance_server_id,
            legal_audience: legal_server_id,
        }
        
        # Map audiences to service app credentials (for cross-agent exchanges)
        # Default to Chat Assistant credentials if agent-specific not configured
        # Uses configurable audiences from environment variables
        self.audience_to_service_app: Dict[str, Dict[str, str]] = {
            hr_audience: {
                "client_id": self.hr_service_client_id or self.client_id,
                "client_secret": self.hr_service_client_secret or self.client_secret
            },
            finance_audience: {
                "client_id": self.finance_service_client_id or self.client_id,
                "client_secret": self.finance_service_client_secret or self.client_secret
            },
            legal_audience: {
                "client_id": self.legal_service_client_id or self.client_id,
                "client_secret": self.legal_service_client_secret or self.client_secret
            }
        }
        
        # Default SDK config (for main server operations)
        if not all([self.okta_domain, self.client_id, self.client_secret]):
            logger.error(f"Missing SDK config: okta_domain={self.okta_domain}, client_id={self.client_id}, client_secret={self.client_secret is not None}")
            raise ValueError("Missing required Okta configuration for SDK initialization")
        
        # Create OktaAIConfig object with snake_case field names
        sdk_config = OktaAIConfig(
            okta_domain=self.okta_domain,
            client_id=self.client_id,
            client_secret=self.client_secret,
            authorization_server_id=self.main_server_id
        )
        self.sdk = OktaAISDK(sdk_config)
        
        # Cache for per-server SDK instances
        self._server_sdks: Dict[str, OktaAISDK] = {}

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Okta ID token and return user information
        """
        try:
            # Decode token header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                raise ValueError("Token missing key ID")
            
            # Get JWKS
            jwks = await self._get_jwks()
            
            # Find the correct key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                raise ValueError("Unable to find matching key")
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"{self.base_url}/oauth2/default"
            )
            
            # Validate token expiration
            if datetime.fromtimestamp(payload.get("exp", 0)) < datetime.now():
                raise ValueError("Token has expired")
            
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "preferred_username": payload.get("preferred_username"),
                "groups": payload.get("groups", []),
                "department": payload.get("department"),
                "title": payload.get("title"),
                "token_type": "okta_id_token",
                "validated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[TOKEN_VALIDATION] FAILED: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid token: {str(e)}")

    async def _get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS from Okta with caching
        """
        # Check cache
        if (self._jwks_cache and 
            self._jwks_cache_expiry and 
            datetime.now() < self._jwks_cache_expiry):
            return self._jwks_cache
        
        # Fetch fresh JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Cache for 1 hour
            self._jwks_cache = jwks
            self._jwks_cache_expiry = datetime.now() + timedelta(hours=1)
            
            return jwks

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information from Okta
        """
        try:
            # This would require an access token in production
            # For demo purposes, we'll return mock data
            return {
                "id": user_id,
                "email": f"user{user_id}@streamward.com",
                "name": f"User {user_id}",
                "department": "Engineering",
                "title": "Software Engineer",
                "groups": ["employees", "engineering"],
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise

    async def get_user_groups(self, user_id: str) -> List[str]:
        """
        Get user groups from Okta
        """
        try:
            user_info = await self.get_user_info(user_id)
            return user_info.get("groups", [])
            
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    def create_dpop_proof(self, method: str, url: str, access_token: str) -> str:
        """
        Create DPOP proof for protected resource access
        """
        try:
            # This is a simplified implementation
            # In production, you'd use proper cryptographic signing
            
            dpop_payload = {
                "htu": url,
                "htm": method.upper(),
                "iat": int(datetime.now().timestamp()),
                "jti": f"dpop-{datetime.now().timestamp()}"
            }
            
            # In production, sign with private key
            dpop_token = jwt.encode(
                dpop_payload,
                "dpop-secret-key",  # Use actual private key
                algorithm="HS256"
            )
            
            return dpop_token
            
        except Exception as e:
            logger.error(f"Error creating DPOP proof: {e}")
            raise

    def _get_sdk_for_server(self, authorization_server_id: str, client_id: str, client_secret: str) -> OktaAISDK:
        """
        Get or create SDK instance for a specific authorization server
        """
        cache_key = f"{authorization_server_id}:{client_id}"
        if cache_key not in self._server_sdks:
            sdk_config = OktaAIConfig(
                okta_domain=self.okta_domain,
                client_id=client_id,
                client_secret=client_secret,
                authorization_server_id=authorization_server_id
            )
            self._server_sdks[cache_key] = OktaAISDK(sdk_config)
        return self._server_sdks[cache_key]
    
    async def exchange_token(
        self, 
        token: str, 
        target_audience: str,
        scope: Optional[str] = None,
        subject_token_type: Optional[str] = None,
        source_agent: Optional[str] = None
    ) -> str:
        """
        Exchange token for different audience using RFC 8693 Token Exchange
        This is used for A2A (Agent-to-Agent) communication.
        
        Args:
            token: The subject token to exchange (access token or ID token)
            target_audience: The target audience for the new token
            scope: Optional scope for the new token (must match target server's scopes)
            subject_token_type: Type of the input token (defaults to access_token)
                              Options: "urn:ietf:params:oauth:token-type:access_token" 
                                      or "urn:ietf:params:oauth:token-type:id_token"
            source_agent: Optional agent name ("hr", "finance", "legal") for cross-agent exchanges.
                         If provided, uses that agent's service app credentials.
                         If None, uses Chat Assistant credentials (for user-to-agent exchanges)
        
        Returns:
            The exchanged access token
        
        Example:
            ```python
            # Chat Assistant exchanging user token for HR agent token
            hr_token = await okta_auth.exchange_token(
                token=user_access_token,
                target_audience="hr-agent-audience",
                scope=get_default_hr_scopes()  # Uses centralized scope constants
            )
            
            # HR agent exchanging its token for Finance agent token
            finance_token = await okta_auth.exchange_token(
                token=hr_agent_token,
                target_audience="finance-agent-audience",
                scope=OKTA_SCOPES.FINANCE.TRANSACTIONS_READ,  # Uses centralized scope constants
                source_agent="hr"  # Uses HR service app credentials
            )
            ```
        """
        try:
            logger.info(f"[TOKEN_EXCHANGE] Starting: audience={target_audience}, scope={scope}, source_agent={source_agent or 'user-to-agent'}")
            
            # Determine which authorization server to use based on target audience
            authorization_server_id = self.audience_to_server_map.get(target_audience)
            if not authorization_server_id:
                raise ValueError(f"No authorization server mapped for audience: {target_audience}")
            
            # Determine which service app credentials to use based on source agent
            if source_agent:
                # Cross-agent exchange - use source agent's service app credentials
                agent_cred_map = {
                    "hr": {
                        "client_id": self.hr_service_client_id or self.client_id,
                        "client_secret": self.hr_service_client_secret or self.client_secret
                    },
                    "finance": {
                        "client_id": self.finance_service_client_id or self.client_id,
                        "client_secret": self.finance_service_client_secret or self.client_secret
                    },
                    "legal": {
                        "client_id": self.legal_service_client_id or self.client_id,
                        "client_secret": self.legal_service_client_secret or self.client_secret
                    }
                }
                if source_agent.lower() in agent_cred_map:
                    service_creds = agent_cred_map[source_agent.lower()]
                    client_id = service_creds["client_id"]
                    client_secret = service_creds["client_secret"]
                    logger.info(f"[TOKEN_EXCHANGE] Using {source_agent} service app credentials")
                else:
                    # Fallback to Chat Assistant if invalid source_agent
                    client_id = self.client_id
                    client_secret = self.client_secret
                    logger.warning(f"[TOKEN_EXCHANGE] Unknown source_agent '{source_agent}', using Chat Assistant credentials")
            else:
                # User-to-agent exchange - use Chat Assistant credentials (default)
                client_id = self.client_id
                client_secret = self.client_secret
                logger.info(f"[TOKEN_EXCHANGE] Using Chat Assistant credentials for user-to-agent exchange")
            
            # Get SDK instance for this authorization server
            sdk = self._get_sdk_for_server(authorization_server_id, client_id, client_secret)
            
            # Determine subject token type (what we're exchanging FROM)
            input_token_type = subject_token_type or "urn:ietf:params:oauth:token-type:access_token"
            
            # Create token exchange request
            exchange_request = TokenExchangeRequest(
                subject_token=token,
                subject_token_type=input_token_type,
                audience=target_audience,
                scope=scope
            )
            
            logger.info(f"[TOKEN_EXCHANGE] Calling {self.okta_domain}/oauth2/{authorization_server_id}/v1/token")
            
            # Perform token exchange using the appropriate SDK
            exchange_response = sdk.token_exchange.exchange_token(exchange_request)
            
            logger.info(f"[TOKEN_EXCHANGE] SUCCESS: type={exchange_response.issued_token_type}, expires={exchange_response.expires_in}s")
            logger.debug(f"[TOKEN_EXCHANGE] Generated token (first 50 chars): {exchange_response.access_token[:50]}...")
            logger.debug(f"[TOKEN_EXCHANGE] Full token: {exchange_response.access_token}")
            
            return exchange_response.access_token
            
        except Exception as e:
            logger.error(f"[TOKEN_EXCHANGE] FAILED: audience={target_audience}, error={str(e)}", exc_info=True)
            raise ValueError(f"Token exchange failed: {str(e)}")
    
    def verify_token(self, token: str, issuer: Optional[str] = None, audience: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify token using SDK's verify_token method
        Follows the same pattern as the SDK sample usage.
        
        Args:
            token: The token to verify (access token)
            issuer: Expected issuer (defaults to configured Okta domain)
            audience: Expected audience (defaults to configured client_id)
        
        Returns:
            Dictionary with verification result including 'valid', 'sub', 'email', etc.
        
        Example:
            ```python
            # Verify access token
            result = okta_auth.verify_token(
                token=access_token,
                issuer="https://your-domain.okta.com",
                audience="api://default"
            )
            if result.get('valid'):
                print(f"User authenticated: {result.get('sub')}")
            ```
        """
        try:
            # Use SDK's verify_token method (following sample pattern)
            # Create TokenVerificationOptions object (not dict)
            verification_options = TokenVerificationOptions(
                issuer=issuer or f"{self.okta_domain}/oauth2/{self.authorization_server_id}",
                audience=audience or self.client_id
            )
            
            verification_result = self.sdk.token_exchange.verify_token(
                token=token,
                options=verification_options
            )
            
            # Convert SDK result to dict format
            return {
                "valid": verification_result.valid,
                "sub": verification_result.sub,
                "email": verification_result.email,
                "aud": verification_result.aud,
                "iss": verification_result.iss,
                "exp": verification_result.exp,
                "scope": verification_result.scope,
                "payload": verification_result.payload,
                "error": verification_result.error
            }
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
