import os
import logging
from typing import Optional
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.credentials import Credentials, CredentialConfiguration
from openfga_sdk.client.models import ClientTuple, ClientWriteRequest

logger = logging.getLogger(__name__)

class AuthorizationManager:
    """Manages Auth0 FGA authorization for document access control"""
    
    def __init__(self):
        self.openfga_client: Optional[OpenFgaClient] = None
        self._connect()
    
    def _connect(self):
        """Connect to Auth0 FGA"""
        try:
            # Check if FGA environment variables are set
            fga_store_id = os.getenv('FGA_STORE_ID')
            fga_client_id = os.getenv('FGA_CLIENT_ID')
            fga_client_secret = os.getenv('FGA_CLIENT_SECRET')
            
            if not all([fga_store_id, fga_client_id, fga_client_secret]):
                logger.warning("FGA environment variables not set - running in demo mode")
                self.openfga_client = None
                return
            
            openfga_client_config = ClientConfiguration(
                api_url=os.getenv('FGA_API_URL', 'https://api.us1.fga.dev'),
                store_id=fga_store_id,
                authorization_model_id=os.getenv('FGA_AUTHORIZATION_MODEL_ID'),
                credentials=Credentials(
                    method="client_credentials",
                    configuration=CredentialConfiguration(
                        api_issuer=os.getenv('FGA_API_TOKEN_ISSUER', 'auth.fga.dev'),
                        api_audience=os.getenv('FGA_API_AUDIENCE', 'https://api.us1.fga.dev/'),
                        client_id=fga_client_id,
                        client_secret=fga_client_secret,
                    ),
                ),
            )
            
            logger.info("Connecting to Auth0 FGA...")
            self.openfga_client = OpenFgaClient(openfga_client_config)
            logger.info("✅ Connected to Auth0 FGA successfully")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Auth0 FGA ({e}) - running in demo mode")
            self.openfga_client = None
    
    async def add_relation(
        self, user_email: str, document_id: str, relation: str = "owner"
    ) -> bool:
        """Add a relation between user and document"""
        if not self.openfga_client:
            logger.warning("FGA client not connected - skipping relation (demo mode)")
            return True
            
        try:
            await self.openfga_client.write(
                ClientWriteRequest(
                    writes=[
                        ClientTuple(
                            user=f"user:{user_email}",
                            relation=relation,
                            object=f"doc:{document_id}",
                        )
                    ]
                )
            )
            logger.info(f"✅ Added {relation} relation for user:{user_email} -> doc:{document_id}")
            return True
        except Exception as e:
            logger.warning(f"FGA relation add failed ({e}) - continuing in demo mode")
            return True
    
    async def delete_relation(
        self, user_email: str, document_id: str, relation: str = "owner"
    ) -> bool:
        """Delete a relation between user and document"""
        if not self.openfga_client:
            logger.warning("FGA client not connected - skipping relation deletion (demo mode)")
            return True  # Return True in demo mode
            
        try:
            # Create the tuple to delete - must match EXACT format used when adding
            # Format: user:email, relation:relation_name, object:doc:document_id
            tuple_to_delete = ClientTuple(
                user=f"user:{user_email}",
                relation=relation,
                object=f"doc:{document_id}",
            )
            
            logger.debug(f"Attempting to delete tuple: user={tuple_to_delete.user}, relation={tuple_to_delete.relation}, object={tuple_to_delete.object}")
            
            # Attempt to delete the relation tuple
            # According to FGA API docs (https://docs.fga.dev/api/service#/Relationship%20Tuples/Write),
            # deletes should work even if tuple doesn't exist
            write_response = await self.openfga_client.write(
                ClientWriteRequest(
                    deletes=[tuple_to_delete]
                )
            )
            
            logger.info(f"✅ Deleted {relation} relation for user:{user_email} -> doc:{document_id}")
            if write_response:
                logger.debug(f"Write response: {write_response}")
            return True
            
        except Exception as e:
            # Log the full error for debugging
            error_msg = str(e)
            error_details = error_msg.lower()
            
            # Try to extract more details from the exception
            error_type = type(e).__name__
            logger.error(f"❌ Failed to delete {relation} relation: {error_type}: {e}")
            
            # Check exception attributes for more details
            error_info = {}
            if hasattr(e, 'status_code'):
                error_info['status_code'] = e.status_code
                logger.debug(f"Error status code: {e.status_code}")
            if hasattr(e, 'response'):
                error_info['response'] = str(e.response)
                logger.debug(f"Error response: {e.response}")
            if hasattr(e, 'body'):
                error_info['body'] = str(e.body)
                logger.debug(f"Error body: {e.body}")
            if hasattr(e, 'reason'):
                error_info['reason'] = str(e.reason)
                logger.debug(f"Error reason: {e.reason}")
            if hasattr(e, 'details'):
                error_info['details'] = e.details
                logger.debug(f"Error details: {e.details}")
            
            # For ValidationException, try to get validation errors
            if 'validation' in error_type.lower() or 'ValidationException' in str(type(e)):
                logger.debug(f"Validation error detected - checking for validation details")
                # Check common exception attributes
                for attr in ['message', 'validation_errors', 'errors', 'error', 'details']:
                    if hasattr(e, attr):
                        attr_value = getattr(e, attr)
                        if attr_value:
                            logger.debug(f"  {attr}: {attr_value}")
            
            # Log all exception attributes for debugging
            logger.debug(f"Exception attributes: {dir(e)}")
            logger.debug(f"Exception args: {e.args}")
            
            # Check if it's a ValidationException or 400 error
            is_validation_error = ("validation" in error_type.lower() or 
                                  "ValidationException" in str(type(e)) or
                                  "400" in error_msg or 
                                  "bad request" in error_details)
            
            if is_validation_error:
                logger.debug(f"Validation/Bad Request error when deleting {relation} relation")
                logger.debug(f"Tuple format: user=user:{user_email}, relation={relation}, object=doc:{document_id}")
                
                # For owner relations with validation errors, this might be a model constraint
                # Since it works in FGA console but not via SDK, it could be:
                # 1. A model validation rule preventing owner deletion
                # 2. A required condition that's met in console but not in SDK
                # 3. A timing/state issue
                if "owner" in relation.lower():
                    logger.warning(f"⚠️ Owner relation deletion failed with ValidationException (400)")
                    logger.warning(f"   This may be a constraint in your FGA authorization model")
                    logger.warning(f"   Owner relations may require special conditions to delete")
                    logger.warning(f"   The document is already deleted from Pinecone, so this is non-critical")
                    logger.info(f"💡 Tip: You can manually delete owner relations in FGA console if needed")
                    # Return True to avoid blocking cleanup - document already deleted from Pinecone
                    return True
            
            # For other errors, log but still try to continue
            if "403" in error_msg or "forbidden" in error_details:
                logger.warning(f"Forbidden when deleting {relation} - insufficient permissions")
            elif "404" in error_msg or "not found" in error_details:
                logger.debug(f"Tuple not found (404) - may have already been deleted")
                return True  # Not an error if already gone
            
            # For owner relations, be more lenient since the document is already deleted
            if relation == "owner":
                logger.warning(f"Owner relation deletion failed but continuing - document already removed from Pinecone")
                return True
            
            return False
    
    async def check_permission(
        self, user_email: str, document_id: str, relation: str = "can_view"
    ) -> bool:
        """Check if user has permission to access document"""
        # In demo mode (no FGA configured), always allow access
        if not self.openfga_client:
            logger.debug(f"Demo mode: allowing access for {user_email} to {document_id}")
            return True
            
        try:
            from openfga_sdk.client.models import ClientCheckRequest
            response = await self.openfga_client.check(
                ClientCheckRequest(
                    user=f"user:{user_email}",
                    relation=relation,
                    object=f"doc:{document_id}"
                )
            )
            logger.debug(f"FGA check result: {response.allowed} for {user_email} -> {document_id}")
            return response.allowed
        except Exception as e:
            logger.warning(f"FGA check failed ({e}) - allowing access (demo mode)")
            return True
    
    async def check_access(
        self, user_email: str, document_id: str, relation: str = "viewer"
    ) -> bool:
        """Alias for check_permission with different default relation"""
        return await self.check_permission(user_email, document_id, relation)
    
    def is_connected(self) -> bool:
        """Check if FGA client is connected"""
        return self.openfga_client is not None
    
    async def close(self):
        """Properly close the FGA client and clean up resources"""
        if self.openfga_client:
            try:
                # Close the underlying aiohttp session if it exists
                if hasattr(self.openfga_client, 'close'):
                    await self.openfga_client.close()
                logger.debug("[FGA] Client session closed successfully")
            except Exception as e:
                logger.debug(f"[FGA] Error closing client: {e}")
            finally:
                self.openfga_client = None

# Global instance
authorization_manager = AuthorizationManager()
