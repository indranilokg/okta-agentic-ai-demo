import httpx
import jwt
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class OktaAuth:
    """
    Okta authentication handler for ID token validation and user management
    """
    
    def __init__(self):
        self.domain = os.getenv("OKTA_DOMAIN")
        self.client_id = os.getenv("OKTA_CLIENT_ID")
        self.client_secret = os.getenv("OKTA_CLIENT_SECRET")
        self.redirect_uri = os.getenv("OKTA_REDIRECT_URI")
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Missing required Okta configuration")
        
        self.base_url = f"https://{self.domain}"
        self.jwks_url = f"{self.base_url}/oauth2/default/v1/keys"
        
        # Cache for JWKS
        self._jwks_cache = None
        self._jwks_cache_expiry = None

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
            logger.error(f"Token validation failed: {e}")
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

    async def exchange_token(self, token: str, target_audience: str) -> str:
        """
        Exchange token for different audience (for A2A communication)
        """
        try:
            # This would implement RFC 8693 token exchange
            # For demo purposes, return a mock exchanged token
            
            return f"exchanged-token-for-{target_audience}-{datetime.now().timestamp()}"
            
        except Exception as e:
            logger.error(f"Error exchanging token: {e}")
            raise
