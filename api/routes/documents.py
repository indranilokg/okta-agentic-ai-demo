import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from auth.fga_manager import authorization_manager
from auth.okta_validator import get_current_user
from rag.context_docs_tool import document_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Pydantic models
class DocumentUpload(BaseModel):
    content: str
    title: str
    metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    document_id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    owner_email: str

class DocumentShare(BaseModel):
    user_email: str
    relation: str = "can_view"

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    document: DocumentUpload,
    current_user: dict = Depends(get_current_user)
):
    """Upload a new document to the knowledge base"""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Add document to retriever
        metadata = {
            "title": document.title,
            "owner": user_email,
            "created_at": datetime.now().isoformat(),
            **(document.metadata or {})
        }
        
        success = await document_retriever.add_document(
            document_id, 
            document.content, 
            metadata
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add document")
        
        # Add FGA relations (user owns the document and can also view it)
        owner_success = await authorization_manager.add_relation(
            user_email, document_id, "owner"
        )
        
        if not owner_success:
            logger.warning(f"Failed to add owner FGA relation for document {document_id}")
        
        # Also add viewer relation so the owner can retrieve the document
        viewer_success = await authorization_manager.add_relation(
            user_email, document_id, "viewer"
        )
        
        if not viewer_success:
            logger.warning(f"Failed to add viewer FGA relation for document {document_id}")
        
        return DocumentResponse(
            document_id=document_id,
            title=document.title,
            content=document.content,
            metadata=metadata,
            created_at=datetime.now(),
            owner_email=user_email
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail="Document upload failed")

@router.get("/", response_model=DocumentListResponse)
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all documents the user has access to"""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found")
        
        # Get all documents and check permissions
        accessible_documents = []
        
        # For Pinecone, we need to list documents and check permissions
        # This is a simplified approach - in production you'd want to maintain a document index
        try:
            # Initialize Pinecone store if needed
            if not document_retriever.pinecone_store.index:
                await document_retriever.pinecone_store.initialize()
            
            # List all documents using the dedicated list method
            all_docs = await document_retriever.pinecone_store.list_all_documents(k=100)
            logger.info(f"Found {len(all_docs)} documents in Pinecone")
            
            for doc in all_docs:
                doc_id = doc.metadata.get("document_id")
                if doc_id:
                    # Check FGA permissions if connected
                    if authorization_manager.is_connected():
                        has_access = await authorization_manager.check_access(
                            user_email, doc_id, "viewer"
                        )
                        if not has_access:
                            logger.debug(f"Skipping document {doc_id} - no access for {user_email}")
                            continue
                    # For demo mode (no FGA), allow all documents
                    
                    accessible_documents.append(DocumentResponse(
                        document_id=doc_id,
                        title=doc.metadata.get("title", "Untitled"),
                        content=doc.metadata.get("content", doc.page_content),  # Prefer metadata content
                        metadata=doc.metadata,
                        created_at=datetime.fromisoformat(
                            doc.metadata.get("created_at", datetime.now().isoformat())
                        ),
                        owner_email=doc.metadata.get("owner", "unknown")
                    ))
        except Exception as e:
            logger.error(f"Failed to search Pinecone documents: {e}")
            # Fallback to empty list
        
        return DocumentListResponse(
            documents=accessible_documents,
            total=len(accessible_documents)
        )
        
    except Exception as e:
        logger.error(f"Document list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")

@router.post("/{document_id}/share")
async def share_document(
    document_id: str,
    share_request: DocumentShare,
    current_user: dict = Depends(get_current_user)
):
    """Share a document with another user"""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found")
        
        # Check if user owns the document
        has_owner_permission = await authorization_manager.check_access(
            user_email, document_id, "owner"
        )
        
        if not has_owner_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to share this document")
        
        # Add FGA relation for the target user
        success = await authorization_manager.add_relation(
            share_request.user_email, 
            document_id, 
            share_request.relation
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to share document")
        
        return {"message": f"Document shared with {share_request.user_email}"}
        
    except Exception as e:
        logger.error(f"Document share error: {e}")
        raise HTTPException(status_code=500, detail="Document sharing failed")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document (only owner can delete)"""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found")
        
        # Check if user owns the document
        has_owner_permission = await authorization_manager.check_access(
            user_email, document_id, "owner"
        )
        
        if not has_owner_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this document")
        
        # Remove from Pinecone
        await document_retriever.pinecone_store.delete_document(document_id)
        
        # Remove FGA relations
        await authorization_manager.delete_relation(user_email, document_id, "owner")
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(f"Document delete error: {e}")
        raise HTTPException(status_code=500, detail="Document deletion failed")

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific document"""
    try:
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found")
        
        logger.info(f"Checking access for user: {user_email} to document: {document_id}")
        
        # Check if user has access
        has_permission = await authorization_manager.check_access(
            user_email, document_id, "viewer"
        )
        
        logger.info(f"Permission check result: {has_permission}")
        
        if not has_permission:
            logger.warning(f"Access denied for user: {user_email} to document: {document_id}")
            raise HTTPException(status_code=403, detail="You don't have access to this document")
        
        # Get document from Pinecone
        logger.info(f"Getting document metadata for ID: {document_id}")
        doc_metadata = await document_retriever.pinecone_store.get_document_metadata(document_id)
        logger.info(f"Document metadata result: {doc_metadata}")
        
        if not doc_metadata:
            logger.warning(f"Document not found in Pinecone: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Successfully retrieved document metadata, creating response...")
        
        # For now, we'll return the metadata. In a full implementation, you'd want to store content separately
        # or retrieve it from Pinecone using a different approach
        response = DocumentResponse(
            document_id=document_id,
            title=doc_metadata.get("title", "Untitled"),
            content=doc_metadata.get("content", "Content not available"),  # Get content from metadata
            metadata=doc_metadata,
            created_at=datetime.fromisoformat(
                doc_metadata.get("created_at", datetime.now().isoformat())
            ),
            owner_email=doc_metadata.get("owner", "unknown")
        )
        
        logger.info(f"Response created successfully: {response.title}")
        return response
        
    except HTTPException as e:
        logger.error(f"HTTP Exception in get_document: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")
