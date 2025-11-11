#!/usr/bin/env python3
"""
Clear all documents from Pinecone
This will delete all documents from the Pinecone index

Run from project root or from scripts directory.
"""
import os
import sys
import asyncio
import logging
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

async def clear_all_documents():
    """Delete all documents from Pinecone"""
    print("=" * 70)
    print("Clearing All Documents from Pinecone")
    print("=" * 70)
    print()
    
    try:
        from rag.pinecone_store import pinecone_store
        from auth.fga_manager import authorization_manager
        
        await pinecone_store.initialize()
        authorization_manager._connect()
        
        if not pinecone_store.index:
            print(" Pinecone not initialized")
            return
        
        # Get all documents
        print(" Step 1: Getting all documents from Pinecone...")
        all_docs = await pinecone_store.list_all_documents(k=1000)
        print(f"   Found {len(all_docs)} documents")
        
        if len(all_docs) == 0:
            print(" No documents to delete")
            return
        
        # Confirm deletion
        print()
        print(f"  WARNING: This will delete {len(all_docs)} documents from Pinecone!")
        response = input("Type 'DELETE ALL' to confirm: ")
        
        if response != "DELETE ALL":
            print(" Deletion cancelled")
            return
        
        print()
        print("🗑  Step 2: Deleting documents...")
        
        deleted_count = 0
        failed_count = 0
        
        for doc in all_docs:
            doc_id = doc.metadata.get("document_id")
            if not doc_id:
                continue
            
            title = doc.metadata.get("title", "Untitled")
            
            try:
                # Delete from Pinecone
                success = await pinecone_store.delete_document(doc_id)
                
                if success:
                    deleted_count += 1
                    if deleted_count % 10 == 0:
                        print(f"   Deleted {deleted_count}/{len(all_docs)} documents...")
                else:
                    failed_count += 1
                    print(f"    Failed to delete: {doc_id}")
                
                # Optionally delete FGA relations (if FGA is connected)
                if authorization_manager.is_connected():
                    try:
                        await authorization_manager.delete_relation(
                            "user:demo@streamward.com", doc_id, "owner"
                        )
                    except:
                        pass
                    try:
                        await authorization_manager.delete_relation(
                            "user:demo@streamward.com", doc_id, "viewer"
                        )
                    except:
                        pass
                    # Try with indranil.jha@okta.com as well
                    try:
                        await authorization_manager.delete_relation(
                            "indranil.jha@okta.com", doc_id, "owner"
                        )
                    except:
                        pass
                    try:
                        await authorization_manager.delete_relation(
                            "indranil.jha@okta.com", doc_id, "viewer"
                        )
                    except:
                        pass
            except Exception as e:
                failed_count += 1
                print(f"    Error deleting {doc_id}: {e}")
        
        print()
        print("=" * 70)
        print(" CLEANUP COMPLETE")
        print("=" * 70)
        print(f" Results:")
        print(f"   Documents deleted: {deleted_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total processed: {len(all_docs)}")
        print()
        print(" Note: FGA relations may still exist - delete them manually if needed")
        print("=" * 70)
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(" Pinecone Cleanup Script\n")
    
    try:
        asyncio.run(clear_all_documents())
    except KeyboardInterrupt:
        print("\n\n Cleanup interrupted by user")
    except Exception as e:
        print(f"\n\n Cleanup failed: {e}")
        import traceback
        traceback.print_exc()

