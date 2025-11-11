"""
Pinecone Vector Store Implementation for Streamward RAG System
"""
import os
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class PineconeDocumentStore:
    """
    Pinecone-based document storage with embeddings for RAG
    """
    
    def __init__(self):
        self.pc = None
        self.index = None
        self.vectorstore = None
        self.embeddings = None
        self.index_name = None
        
    async def initialize(self):
        """Initialize Pinecone connection and index"""
        try:
            # Get Pinecone configuration
            api_key = os.getenv('PINECONE_API_KEY')
            environment = os.getenv('PINECONE_ENVIRONMENT')
            self.index_name = os.getenv('PINECONE_INDEX_NAME', 'streamward-documents')
            
            if not api_key or not environment:
                logger.warning("Pinecone configuration missing. Using mock store.")
                return False
                
            # Initialize Pinecone
            self.pc = Pinecone(api_key=api_key)
            
            # Initialize embeddings
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.error("OPENAI_API_KEY required for embeddings")
                return False
                
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=openai_api_key,
                model="text-embedding-3-small"
            )
            
            # Check if index exists, create if not
            if self.index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # text-embedding-3-small dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=environment
                    )
                )
                
                # Wait for index to be ready
                import time
                time.sleep(10)
            
            # Get index
            self.index = self.pc.Index(self.index_name)
            
            # Initialize vector store
            self.vectorstore = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings
            )
            
            logger.info(f" Pinecone initialized successfully with index: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            return False
    
    async def add_document(self, content: str, metadata: Dict[str, Any], document_id: Optional[str] = None) -> str:
        """Add a document to Pinecone
        
        Args:
            content: Document content
            metadata: Document metadata
            document_id: Optional document ID. If not provided, a new UUID will be generated.
        """
        if not self.index or not self.embeddings:
            logger.error("Pinecone not initialized")
            return None
            
        try:
            # Use provided document_id or generate a new one
            doc_id = document_id or str(uuid.uuid4())
            
            # Generate embedding for the content
            embedding = self.embeddings.embed_query(content)
            
            # Prepare metadata (ensure document_id is in metadata for consistency)
            doc_metadata = {
                **metadata,
                'document_id': doc_id,
                'created_at': datetime.now().isoformat(),
                'content': content  # Store content in metadata for retrieval
            }
            
            # Use Pinecone's upsert method directly with our custom ID
            upsert_response = self.index.upsert(
                vectors=[{
                    'id': doc_id,
                    'values': embedding,
                    'metadata': doc_metadata
                }]
            )
            logger.info(f"Upsert response: {upsert_response}")
            
            logger.info(f" Document added to Pinecone with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document to Pinecone: {e}")
            return None
    
    async def search_documents(self, query: str, k: int = 5) -> List[Document]:
        """Search for similar documents"""
        if not self.index or not self.embeddings:
            logger.error("Pinecone not initialized")
            return []
            
        try:
            # Generate embedding for the query
            query_embedding = self.embeddings.embed_query(query)
            
            # Query Pinecone directly (like list_all_documents)
            query_response = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True
            )
            
            documents = []
            for match in query_response.matches:
                # Extract content from metadata (where we store it)
                content = match.metadata.get('content', '')
                
                # Create Document with content in page_content
                doc = Document(
                    page_content=content,
                    metadata=match.metadata
                )
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents for query: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to search Pinecone: {e}")
            return []
    
    async def list_all_documents(self, k: int = 100) -> List[Document]:
        """List all documents by querying with a dummy vector"""
        if not self.index or not self.embeddings:
            logger.error("Pinecone not initialized")
            return []
            
        try:
            # Use a dummy query to get a broad set of documents
            # Using a generic query that should match most documents
            dummy_query = "document"
            query_embedding = self.embeddings.embed_query(dummy_query)
            
            # Query Pinecone with a large top_k to get all documents
            query_response = self.index.query(
                vector=query_embedding,
                top_k=min(k, 10000),  # Pinecone limit is typically 10000
                include_metadata=True
            )
            
            documents = []
            for match in query_response.matches:
                # Convert match to Document format
                doc = Document(
                    page_content=match.metadata.get('content', ''),
                    metadata=match.metadata
                )
                documents.append(doc)
            
            logger.info(f"Listed {len(documents)} documents from Pinecone")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list all documents from Pinecone: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from Pinecone"""
        if not self.index:
            logger.error("Pinecone not initialized")
            return False
            
        try:
            # Delete by document_id metadata
            self.index.delete(filter={"document_id": document_id})
            logger.info(f" Document deleted from Pinecone: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document from Pinecone: {e}")
            return False
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata including content"""
        if not self.index:
            logger.error("Pinecone not initialized")
            return None
            
        try:
            # Use fetch to get document by ID
            logger.info(f"Fetching document from Pinecone: {document_id}")
            fetch_response = self.index.fetch(ids=[document_id])
            logger.info(f"Fetch response: {len(fetch_response.vectors)} vectors found")
            
            if document_id in fetch_response.vectors:
                vector_data = fetch_response.vectors[document_id]
                metadata = vector_data.metadata
                logger.info(f"Found metadata: {metadata}")
                
                # Ensure content is included in metadata
                if 'content' not in metadata:
                    logger.warning(f"Content not found in metadata for document {document_id}")
                
                return metadata
            else:
                logger.warning(f"Document ID {document_id} not found in fetch response")
                logger.info(f"Available IDs: {list(fetch_response.vectors.keys())}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document metadata: {e}")
            return None

# Global instance
pinecone_store = PineconeDocumentStore()
