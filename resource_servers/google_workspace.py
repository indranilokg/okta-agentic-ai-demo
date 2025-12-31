import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
import requests

try:
    from okta_ai_sdk import OktaAISDK, OktaAIConfig, Auth0Config, GetExternalProviderTokenRequest, CompleteLinkingAndGetTokenRequest
except ImportError as e:
    raise ImportError(
        f"okta-ai-sdk-proto>=1.0.0 is required for Connected Accounts. "
        f"Install with: pip install --upgrade okta-ai-sdk-proto\n"
        f"Error details: {e}"
    )

from auth.okta_auth import OktaAuth
from auth.okta_cross_app_access import OktaCrossAppAccessManager

logger = logging.getLogger(__name__)

class GoogleWorkspaceResourceServer:
    """
    Resource Server for Google Workspace (Okta-secured with Connected Accounts)
    
    Features:
    - Handles Google Workspace resources (Calendar, Gmail, Drive, etc.)
    - Uses Connected Accounts SDK to get Google tokens from Auth0 vault
    - If token not in vault, initiates account linking flow
    - Provides audit trail with token claims (subject, scope, expiration)
    - **Multi-user support**: Stores auth_session server-side, keyed by user's Okta sub
    
    Token Flow:
    1. Chat Assistant exchanges access token for ID-JAG token
    2. Chat Assistant exchanges ID-JAG for authorization server access token
    3. Resource Server uses Connected Accounts SDK to get Google token from vault
    4. If token not found, returns authorization URL for account linking
    5. After linking, token is stored in vault and used for Google API calls
    
    Multi-User Architecture:
    - auth_session is stored server-side, keyed by user's Okta 'sub' (subject)
    - This ensures each user's linking state is isolated
    - Frontend doesn't need to store auth_session - backend retrieves it from user's session
    """
    
    def __init__(self):
        self.okta_auth = OktaAuth()
        self.cross_app_access_manager = OktaCrossAppAccessManager()
        self.calendar_data = self._initialize_mock_calendar_data()
        self.tools = self._define_tools()
        
        # Auth0 Connected Accounts configuration
        self.auth0_config = self._initialize_auth0_config()
        self.connection = os.getenv("GOOGLE_CONNECTION_NAME", "google-oauth2")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/api/resource/google-workspace/callback")
        
        # In-memory store for auth_sessions (keyed by user's Okta 'sub')
        # In production, use Redis or database for persistence across restarts
        self._auth_sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(" GoogleWorkspaceResourceServer initialized with Connected Accounts support (multi-user)")
    
    def _initialize_auth0_config(self) -> Optional[Auth0Config]:
        """Initialize Auth0 configuration for Connected Accounts"""
        try:
            token_endpoint = os.getenv("AUTH0_TOKEN_ENDPOINT")
            myaccount_connect_endpoint = os.getenv("AUTH0_MYACCOUNT_CONNECT_ENDPOINT")
            myaccount_complete_endpoint = os.getenv("AUTH0_MYACCOUNT_COMPLETE_ENDPOINT")
            vault_audience = os.getenv("AUTH0_VAULT_AUDIENCE")
            myaccount_audience = os.getenv("AUTH0_MYACCOUNT_AUDIENCE")
            vault_token_type = os.getenv("AUTH0_VAULT_TOKEN_TYPE", "urn:okta-token")
            vault_scope = os.getenv("AUTH0_VAULT_SCOPE", "read:vault")
            vault_client_id = os.getenv("AUTH0_VAULT_CLIENT_ID")
            vault_client_secret = os.getenv("AUTH0_VAULT_CLIENT_SECRET")
            myaccount_client_id = os.getenv("AUTH0_MYACCOUNT_CLIENT_ID")
            myaccount_client_secret = os.getenv("AUTH0_MYACCOUNT_CLIENT_SECRET")
            
            if not all([token_endpoint, myaccount_connect_endpoint, myaccount_complete_endpoint, 
                       vault_audience, myaccount_audience, vault_client_id, vault_client_secret,
                       myaccount_client_id, myaccount_client_secret]):
                logger.warning(" Auth0 Connected Accounts configuration incomplete - Google Workspace features disabled")
                return None
            
            return Auth0Config(
                token_endpoint=token_endpoint,
                myaccount_connect_endpoint=myaccount_connect_endpoint,
                myaccount_complete_endpoint=myaccount_complete_endpoint,
                vault_audience=vault_audience,
                myaccount_audience=myaccount_audience,
                vault_token_type=vault_token_type,
                vault_scope=vault_scope,
                vault_client_id=vault_client_id,
                vault_client_secret=vault_client_secret,
                myaccount_client_id=myaccount_client_id,
                myaccount_client_secret=myaccount_client_secret
            )
        except Exception as e:
            logger.error(f" Failed to initialize Auth0 config: {e}")
            return None
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available resource tools for Google Workspace"""
        return [
            {
                "name": "get_calendar_events",
                "description": "Get calendar events from Google Calendar. Can filter by date range, calendar ID, or event status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date for calendar query in ISO format (YYYY-MM-DD). Default: 1 month ago",
                            "format": "date"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for calendar query in ISO format (YYYY-MM-DD). Default: today",
                            "format": "date"
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Optional: Specific calendar ID. If not provided, uses primary calendar.",
                            "default": "primary"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of events to return. Default: 50",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 2500
                        }
                    }
                }
            },
            {
                "name": "create_calendar_event",
                "description": "Create a new calendar event in Google Calendar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Event title/summary",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Event start time in ISO 8601 format (e.g., 2025-11-10T14:00:00)",
                            "format": "date-time"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "Event end time in ISO 8601 format (e.g., 2025-11-10T15:00:00)",
                            "format": "date-time"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional event description"
                        },
                        "location": {
                            "type": "string",
                            "description": "Optional event location"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "format": "email"
                            },
                            "description": "Optional list of attendee email addresses"
                        }
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            },
            {
                "name": "list_calendars",
                "description": "List all calendars accessible to the user.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "forget_connected_account",
                "description": "Remove/disconnect the user's Google connected account from Auth0. This will delete the connected account so the user will need to re-authorize next time.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def _initialize_mock_calendar_data(self) -> Dict[str, Any]:
        """Initialize mock calendar data structure (dates are generated dynamically)"""
        return {
            "calendars": {
                "primary": {
                    "id": "primary",
                    "name": "Primary Calendar",
                    "description": "Default calendar",
                    "timezone": "America/Los_Angeles",
                    "access_role": "owner"
                },
                "work": {
                    "id": "work",
                    "name": "Work Calendar",
                    "description": "Work-related events",
                    "timezone": "America/Los_Angeles",
                    "access_role": "owner"
                }
            },
            "events": []  # Events will be generated dynamically in _get_mock_events()
        }
    
    def _get_mock_events(self) -> List[Dict[str, Any]]:
        """Generate mock calendar events with dates relative to current time"""
        # Use UTC timezone-aware datetime for consistency
        today = datetime.now(timezone.utc)
        
        return [
            {
                "id": "event-001",
                "calendar_id": "primary",
                "summary": "Team Standup",
                "description": "Daily team standup meeting",
                "start": {
                    "dateTime": (today - timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": (today - timedelta(days=5)).replace(hour=10, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "location": "Conference Room A",
                "attendees": [
                    {"email": "jane.doe@streamward.com", "responseStatus": "accepted"},
                    {"email": "john.smith@streamward.com", "responseStatus": "accepted"}
                ],
                "status": "confirmed",
                "created": (today - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": (today - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            {
                "id": "event-002",
                "calendar_id": "primary",
                "summary": "Client Meeting - TechCorp",
                "description": "Quarterly review meeting with TechCorp Solutions",
                "start": {
                    "dateTime": (today - timedelta(days=12)).replace(hour=14, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": (today - timedelta(days=12)).replace(hour=15, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "location": "Virtual - Zoom",
                "attendees": [
                    {"email": "jane.doe@streamward.com", "responseStatus": "accepted"},
                    {"email": "contact@techcorp.com", "responseStatus": "accepted"}
                ],
                "status": "confirmed",
                "created": (today - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": (today - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            {
                "id": "event-003",
                "calendar_id": "work",
                "summary": "Engineering All-Hands",
                "description": "Monthly engineering department all-hands meeting",
                "start": {
                    "dateTime": (today - timedelta(days=20)).replace(hour=11, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": (today - timedelta(days=20)).replace(hour=12, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "location": "Main Auditorium",
                "attendees": [
                    {"email": "jane.doe@streamward.com", "responseStatus": "accepted"},
                    {"email": "john.smith@streamward.com", "responseStatus": "accepted"},
                    {"email": "engineering@streamward.com", "responseStatus": "accepted"}
                ],
                "status": "confirmed",
                "created": (today - timedelta(days=25)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": (today - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            {
                "id": "event-004",
                "calendar_id": "primary",
                "summary": "One-on-One with Manager",
                "description": "Weekly one-on-one with direct manager",
                "start": {
                    "dateTime": (today - timedelta(days=3)).replace(hour=15, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": (today - timedelta(days=3)).replace(hour=15, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "location": "Office - Room 205",
                "attendees": [
                    {"email": "jane.doe@streamward.com", "responseStatus": "accepted"}
                ],
                "status": "confirmed",
                "created": (today - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": (today - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            {
                "id": "event-005",
                "calendar_id": "primary",
                "summary": "Project Planning Session",
                "description": "Q4 project planning and roadmap discussion",
                "start": {
                    "dateTime": (today - timedelta(days=25)).replace(hour=13, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": (today - timedelta(days=25)).replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "timeZone": "America/Los_Angeles"
                },
                "location": "Conference Room B",
                "attendees": [
                    {"email": "jane.doe@streamward.com", "responseStatus": "accepted"},
                    {"email": "john.smith@streamward.com", "responseStatus": "accepted"},
                    {"email": "project.manager@streamward.com", "responseStatus": "accepted"}
                ],
                "status": "confirmed",
                "created": (today - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": (today - timedelta(days=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        ]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available resource tools"""
        return self.tools
    
    async def _exchange_for_id_jag_token(self, original_access_token: str) -> Optional[Dict[str, Any]]:
        """
        Exchange original Okta access token for ID-JAG token.
        
        Following MCP flow pattern:
        - Original access token is from OKTA_MAIN_SERVER_ID (custom auth server)
        - Exchange for ID-JAG token targeting OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID (MCP auth server)
        - This matches MCP Step 1 exactly
        
        Args:
            original_access_token: Original Okta access token from NextAuth (OKTA_MAIN_SERVER_ID)
            
        Returns:
            Dict with access_token (ID-JAG token), expires_in, token_type, or None if failed
        """
        try:
            if not self.cross_app_access_manager.sdk_main:
                logger.error("[GOOGLE_WORKSPACE] SDK not configured for ID-JAG exchange")
                return None
            
            # Get MCP authorization server ID (like MCP Step 1 does)
            # Original token is from OKTA_MAIN_SERVER_ID, exchange for ID-JAG targeting MCP server
            mcp_auth_server_id = os.getenv("OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID", "").strip()
            if not mcp_auth_server_id:
                logger.error("[GOOGLE_WORKSPACE] OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID not configured")
                return None
            
            okta_domain = os.getenv("OKTA_DOMAIN", "").strip()
            id_jag_audience = f"{okta_domain}/oauth2/{mcp_auth_server_id}"
            
            logger.debug(f"[GOOGLE_WORKSPACE] Exchanging original token (from {os.getenv('OKTA_MAIN_SERVER_ID')}) for ID-JAG token (audience: {id_jag_audience})")
            
            # Exchange access token for ID-JAG token (matching MCP Step 1 exactly)
            id_jag_result = self.cross_app_access_manager.sdk_main.cross_app_access.exchange_token(
                token=original_access_token,
                token_type="access_token",
                audience=id_jag_audience,
                scope="mcp:read"  # Same scope as MCP
            )
            
            logger.info(f"[GOOGLE_WORKSPACE] ID-JAG token obtained: expires_in={id_jag_result.expires_in}s")
            
            return {
                "access_token": id_jag_result.access_token,
                "expires_in": id_jag_result.expires_in,
                "token_type": id_jag_result.token_type,
                "scope": getattr(id_jag_result, 'scope', None)
            }
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error exchanging for ID-JAG token: {str(e)}", exc_info=True)
            return None
    
    async def _exchange_id_jag_for_mcp_token(self, id_jag_token: str) -> Optional[Dict[str, Any]]:
        """
        Exchange ID-JAG token for MCP authorization server token.
        
        This matches MCP Step 3 exactly - exchange ID-JAG token for MCP server token.
        The MCP server token will be used for Auth0 Connected Accounts.
        
        Args:
            id_jag_token: ID-JAG token from previous exchange
            
        Returns:
            Dict with access_token (MCP server token), expires_in, token_type, or None if failed
        """
        try:
            # Use the cross_app_access_manager's MCP exchange method (same as MCP flow)
            if not self.cross_app_access_manager.sdk_mcp:
                logger.error("[GOOGLE_WORKSPACE] MCP SDK not configured")
                return None
            
            # Use MCP config values directly (matching MCP Step 3)
            mcp_auth_server_id = self.cross_app_access_manager.mcp_config.authorization_server_id
            
            logger.debug(f"[GOOGLE_WORKSPACE] Exchanging ID-JAG token for MCP auth server token (server: {mcp_auth_server_id})")
            
            # Create request for MCP authorization server token (matching MCP Step 3 exactly)
            from okta_ai_sdk import AuthServerTokenRequest
            auth_server_request = AuthServerTokenRequest(
                id_jag_token=id_jag_token,
                authorization_server_id=mcp_auth_server_id,
                principal_id=self.cross_app_access_manager.mcp_config.principal_id,
                private_jwk=self.cross_app_access_manager.mcp_config.private_jwk
            )
            
            # Exchange ID-JAG for MCP authorization server token using sdk_mcp (matching MCP Step 3)
            mcp_token_result = self.cross_app_access_manager.sdk_mcp.cross_app_access.exchange_id_jag_for_auth_server_token(
                auth_server_request
            )
            
            logger.info(f"[GOOGLE_WORKSPACE] MCP auth server token obtained: expires_in={mcp_token_result.expires_in}s")
            
            return {
                "access_token": mcp_token_result.access_token,
                "expires_in": mcp_token_result.expires_in,
                "token_type": mcp_token_result.token_type,
                "scope": getattr(mcp_token_result, 'scope', None)
            }
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error exchanging ID-JAG for MCP token: {str(e)}", exc_info=True)
            return None
    
    async def _get_google_token_from_vault(self, okta_access_token: str, user_sub: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Google token from Auth0 vault using Connected Accounts SDK.
        
        Args:
            okta_access_token: Okta authorization server access token (from ID-JAG exchange)
            state: Optional state parameter for OAuth flow
            
        Returns:
            Dict with either:
            - If token found: {"token": "...", "token_type": "...", "expires_in": ..., "scope": "..."}
            - If linking required: {"requires_linking": True, "authorization_url": "...", "auth_session": "..."}
        """
        if not self.auth0_config:
            return {
                "error": "auth0_not_configured",
                "message": "Auth0 Connected Accounts configuration not available"
            }
        
        try:
            # Initialize SDK for Connected Accounts
            # We need a dummy config for SDK initialization (won't be used for Connected Accounts)
            okta_domain = os.getenv("OKTA_DOMAIN", "").strip()
            if not okta_domain:
                return {"error": "okta_domain_missing", "message": "OKTA_DOMAIN not configured"}
            
            dummy_config = OktaAIConfig(
                oktaDomain=okta_domain,
                clientId="dummy",  # Not used for Connected Accounts
                clientSecret="dummy",
                authorizationServerId="default"
            )
            sdk = OktaAISDK(dummy_config)
            
            # Generate state if not provided
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Create request to get external provider token
            request = GetExternalProviderTokenRequest(
                okta_access_token=okta_access_token,
                auth0_config=self.auth0_config,
                connection=self.connection,
                redirect_uri=self.redirect_uri,
                state=state
            )
            
            # Get external provider token (tries vault first, initiates linking if needed)
            response = sdk.connected_accounts.get_external_provider_token_from_vault(request)
            
            if response.requires_linking:
                logger.info("[GOOGLE_WORKSPACE] Token not found in vault - Account linking required")
                
                # Store auth_session server-side, keyed by user's sub (for multi-user support)
                if user_sub:
                    logger.info(f"[GOOGLE_WORKSPACE] Storing auth_session for user_sub: {user_sub}")
                    logger.debug(f"[GOOGLE_WORKSPACE] Auth session value: {response.auth_session[:50] + '...' if response.auth_session else None}")
                    self._auth_sessions[user_sub] = {
                        "auth_session": response.auth_session,
                        "state": state,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    logger.info(f"[GOOGLE_WORKSPACE] ✅ Stored auth_session for user: {user_sub}")
                    logger.debug(f"[GOOGLE_WORKSPACE] All stored auth_sessions keys: {list(self._auth_sessions.keys())}")
                else:
                    logger.warning("[GOOGLE_WORKSPACE] No user_sub provided - cannot store auth_session server-side")
                
                return {
                    "requires_linking": True,
                    "authorization_url": response.authorization_url,
                    "state": state,
                    # Don't return auth_session to frontend - backend will retrieve it by user_sub
                }
            else:
                logger.info("[GOOGLE_WORKSPACE] Token found in vault")
                return {
                    "token": response.token,
                    "token_type": response.token_type,
                    "expires_in": response.expires_in,
                    "scope": response.scope
                }
                
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error getting token from vault: {str(e)}", exc_info=True)
            return {
                "error": "vault_error",
                "message": f"Error getting token from vault: {str(e)}"
            }
    
    async def _get_auth_session_for_user(self, user_sub: str) -> Optional[str]:
        """
        Retrieve auth_session for a user (server-side storage for multi-user support).
        
        Args:
            user_sub: User's Okta subject identifier
            
        Returns:
            auth_session string if found, None otherwise
        """
        session_data = self._auth_sessions.get(user_sub)
        if session_data:
            return session_data.get("auth_session")
        return None
    
    async def _complete_linking_and_get_token(self, connect_code: str, okta_access_token: str, user_sub: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete account linking and get Google token from vault.
        
        Args:
            connect_code: Authorization code from callback URL
            okta_access_token: Okta authorization server access token
            user_sub: User's Okta subject identifier (to retrieve stored auth_session)
            
        Returns:
            Dict with token information
        """
        logger.info(f"[GOOGLE_WORKSPACE] Completing linking for user: {user_sub}")
        logger.debug(f"[GOOGLE_WORKSPACE] Connect code: {connect_code[:20] + '...' if connect_code else None}")
        
        if not self.auth0_config:
            logger.error("[GOOGLE_WORKSPACE] Auth0 config not available")
            return {
                "error": "auth0_not_configured",
                "message": "Auth0 Connected Accounts configuration not available"
            }
        
        # Retrieve auth_session from server-side storage (multi-user support)
        auth_session = None
        if user_sub:
            logger.debug(f"[GOOGLE_WORKSPACE] Retrieving auth_session for user: {user_sub}")
            logger.debug(f"[GOOGLE_WORKSPACE] Stored auth_sessions keys: {list(self._auth_sessions.keys())}")
            auth_session = await self._get_auth_session_for_user(user_sub)
            logger.debug(f"[GOOGLE_WORKSPACE] Retrieved auth_session: {auth_session[:50] + '...' if auth_session else None}")
            
            if not auth_session:
                logger.error(f"[GOOGLE_WORKSPACE] No auth_session found for user: {user_sub}")
                logger.error(f"[GOOGLE_WORKSPACE] Available users: {list(self._auth_sessions.keys())}")
                return {
                    "error": "no_auth_session",
                    "message": f"No pending auth_session found for user {user_sub}. Please initiate linking again."
                }
        else:
            logger.error("[GOOGLE_WORKSPACE] No user_sub provided")
            return {
                "error": "missing_user_sub",
                "message": "User identifier required to retrieve auth_session"
            }
        
        try:
            # Initialize SDK
            okta_domain = os.getenv("OKTA_DOMAIN", "").strip()
            dummy_config = OktaAIConfig(
                oktaDomain=okta_domain,
                clientId="dummy",
                clientSecret="dummy",
                authorizationServerId="default"
            )
            sdk = OktaAISDK(dummy_config)
            
            # Create request to complete linking
            request = CompleteLinkingAndGetTokenRequest(
                auth_session=auth_session,
                connect_code=connect_code,
                redirect_uri=self.redirect_uri,
                auth0_config=self.auth0_config,
                connection=self.connection,
                okta_access_token=okta_access_token
            )
            
            # Complete linking and get token
            response = sdk.connected_accounts.complete_linking_and_get_token_from_vault(request)
            
            # Clear stored auth_session after successful linking
            if user_sub and user_sub in self._auth_sessions:
                del self._auth_sessions[user_sub]
                logger.debug(f"[GOOGLE_WORKSPACE] Cleared auth_session for user: {user_sub}")
            
            logger.info("[GOOGLE_WORKSPACE] Account linking completed and token obtained")
            return {
                "token": response.token,
                "token_type": response.token_type,
                "expires_in": response.expires_in,
                "scope": response.scope,
                "connection_id": getattr(response, 'connection_id', None),
                "user_id": getattr(response, 'user_id', None)
            }
            
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error completing linking: {str(e)}", exc_info=True)
            return {
                "error": "linking_error",
                "message": f"Error completing account linking: {str(e)}"
            }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a resource tool by name with arguments.
        
        Flow:
        1. Get original Okta access token from user_info
        2. Exchange for ID-JAG token (targeting custom authorization server)
        3. Exchange ID-JAG token for authorization server token
        4. Try to get Google token from Auth0 vault using the authorization server token
        5. If token not found, return authorization URL for linking
        6. If token found, use it to call Google API
        """
        try:
            # Get original Okta access token (from NextAuth custom auth server)
            original_okta_token = user_info.get("access_token") or user_info.get("token")
            
            if not original_okta_token:
                return {
                    "error": "missing_okta_token",
                    "message": "Okta access token required. Please authenticate first."
                }
            
            # Extract user's sub (subject) for multi-user support
            user_sub = user_info.get("sub") or user_info.get("user_id")
            logger.info(f"[GOOGLE_WORKSPACE] call_tool({tool_name}) - user_sub from user_info: {user_sub}")
            logger.debug(f"[GOOGLE_WORKSPACE] call_tool - user_info keys: {list(user_info.keys())}")
            logger.debug(f"[GOOGLE_WORKSPACE] call_tool - user_info['sub']: {user_info.get('sub')}")
            logger.debug(f"[GOOGLE_WORKSPACE] call_tool - user_info['email']: {user_info.get('email')}")
            
            # Perform ID-JAG exchange matching MCP flow exactly
            # Step 1: Exchange original token (OKTA_MAIN_SERVER_ID) for ID-JAG token (targeting MCP server)
            id_jag_result = await self._exchange_for_id_jag_token(original_okta_token)
            if not id_jag_result:
                return {
                    "error": "id_jag_exchange_failed",
                    "message": "Failed to exchange token for ID-JAG token"
                }
            
            id_jag_token = id_jag_result.get("access_token")
            id_jag_expires_in = id_jag_result.get("expires_in")
            
            # Step 2: Exchange ID-JAG token for MCP authorization server token (OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID)
            # Use the MCP server token for Auth0 (matching MCP flow Step 3)
            mcp_token_result = await self._exchange_id_jag_for_mcp_token(id_jag_token)
            if not mcp_token_result:
                return {
                    "error": "mcp_token_exchange_failed",
                    "message": "Failed to exchange ID-JAG token for MCP authorization server token"
                }
            
            okta_access_token = mcp_token_result.get("access_token")  # MCP server token used for Auth0
            
            # Special handling for forget_connected_account - skip Google token retrieval
            if tool_name == "forget_connected_account":
                tool_result = await self._forget_connected_account(arguments, user_info)
                # Add flow info for forget_connected_account
                if tool_result and not tool_result.get("error"):
                    tool_result["flow_info"] = {
                        "flow_state": "account_removed",
                        "original_okta_token": original_okta_token,
                        "id_jag_token": id_jag_token,
                        "id_jag_expires_in": id_jag_expires_in,
                        "okta_access_token": okta_access_token,
                        "tools_called": [tool_name]
                    }
                return tool_result
            
            # Try to get Google token from vault using the authorization server token
            google_token_result = await self._get_google_token_from_vault(okta_access_token, user_sub=user_sub)
            
            # Check if linking is required
            if google_token_result.get("requires_linking"):
                logger.info(f"[GOOGLE_WORKSPACE] Account linking required for tool: {tool_name}")
                return {
                    "requires_linking": True,
                    "authorization_url": google_token_result.get("authorization_url"),
                    "state": google_token_result.get("state"),
                    "message": "Google account authorization required. Please authorize to continue.",
                    "flow_info": {
                        "flow_state": "linking_required",
                        "original_okta_token": original_okta_token,  # Original Okta token (before ID-JAG)
                        "id_jag_token": id_jag_token,  # ID-JAG token
                        "id_jag_expires_in": id_jag_expires_in,
                        "okta_access_token": okta_access_token,  # Okta Access Token (after ID-JAG, used for Auth0)
                        "authorization_url": google_token_result.get("authorization_url"),
                    }
                    # Note: auth_session is stored server-side, not returned to frontend
                }
            
            # Check for errors
            if google_token_result.get("error"):
                return {
                    "error": google_token_result.get("error"),
                    "message": google_token_result.get("message", "Failed to get Google token")
                }
            
            # Token found - extract it
            google_token = google_token_result.get("token")
            if not google_token:
                return {
                    "error": "no_token",
                    "message": "Google token not available"
                }
            
            # Store Google token in user_info for tool execution
            user_info["google_token"] = google_token
            user_info["google_token_type"] = google_token_result.get("token_type")
            user_info["google_token_expires_in"] = google_token_result.get("expires_in")
            
            logger.debug(f"[GOOGLE_WORKSPACE] Google token obtained, executing tool: {tool_name}")
            
            # Execute the requested tool
            tool_result = None
            if tool_name == "get_calendar_events":
                tool_result = await self._get_calendar_events(arguments, user_info)
            elif tool_name == "create_calendar_event":
                tool_result = await self._create_calendar_event(arguments, user_info)
            elif tool_name == "list_calendars":
                tool_result = await self._list_calendars(arguments, user_info)
            else:
                return {
                    "error": "unknown_tool",
                    "message": f"Unknown tool: {tool_name}",
                    "available_tools": [tool["name"] for tool in self.tools]
                }
            
            # Add flow info for frontend display
            if tool_result and not tool_result.get("error"):
                tool_result["flow_info"] = {
                    "flow_state": "token_found",
                    "original_okta_token": original_okta_token,  # Original Okta token from OKTA_MAIN_SERVER_ID
                    "id_jag_token": id_jag_token,  # ID-JAG token (targeting MCP server)
                    "id_jag_expires_in": id_jag_expires_in,
                    "okta_access_token": okta_access_token,  # MCP server token (from OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID, used for Auth0)
                    "google_token": google_token,  # Full Google token for copy functionality
                    "token_type": google_token_result.get("token_type"),
                    "expires_in": google_token_result.get("expires_in"),
                    "scope": google_token_result.get("scope"),
                    "tools_called": [tool_name]
                }
            
            return tool_result
                
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Tool execution error: {str(e)}", exc_info=True)
            return {
                "error": "execution_error",
                "message": f"Error executing tool {tool_name}: {str(e)}"
            }
    
    async def _get_calendar_events(self, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get calendar events within a date range.
        
        If Google token is available, calls Google Calendar API.
        Otherwise, returns mock data for demonstration.
        """
        try:
            google_token = user_info.get("google_token")
            
            if google_token:
                # TODO: Call actual Google Calendar API
                # For now, return mock data but indicate it's from Google
                logger.info("[GOOGLE_WORKSPACE] Google token available - would call Google Calendar API")
                # In production: Use google_token to call Google Calendar API
                # Example: https://www.googleapis.com/calendar/v3/calendars/primary/events
            # Helper function to parse datetime string safely
            def parse_datetime_str(dt_str: str) -> datetime:
                """Parse datetime string, handling both Z and timezone offset formats"""
                import re
                
                # First, aggressively clean up any double timezone offsets
                # Remove all instances of +00:00+00:00 patterns
                while "+00:00+00:00" in dt_str or re.search(r'\+00:00\+00:00', dt_str):
                    dt_str = dt_str.replace("+00:00+00:00", "+00:00")
                    dt_str = re.sub(r'(\+00:00){2,}', '+00:00', dt_str)
                
                # Check if string already has timezone offset (ends with +XX:XX or -XX:XX pattern)
                has_timezone = bool(re.search(r'[+-]\d{2}:\d{2}$', dt_str))
                
                if dt_str.endswith("Z"):
                    # Replace Z with +00:00
                    dt_str = dt_str[:-1] + "+00:00"
                elif has_timezone:
                    # Already has timezone offset, use as-is
                    pass
                else:
                    # No timezone, assume UTC
                    dt_str = dt_str + "+00:00"
                
                # Final cleanup before parsing
                dt_str = dt_str.replace("+00:00+00:00", "+00:00")
                
                try:
                    dt = datetime.fromisoformat(dt_str)
                except ValueError as e:
                    logger.error(f"[GOOGLE_WORKSPACE] Failed to parse datetime '{dt_str}': {e}")
                    # Fallback: try to clean up the string more aggressively
                    dt_str_clean = dt_str.replace("+00:00+00:00", "+00:00")
                    dt_str_clean = re.sub(r'(\+00:00){2,}', '+00:00', dt_str_clean)
                    # If still has double, remove all but one
                    if dt_str_clean.count("+00:00") > 1:
                        # Find the last occurrence and keep only that
                        last_pos = dt_str_clean.rfind("+00:00")
                        dt_str_clean = dt_str_clean[:last_pos].replace("+00:00", "") + dt_str_clean[last_pos:]
                    dt = datetime.fromisoformat(dt_str_clean)
                
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            
            # Parse date arguments
            # Use UTC timezone-aware datetime for consistency
            end_date = datetime.now(timezone.utc)
            if arguments.get("end_date"):
                end_date = parse_datetime_str(arguments["end_date"])
            
            start_date = end_date - timedelta(days=30)  # Default: 1 month ago
            if arguments.get("start_date"):
                start_date = parse_datetime_str(arguments["start_date"])
            
            calendar_id = arguments.get("calendar_id", "primary")
            max_results = arguments.get("max_results", 50)
            
            # Get mock events (generated dynamically with current dates)
            mock_events = self._get_mock_events()
            
            # Filter events by date range and calendar
            filtered_events = []
            for event in mock_events:
                if event["calendar_id"] != calendar_id and calendar_id != "all":
                    continue
                
                event_start = parse_datetime_str(event["start"]["dateTime"])
                
                if start_date <= event_start <= end_date:
                    filtered_events.append(event)
            
            # Sort by start time (most recent first)
            filtered_events.sort(key=lambda x: parse_datetime_str(x["start"]["dateTime"]), reverse=True)
            
            # Limit results
            filtered_events = filtered_events[:max_results]
            
            logger.info(f"[GOOGLE_WORKSPACE] Retrieved {len(filtered_events)} calendar events from {start_date.date()} to {end_date.date()}")
            
            return {
                "success": True,
                "events": filtered_events,
                "total": len(filtered_events),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "calendar_id": calendar_id
            }
            
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error getting calendar events: {str(e)}", exc_info=True)
            return {
                "error": "get_events_error",
                "message": f"Error retrieving calendar events: {str(e)}"
            }
    
    async def _create_calendar_event(self, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event (dummy implementation)"""
        try:
            event_id = f"event-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            new_event = {
                "id": event_id,
                "calendar_id": "primary",
                "summary": arguments.get("summary", "New Event"),
                "description": arguments.get("description", ""),
                "start": {
                    "dateTime": arguments["start_time"],
                    "timeZone": "America/Los_Angeles"
                },
                "end": {
                    "dateTime": arguments["end_time"],
                    "timeZone": "America/Los_Angeles"
                },
                "location": arguments.get("location", ""),
                "attendees": [{"email": email, "responseStatus": "needsAction"} for email in arguments.get("attendees", [])],
                "status": "confirmed",
                "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            # Add to mock data
            self.calendar_data["events"].append(new_event)
            
            logger.info(f"[GOOGLE_WORKSPACE] Created calendar event: {new_event['summary']}")
            
            return {
                "success": True,
                "event": new_event,
                "message": "Calendar event created successfully"
            }
            
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error creating calendar event: {str(e)}", exc_info=True)
            return {
                "error": "create_event_error",
                "message": f"Error creating calendar event: {str(e)}"
            }
    
    async def _list_calendars(self, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """List all accessible calendars"""
        try:
            calendars = list(self.calendar_data["calendars"].values())
            
            logger.info(f"[GOOGLE_WORKSPACE] Retrieved {len(calendars)} calendars")
            
            return {
                "success": True,
                "calendars": calendars,
                "total": len(calendars)
            }
            
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error listing calendars: {str(e)}", exc_info=True)
            return {
                "error": "list_calendars_error",
                "message": f"Error listing calendars: {str(e)}"
            }
    
    async def _forget_connected_account(self, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove/disconnect the user's Google connected account from Auth0.
        
        This performs Step 7 from the notebook:
        1. Perform ID-JAG exchange to get MCP server token
        2. Exchange for MyAccount token
        3. List connected accounts
        4. Delete the Google connected account
        """
        try:
            if not self.auth0_config:
                return {
                    "error": "auth0_not_configured",
                    "message": "Auth0 Connected Accounts configuration not available"
                }
            
            # Get original Okta access token (from NextAuth custom auth server)
            original_okta_token = user_info.get("access_token") or user_info.get("token")
            
            if not original_okta_token:
                return {
                    "error": "missing_okta_token",
                    "message": "Okta access token required. Please authenticate first."
                }
            
            # Extract user's sub (subject) for multi-user support
            user_sub = user_info.get("sub") or user_info.get("user_id")
            
            # Perform ID-JAG exchange matching MCP flow exactly
            # Step 1: Exchange original token (OKTA_MAIN_SERVER_ID) for ID-JAG token (targeting MCP server)
            id_jag_result = await self._exchange_for_id_jag_token(original_okta_token)
            if not id_jag_result:
                return {
                    "error": "id_jag_exchange_failed",
                    "message": "Failed to exchange token for ID-JAG token"
                }
            
            id_jag_token = id_jag_result.get("access_token")
            
            # Step 2: Exchange ID-JAG token for MCP authorization server token (OKTA_EMPLOYEE_MCP_AUTHORIZATION_SERVER_ID)
            mcp_token_result = await self._exchange_id_jag_for_mcp_token(id_jag_token)
            if not mcp_token_result:
                return {
                    "error": "mcp_token_exchange_failed",
                    "message": "Failed to exchange ID-JAG token for MCP authorization server token"
                }
            
            okta_access_token = mcp_token_result.get("access_token")  # MCP server token
            
            logger.info("[GOOGLE_WORKSPACE] Step 7: Getting MyAccount token to manage connected accounts...")
            
            # Step 3: Exchange MCP token for MyAccount token
            myaccount_token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                'audience': self.auth0_config.myaccount_audience,
                'client_id': self.auth0_config.myaccount_client_id,
                'client_secret': self.auth0_config.myaccount_client_secret,
                'subject_token_type': self.auth0_config.vault_token_type,
                'scope': 'create:me:connected_accounts read:me:connected_accounts delete:me:connected_accounts',
                'subject_token': okta_access_token,  # MCP server token
            }
            
            token_response = requests.post(
                self.auth0_config.token_endpoint,
                data=myaccount_token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if token_response.status_code != 200:
                logger.error(f"[GOOGLE_WORKSPACE] Failed to get MyAccount token: {token_response.status_code} - {token_response.text}")
                return {
                    "error": "myaccount_token_failed",
                    "message": f"Failed to get MyAccount token: {token_response.status_code}"
                }
            
            auth0_myaccount_token = token_response.json()["access_token"]
            logger.info("[GOOGLE_WORKSPACE] MyAccount token obtained")
            
            # Step 4: List connected accounts
            list_response = requests.get(
                f"{self.auth0_config.myaccount_audience}v1/connected-accounts/accounts",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {auth0_myaccount_token}'
                }
            )
            
            if list_response.status_code != 200:
                logger.error(f"[GOOGLE_WORKSPACE] Failed to list accounts: {list_response.status_code} - {list_response.text}")
                return {
                    "error": "list_accounts_failed",
                    "message": f"Failed to list connected accounts: {list_response.status_code}"
                }
            
            accounts = list_response.json()
            logger.info(f"[GOOGLE_WORKSPACE] Found {len(accounts)} connected account(s)")
            
            # Step 5: Find and delete Google connected account
            google_account = None
            connection_name = self.connection.lower()
            
            # Accounts can be a list or a dict with 'accounts' key
            accounts_list = accounts if isinstance(accounts, list) else accounts.get('accounts', [])
            
            for account in accounts_list:
                # Check if this is the Google account (by connection name or provider)
                account_connection = account.get('connection', '').lower()
                account_provider = account.get('provider', '').lower()
                
                if 'google' in account_connection or 'google' in account_provider or connection_name in account_connection:
                    google_account = account
                    break
            
            if not google_account:
                logger.info("[GOOGLE_WORKSPACE] No Google connected account found")
                return {
                    "success": True,
                    "message": "No Google connected account found. Nothing to remove.",
                    "accounts_found": len(accounts_list)
                }
            
            connection_id = google_account.get('connection_id') or google_account.get('id')
            if not connection_id:
                logger.error(f"[GOOGLE_WORKSPACE] Could not find connection_id in account: {google_account}")
                return {
                    "error": "missing_connection_id",
                    "message": "Could not find connection ID for Google account"
                }
            
            # Step 6: Delete the connected account
            logger.info(f"[GOOGLE_WORKSPACE] Deleting Google connected account: {connection_id}")
            delete_response = requests.delete(
                f"{self.auth0_config.myaccount_audience}v1/connected-accounts/accounts/{connection_id}",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {auth0_myaccount_token}'
                }
            )
            
            if delete_response.status_code in [200, 204]:
                logger.info(f"[GOOGLE_WORKSPACE] Successfully deleted Google connected account: {connection_id}")
                return {
                    "success": True,
                    "message": "Google connected account has been removed successfully. You will need to re-authorize next time you use Google Workspace features.",
                    "connection_id": connection_id,
                    "deleted_account": {
                        "provider": google_account.get('provider'),
                        "connection": google_account.get('connection'),
                        "user_id": google_account.get('user_id')
                    }
                }
            else:
                logger.error(f"[GOOGLE_WORKSPACE] Failed to delete account: {delete_response.status_code} - {delete_response.text}")
                return {
                    "error": "delete_account_failed",
                    "message": f"Failed to delete connected account: {delete_response.status_code}",
                    "response": delete_response.text
                }
            
        except Exception as e:
            logger.error(f"[GOOGLE_WORKSPACE] Error forgetting connected account: {str(e)}", exc_info=True)
            return {
                "error": "forget_account_error",
                "message": f"Error removing connected account: {str(e)}"
            }


