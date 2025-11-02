import httpx
import jwt
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class Auth0Auth:
    """
    Auth0 authentication handler for partner management system access
    """
    
    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.client_id = os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET")
        self.audience = os.getenv("AUTH0_AUDIENCE")
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Missing required Auth0 configuration")
        
        self.base_url = f"https://{self.domain}"
        self.jwks_url = f"{self.base_url}/.well-known/jwks.json"
        
        # Cache for JWKS
        self._jwks_cache = None
        self._jwks_cache_expiry = None

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Auth0 access token and return user information
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
                audience=self.audience,
                issuer=f"{self.base_url}/"
            )
            
            # Validate token expiration
            if datetime.fromtimestamp(payload.get("exp", 0)) < datetime.now():
                raise ValueError("Token has expired")
            
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "nickname": payload.get("nickname"),
                "permissions": payload.get("permissions", []),
                "roles": payload.get("roles", []),
                "token_type": "auth0_access_token",
                "validated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Auth0 token validation failed: {e}")
            raise ValueError(f"Invalid Auth0 token: {str(e)}")

    async def _get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS from Auth0 with caching
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

    async def get_access_token(self, client_credentials: bool = True) -> str:
        """
        Get Auth0 access token using client credentials flow
        """
        try:
            async with httpx.AsyncClient() as client:
                if client_credentials:
                    # Client credentials flow
                    data = {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "audience": self.audience,
                        "grant_type": "client_credentials"
                    }
                else:
                    # This would be for other flows like authorization code
                    raise NotImplementedError("Only client credentials flow implemented")
                
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                
                token_data = response.json()
                return token_data["access_token"]
                
        except Exception as e:
            logger.error(f"Error getting Auth0 access token: {e}")
            raise

    async def get_partner_info(self, partner_id: str, access_token: str) -> Dict[str, Any]:
        """
        Get partner information from Auth0-secured system
        """
        try:
            # This would call the actual partner management API
            # For demo purposes, return mock data
            
            mock_partners = {
                "partner-001": {
                    "id": "partner-001",
                    "name": "TechCorp Solutions",
                    "type": "Technology Partner",
                    "sla_level": "Premium",
                    "contract_status": "Active",
                    "contact_email": "partnerships@techcorp.com",
                    "integration_tokens": ["api-token-001", "webhook-token-001"],
                    "last_activity": "2024-01-15T10:30:00Z"
                },
                "partner-002": {
                    "id": "partner-002", 
                    "name": "FinanceFlow Inc",
                    "type": "Financial Services",
                    "sla_level": "Standard",
                    "contract_status": "Active",
                    "contact_email": "business@financeflow.com",
                    "integration_tokens": ["api-token-002"],
                    "last_activity": "2024-01-14T15:45:00Z"
                }
            }
            
            return mock_partners.get(partner_id, {
                "id": partner_id,
                "name": f"Partner {partner_id}",
                "type": "Unknown",
                "sla_level": "Basic",
                "contract_status": "Unknown",
                "contact_email": "unknown@partner.com",
                "integration_tokens": [],
                "last_activity": None
            })
            
        except Exception as e:
            logger.error(f"Error getting partner info: {e}")
            raise

    async def list_partners(self, access_token: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all partners from Auth0-secured system
        """
        try:
            # Mock data for demo
            partners = [
                {
                    "id": "partner-001",
                    "name": "TechCorp Solutions",
                    "type": "Technology Partner",
                    "sla_level": "Premium",
                    "contract_status": "Active"
                },
                {
                    "id": "partner-002",
                    "name": "FinanceFlow Inc", 
                    "type": "Financial Services",
                    "sla_level": "Standard",
                    "contract_status": "Active"
                },
                {
                    "id": "partner-003",
                    "name": "LegalEase Partners",
                    "type": "Legal Services",
                    "sla_level": "Premium",
                    "contract_status": "Pending"
                }
            ]
            
            return partners[:limit]
            
        except Exception as e:
            logger.error(f"Error listing partners: {e}")
            raise

    async def update_partner(self, partner_id: str, updates: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """
        Update partner information
        """
        try:
            # Mock implementation
            partner_info = await self.get_partner_info(partner_id, access_token)
            partner_info.update(updates)
            partner_info["updated_at"] = datetime.now().isoformat()
            
            return partner_info
            
        except Exception as e:
            logger.error(f"Error updating partner: {e}")
            raise

    def create_dpop_proof(self, method: str, url: str, access_token: str) -> str:
        """
        Create DPOP proof for Auth0-protected resources
        """
        try:
            # Simplified DPOP implementation
            dpop_payload = {
                "htu": url,
                "htm": method.upper(),
                "iat": int(datetime.now().timestamp()),
                "jti": f"auth0-dpop-{datetime.now().timestamp()}"
            }
            
            # In production, sign with private key
            dpop_token = jwt.encode(
                dpop_payload,
                "auth0-dpop-secret-key",  # Use actual private key
                algorithm="HS256"
            )
            
            return dpop_token
            
        except Exception as e:
            logger.error(f"Error creating Auth0 DPOP proof: {e}")
            raise

    async def exchange_token_for_cross_app_access(self, token: str, target_app: str) -> str:
        """
        Exchange token for cross-app access (ID-JAG pattern)
        """
        try:
            # This would implement cross-app access token exchange
            # For demo purposes, return a mock exchanged token
            
            return f"cross-app-token-{target_app}-{datetime.now().timestamp()}"
            
        except Exception as e:
            logger.error(f"Error exchanging token for cross-app access: {e}")
            raise
