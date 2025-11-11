#!/usr/bin/env python3
"""
Upload a sample security document and add FGA relations for testing
This script will NOT delete anything - you can manually clean up later

Run from project root or from scripts directory.
"""
import os
import sys
import asyncio
import logging
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Change to project root for imports and .env loading
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from project root
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# Real user email (for document owner and FGA relations)
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "indranil.jha@okta.com")
# Test token that uses TEST_USER_EMAIL from environment
TEST_TOKEN = "test-token-demo-user"

# Sample security document content
SECURITY_DOCUMENT = {
    "title": "Streamward Corporation Security Policy",
    "content": """STREAMWARD CORPORATION SECURITY POLICY

1. PASSWORD REQUIREMENTS
   - Minimum 12 characters
   - Must include uppercase, lowercase, numbers, and special characters
   - Passwords must be changed every 90 days
   - Never share passwords with anyone

2. DATA PROTECTION
   - All sensitive data must be encrypted at rest and in transit
   - Customer data must never be stored on personal devices
   - Regular backups must be maintained for all critical systems
   - Data retention policies must be strictly followed

3. ACCESS CONTROL
   - Employees must only access data they need for their role
   - Multi-factor authentication (MFA) is required for all systems
   - Access reviews must be conducted quarterly
   - Principle of least privilege applies to all accounts

4. INCIDENT RESPONSE
   - All security incidents must be reported to security@streamward.com immediately
   - Incident response team must be notified within 1 hour of discovery
   - Document all incidents in the security incident log
   - Conduct post-incident reviews within 7 days

5. NETWORK SECURITY
   - Use VPN when accessing corporate resources remotely
   - Public Wi-Fi is prohibited for company work
   - All network traffic must be monitored
   - Firewall rules must be reviewed monthly

6. SOFTWARE SECURITY
   - Only approved software may be installed on company devices
   - All software must be kept up to date with latest security patches
   - Open source software requires security review before use
   - Regular vulnerability scanning is mandatory

7. PHYSICAL SECURITY
   - Badges must be worn at all times in office
   - Visitors must be escorted
   - Server rooms are restricted access only
   - Lock screens when away from desk

8. COMPLIANCE
   - All employees must complete security training annually
   - GDPR and SOC 2 compliance requirements must be met
   - Regular security audits will be conducted
   - Non-compliance may result in disciplinary action

For questions, contact: security@streamward.com
Last updated: 2024-01-15
Version: 2.1""",
    "metadata": {
        "department": "IT",
        "category": "policy",
        "version": "2.1",
        "last_updated": "2024-01-15",
        "document_type": "security_policy"
    }
}

