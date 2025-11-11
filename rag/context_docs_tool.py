import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig
from auth0_ai_langchain import FGARetriever
from openfga_sdk.client.models import ClientBatchCheckItem
from pydantic import BaseModel
import openai

from rag.pinecone_store import pinecone_store

logger = logging.getLogger(__name__)

class GetContextDocsSchema(BaseModel):
    question: str

class DocumentRetriever:
    """Document retriever with Auth0 FGA authorization filtering using Pinecone"""
    
    def __init__(self):
        self.pinecone_store = pinecone_store
    
    async def add_document(self, document_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the Pinecone knowledge base"""
        try:
            # Initialize Pinecone if not already done
            if not self.pinecone_store.vectorstore:
                await self.pinecone_store.initialize()
            
            if not self.pinecone_store.vectorstore:
                logger.error("Pinecone not available")
                return False
            
            # Add document to Pinecone with the provided document_id
            doc_id = await self.pinecone_store.add_document(
                content=content,
                metadata={
                    **(metadata or {}),
                    "document_id": document_id
                },
                document_id=document_id  # Pass the document_id to use as the vector ID
            )
            
            logger.info(f" Added document {document_id} to Pinecone knowledge base")
            return doc_id is not None
            
        except Exception as e:
            logger.error(f" Failed to add document {document_id}: {e}")
            return False
    
    async def search_documents(self, query: str, user_email: str) -> List[str]:
        """Search documents with FGA authorization filtering using Pinecone"""
        try:
            # Initialize Pinecone if not already done
            if not self.pinecone_store.vectorstore:
                await self.pinecone_store.initialize()
            
            if not self.pinecone_store.vectorstore:
                logger.error("Pinecone not available")
                return []
            
            # Search Pinecone for similar documents
            documents = await self.pinecone_store.search_documents(query, k=10)
            
            # Filter by FGA permissions
            authorized_docs = []
            for doc in documents:
                doc_id = doc.metadata.get("document_id")
                if doc_id:
                    # Check FGA permission
                    from auth.fga_manager import authorization_manager
                    logger.debug(f"Checking FGA permission for user: {user_email}, document: {doc_id}, relation: viewer")
                    has_permission = await authorization_manager.check_access(
                        user_email, doc_id, "viewer"
                    )
                    logger.debug(f"Permission result for {doc_id}: {has_permission}")
                    
                    if has_permission:
                        authorized_docs.append(doc.page_content)
                    else:
                        logger.debug(f" No permission for user {user_email} on document {doc_id}")
            
            logger.info(f" Found {len(authorized_docs)} authorized documents out of {len(documents)} total")
            if len(authorized_docs) == 0 and len(documents) > 0:
                logger.warning(f" No authorized documents found! User: {user_email}, Total documents found: {len(documents)}")
                logger.warning(f"   This may indicate FGA permission issues or user email mismatch")
            return authorized_docs
            
        except Exception as e:
            logger.error(f" Failed to search documents: {e}")
            return []

# Global document retriever instance
document_retriever = DocumentRetriever()

async def get_context_docs_fn(question: str, config: RunnableConfig):
    """RAG tool that retrieves authorized documents based on user permissions"""
    
    # Extract user information from config
    if "configurable" not in config or "_credentials" not in config["configurable"]:
        return "There is no user logged in."
    
    credentials = config["configurable"]["_credentials"]
    user = credentials.get("user")
    
    if not user:
        return "There is no user logged in."
    
    user_email = user.get("email")
    if not user_email:
        return "User email not found in credentials."
    
    logger.info(f" Searching documents for user: {user_email}, query: {question}")
    
    # Search documents with FGA filtering
    documents = await document_retriever.search_documents(question, user_email)
    
    if not documents:
        return "No authorized documents found for this query."
    
    # Combine documents
    context = "\n\n".join(documents)
    logger.info(f" Retrieved {len(documents)} authorized documents")
    
    return context

# Create the LangChain tool
get_context_docs = StructuredTool(
    name="get_context_docs",
    description="Use this tool when user asks for documents, projects, or anything stored in the knowledge base. This tool respects user permissions.",
    args_schema=GetContextDocsSchema,
    coroutine=get_context_docs_fn,
)
