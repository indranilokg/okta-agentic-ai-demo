"""
Okta Token Validation for FastAPI
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from okta_jwt_verifier import IDTokenVerifier, AccessTokenVerifier
import requests

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

class OktaTokenValidator:
    """Validates Okta JWT tokens"""
    
    def __init__(self):
        self.okta_domain = os.getenv('OKTA_DOMAIN')
        self.client_id = os.getenv('OKTA_CLIENT_ID')
        self.audience = os.getenv('OKTA_AUDIENCE')
        # No default path - will use issuer from token
        self.issuer = None  # Will be set from token
        self.verifier = None  # Will be initialized on first token
        
        # Verifier will be initialized lazily from the first token
        logger.debug("Okta validator initialized (lazy initialization from token)")
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate Okta JWT token and return user info"""
        
        # Special test token for demonstration
        if token == "test-token-demo-user":
            logger.info("✅ Using test token for demonstration")
            return {
                'sub': 'test-user-123',
                'email': 'demo@streamward.com',
                'name': 'Demo User',
                'given_name': 'Demo',
                'family_name': 'User',
                'groups': ['employees', 'demo-users'],
                'claims': {'test': True}
            }
        
        try:
            logger.debug(f"Validating token: {token}")
            
            # Decode the token (without verification) to get issuer, audience, and claims
            import jwt as pyjwt
            decoded = pyjwt.decode(token, options={"verify_signature": False})
            actual_issuer = decoded.get('iss')
            actual_audience = decoded.get('aud')
            logger.info(f"Token issuer: {actual_issuer}, audience: {actual_audience}")
            
            # Initialize or update verifier if needed
            if not self.verifier or self.issuer != actual_issuer:
                logger.info(f"Initializing verifier with issuer: {actual_issuer}")
                
                # Determine token type based on audience:
                # - URLs (http://, https://) → Access tokens
                # - API audiences (api://) → Access tokens
                # - Client IDs (0oa...) → Could be ID token or access token, check token type
                # - Default: Try ID token verifier first, fall back if needed
                is_access_token_audience = (
                    (actual_audience and (actual_audience.startswith('http://') or actual_audience.startswith('https://'))) or
                    (actual_audience and actual_audience.startswith('api://'))
                )
                
                if is_access_token_audience:
                    # Use AccessTokenVerifier for access tokens
                    self.verifier = AccessTokenVerifier(
                        issuer=actual_issuer,
                        audience=actual_audience
                    )
                    logger.info(f"✅ Using AccessTokenVerifier with audience: {actual_audience}")
                else:
                    # For other audiences, try IDTokenVerifier
                    # If audience looks like a client ID (0oa...), use it directly
                    # Otherwise, use configured client_id
                    client_id_to_use = actual_audience if actual_audience and actual_audience.startswith('0oa') else (self.client_id or actual_audience)
                    self.verifier = IDTokenVerifier(
                        issuer=actual_issuer,
                        client_id=client_id_to_use
                    )
                    logger.info(f"✅ Using IDTokenVerifier with client_id: {client_id_to_use}")
                
                self.issuer = actual_issuer
            
            # Verify the token - this validates signature, expiry, etc.
            # AccessTokenVerifier.verify() may return None on success (just validates, doesn't return claims)
            try:
                verify_result = await self.verifier.verify(token)
                
                # If verify() returns None, validation passed - use the already-decoded claims
                # If it returns a dict, use those claims
                if verify_result is None:
                    logger.debug("verify() returned None - validation passed, using pre-decoded claims")
                    jwt_claims = decoded  # Use the claims we decoded earlier
                elif isinstance(verify_result, dict):
                    jwt_claims = verify_result
                else:
                    logger.error(f"Unexpected verify result type: {type(verify_result)}")
                    return None
            except Exception as verify_error:
                logger.error(f"Token verification failed: {verify_error}")
                return None
            
            if not jwt_claims:
                logger.error("Token verification returned empty claims")
                return None
            
            logger.debug(f"Token claims keys: {list(jwt_claims.keys())}")
            logger.debug(f"Token claims email field: {jwt_claims.get('email')}")
            logger.debug(f"Token claims preferred_username: {jwt_claims.get('preferred_username')}")
            logger.debug(f"Token claims sub: {jwt_claims.get('sub')}")
            
            # Extract user information
            # Try multiple possible email fields
            email = (
                jwt_claims.get('email') or 
                jwt_claims.get('preferred_username') or
                jwt_claims.get('upn') or
                jwt_claims.get('sub')  # Fallback to sub if it looks like an email
            )
            
            # If sub looks like an email, use it
            if email and '@' in str(email):
                pass  # Already have email
            elif jwt_claims.get('sub') and '@' in str(jwt_claims.get('sub')):
                email = jwt_claims.get('sub')
            
            user_info = {
                'sub': jwt_claims.get('sub'),
                'email': email,
                'name': jwt_claims.get('name'),
                'given_name': jwt_claims.get('given_name'),
                'family_name': jwt_claims.get('family_name'),
                'groups': jwt_claims.get('groups', []),
                'claims': jwt_claims
            }
            
            logger.info(f"✅ Token validated for user: {user_info['email']} (sub: {user_info.get('sub')})")
            logger.debug(f"Full user info: {user_info}")
            return user_info
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            import traceback
            logger.debug(f"Validation error traceback: {traceback.format_exc()}")
            return None

# Global validator instance
token_validator = OktaTokenValidator()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user from Okta token"""
    token = credentials.credentials
    
    # Validate token
    user_info = await token_validator.validate_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user_info.get('email'):
        raise HTTPException(
            status_code=401,
            detail="User email not found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Optional dependency for endpoints that work with or without authentication"""
    if not credentials:
        logger.debug("No authorization credentials provided - will use demo user")
        return None
    
    token = credentials.credentials
    logger.debug(f"Received token (first 20 chars): {token[:20]}...")
    
    user_info = await token_validator.validate_token(token)
    
    if not user_info:
        logger.warning("Token validation returned None - will use demo user")
    else:
        logger.info(f"Token validation successful for: {user_info.get('email')}")
    
    return user_info