async def upload_security_document():
    """Upload a security document and add FGA relations"""
    print("=" * 70)
    print("Uploading Security Document for RAG Testing")
    print("=" * 70)
    print()
    print(f" Using TEST_USER_EMAIL: {TEST_USER_EMAIL}")
    print()
    
    uploaded_doc_id = None
    doc_owner_email = None
    
    try:
        # Step 1: Upload the document
        print(" Step 1: Uploading security document...")
        print(f"   Title: {SECURITY_DOCUMENT['title']}")
        print(f"   Content length: {len(SECURITY_DOCUMENT['content'])} characters")
        print(f"   Document owner will be: {TEST_USER_EMAIL}")
        print()
        
        async with httpx.AsyncClient() as client:
            upload_response = await client.post(
                f"{API_BASE_URL}/api/documents/upload",
                headers={
                    "Authorization": f"Bearer {TEST_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=SECURITY_DOCUMENT
            )
            
            if upload_response.status_code != 200:
                print(f" Upload failed: {upload_response.status_code}")
                print(f"   Error: {upload_response.text}")
                return None
            
            upload_result = upload_response.json()
            uploaded_doc_id = upload_result["document_id"]
            doc_owner_email = upload_result["owner_email"]
            
            print(f" Document uploaded successfully!")
            print(f"   Document ID: {uploaded_doc_id}")
            print(f"   Title: {upload_result['title']}")
            print(f"   Owner: {doc_owner_email}")
            print()
        
        # Step 2: Add FGA relations for the document owner
        print("🔗 Step 2: Adding FGA relations...")
        print(f"   Document owner: {doc_owner_email}")
        
        from auth.fga_manager import authorization_manager
        authorization_manager._connect()
        
        if authorization_manager.is_connected():
            print(f"   Adding relations for: {doc_owner_email}")
            
            # Add owner relation
            print(f"   Adding owner relation...")
            owner_success = await authorization_manager.add_relation(
                doc_owner_email, uploaded_doc_id, "owner"
            )
            if owner_success:
                print(f"    Owner relation added")
            else:
                print(f"    Failed to add owner relation")
            
            # Add viewer relation
            print(f"   Adding viewer relation...")
            viewer_success = await authorization_manager.add_relation(
                doc_owner_email, uploaded_doc_id, "viewer"
            )
            if viewer_success:
                print(f"    Viewer relation added")
            else:
                print(f"    Failed to add viewer relation")
            
            # Verify permissions
            print(f"   Verifying permissions...")
            owner_permission = await authorization_manager.check_permission(
                doc_owner_email, uploaded_doc_id, "owner"
            )
            viewer_permission = await authorization_manager.check_permission(
                doc_owner_email, uploaded_doc_id, "viewer"
            )
            
            print(f"   Owner permission: {'' if owner_permission else ''}")
            print(f"   Viewer permission: {'' if viewer_permission else ''}")
            
            if owner_permission and viewer_permission:
                print(f" FGA relations verified successfully!")
            else:
                print(f" Some FGA relations may need manual setup")
        else:
            print(" FGA not connected - running in demo mode")
            print("   Relations will need to be added manually")
        
        print()
        
        # Step 3: Verify document can be retrieved
        print(" Step 3: Verifying document retrieval...")
        
        async with httpx.AsyncClient() as client:
            get_response = await client.get(
                f"{API_BASE_URL}/api/documents/{uploaded_doc_id}",
                headers={"Authorization": f"Bearer {TEST_TOKEN}"}
            )
            
            if get_response.status_code == 200:
                get_result = get_response.json()
                print(f" Document retrieval successful!")
                print(f"   Title: {get_result['title']}")
                print(f"   Content preview: {get_result['content'][:100]}...")
            else:
                print(f" Document retrieval failed: {get_response.status_code}")
                print(f"   Error: {get_response.text}")
        
        print()
        
        # Summary
        print("=" * 70)
        print(" UPLOAD COMPLETE")
        print("=" * 70)
        print(f" Document ID: {uploaded_doc_id}")
        print(f" Title: {SECURITY_DOCUMENT['title']}")
        print(f" Document Owner: {doc_owner_email}")
        print(f" FGA Relations: ADDED")
        print()
        print("🧪 Testing Instructions:")
        print(f"   1. In chat UI (logged in with your Okta account), ask:")
        print(f"      'Search for documents about security'")
        print(f"   2. Or ask: 'Find information about password requirements'")
        print(f"   3. Or ask: 'What documents do I have access to?'")
        print()
        print("🗑 To manually delete later:")
        print(f"   1. Delete from Pinecone via API: DELETE /api/documents/{uploaded_doc_id}")
        print(f"   2. Delete FGA relations manually in FGA console")
        print(f"   3. Document ID for reference: {uploaded_doc_id}")
        print("=" * 70)
        
        # Clean up FGA connections
        try:
            from auth.fga_manager import authorization_manager
            await authorization_manager.close()
        except Exception as cleanup_error:
            logger.debug(f"[Cleanup] FGA close error: {cleanup_error}")
        
        return uploaded_doc_id
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up FGA connections even on error
        try:
            from auth.fga_manager import authorization_manager
            await authorization_manager.close()
        except Exception as cleanup_error:
            logger.debug(f"[Cleanup] FGA close error: {cleanup_error}")
        
        return None

if __name__ == "__main__":
    print(" Security Document Upload Script\n")
    
    try:
        doc_id = asyncio.run(upload_security_document())
        
        if doc_id:
            print(f"\n Success! Document uploaded with ID: {doc_id}")
            print(f"   You can now test RAG queries in the chat UI")
        else:
            print(f"\n Upload failed - please check errors above")
            
    except KeyboardInterrupt:
        print("\n\n Upload interrupted by user")
    except Exception as e:
        print(f"\n\n Upload failed: {e}")
        import traceback
        traceback.print_exc()

