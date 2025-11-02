import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
import os

from auth.okta_auth import OktaAuth

logger = logging.getLogger(__name__)

class RAGTool:
    """
    RAG Tool with DPOP protection for document search
    Handles vector search with fine-grained authorization
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=1500
        )
        
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize Pinecone
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "streamward-documents")
        
        if self.pinecone_api_key:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(self.pinecone_index_name)
        else:
            logger.warning("Pinecone API key not provided, using mock data")
            self.index = None
        
        # Initialize auth
        self.okta_auth = OktaAuth()
        
        # Mock document data for demo
        self.mock_documents = self._initialize_mock_documents()
        
        self.system_prompt = """
You are the Streamward Document Search Assistant. Your responsibilities include:

1. **Document Search**: Semantic search across company documents
2. **DPOP Protection**: All requests are protected with DPOP cryptographic proofs
3. **Fine-Grained Authorization**: Filter documents based on user permissions
4. **Context-Aware Responses**: Provide relevant information with source citations

Always maintain security and provide accurate, helpful responses with proper citations.
"""

    def _initialize_mock_documents(self) -> List[Dict[str, Any]]:
        """Initialize mock document data"""
        return [
            {
                "id": "doc-001",
                "title": "Employee Handbook 2024",
                "content": "This handbook contains all company policies including code of conduct, benefits, and procedures.",
                "category": "HR",
                "department_access": ["HR", "All"],
                "security_level": "internal",
                "tags": ["policies", "handbook", "hr", "benefits"],
                "last_updated": "2024-01-01"
            },
            {
                "id": "doc-002",
                "title": "Expense Reimbursement Policy",
                "content": "Employees may submit expense reports for business-related costs. All expenses over $1000 require manager approval.",
                "category": "Finance",
                "department_access": ["Finance", "All"],
                "security_level": "internal",
                "tags": ["expenses", "reimbursement", "finance", "policy"],
                "last_updated": "2024-01-15"
            },
            {
                "id": "doc-003",
                "title": "Data Privacy Policy",
                "content": "This policy outlines how we handle personal data in compliance with GDPR and CCPA regulations.",
                "category": "Legal",
                "department_access": ["Legal", "HR", "IT"],
                "security_level": "confidential",
                "tags": ["privacy", "gdpr", "ccpa", "data", "legal"],
                "last_updated": "2024-01-10"
            },
            {
                "id": "doc-004",
                "title": "IT Security Guidelines",
                "content": "Guidelines for maintaining security including password policies, access controls, and incident response.",
                "category": "IT",
                "department_access": ["IT", "All"],
                "security_level": "internal",
                "tags": ["security", "it", "passwords", "access", "incident"],
                "last_updated": "2024-01-20"
            },
            {
                "id": "doc-005",
                "title": "Partner Agreement Template",
                "content": "Standard template for partner agreements including SLAs, terms, and conditions.",
                "category": "Legal",
                "department_access": ["Legal", "Business"],
                "security_level": "confidential",
                "tags": ["partners", "agreements", "sla", "legal", "contracts"],
                "last_updated": "2024-01-05"
            }
        ]

    async def search_documents(self, query: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search documents with DPOP protection and fine-grained authorization
        """
        try:
            logger.info(f"Document search query: {query[:100]}...")
            
            # Verify DPOP proof (simplified for demo)
            dpop_valid = await self._verify_dpop_proof(user_info)
            if not dpop_valid:
                return {
                    "response": "Access denied: Invalid DPOP proof",
                    "metadata": {"error": "dpop_verification_failed"}
                }
            
            # Check user permissions
            user_permissions = await self._get_user_permissions(user_info)
            
            # Filter documents based on permissions
            accessible_documents = self._filter_documents_by_permissions(self.mock_documents, user_permissions)
            
            # Perform semantic search
            if self.index:
                # Use Pinecone for vector search
                search_results = await self._vector_search(query, accessible_documents)
            else:
                # Use mock search for demo
                search_results = await self._mock_search(query, accessible_documents)
            
            # Generate response with citations
            response = await self._generate_response(query, search_results, user_info)
            
            return {
                "response": response,
                "metadata": {
                    "query": query,
                    "results_count": len(search_results),
                    "accessible_documents": len(accessible_documents),
                    "total_documents": len(self.mock_documents),
                    "dpop_verified": True,
                    "user_permissions": user_permissions
                }
            }
            
        except Exception as e:
            logger.error(f"Document search error: {e}")
            return {
                "response": "I encountered an error searching documents. Please try again.",
                "metadata": {"error": str(e)}
            }

    async def _verify_dpop_proof(self, user_info: Dict[str, Any]) -> bool:
        """
        Verify DPOP proof for request authenticity
        In production, this would verify the cryptographic proof
        """
        try:
            # Simplified DPOP verification for demo
            # In production, you'd verify the JWT signature and claims
            
            # Check if user has valid token
            if not user_info.get("sub"):
                return False
            
            # Simulate DPOP verification
            await asyncio.sleep(0.1)  # Simulate verification time
            
            logger.info("DPOP proof verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"DPOP verification error: {e}")
            return False

    async def _get_user_permissions(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user permissions for document access
        """
        try:
            user_groups = user_info.get("groups", [])
            user_department = user_info.get("department", "Unknown")
            
            # Determine access level based on groups and department
            permissions = {
                "departments": user_groups + [user_department],
                "security_levels": ["internal"],  # Default
                "categories": ["HR", "Finance", "Legal", "IT"]  # Default accessible categories
            }
            
            # Add elevated permissions for specific groups
            if "admin" in user_groups or "hr" in user_groups:
                permissions["security_levels"].append("confidential")
            
            if "legal" in user_groups:
                permissions["categories"].extend(["Legal", "Compliance"])
            
            if "finance" in user_groups:
                permissions["categories"].extend(["Finance", "Accounting"])
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return {
                "departments": ["Unknown"],
                "security_levels": ["internal"],
                "categories": ["HR"]
            }

    def _filter_documents_by_permissions(self, documents: List[Dict[str, Any]], permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter documents based on user permissions
        """
        accessible_docs = []
        
        for doc in documents:
            # Check department access
            doc_departments = doc.get("department_access", [])
            user_departments = permissions.get("departments", [])
            
            if not any(dept in doc_departments or "All" in doc_departments for dept in user_departments):
                continue
            
            # Check security level
            doc_security = doc.get("security_level", "internal")
            user_security_levels = permissions.get("security_levels", ["internal"])
            
            if doc_security not in user_security_levels:
                continue
            
            # Check category access
            doc_category = doc.get("category", "Unknown")
            user_categories = permissions.get("categories", [])
            
            if doc_category not in user_categories:
                continue
            
            accessible_docs.append(doc)
        
        return accessible_docs

    async def _vector_search(self, query: str, accessible_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform vector search using Pinecone
        """
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Search in Pinecone
            search_response = self.index.query(
                vector=query_embedding,
                top_k=5,
                include_metadata=True
            )
            
            # Process results
            results = []
            for match in search_response.matches:
                doc_id = match.id
                score = match.score
                
                # Find document in accessible documents
                doc = next((d for d in accessible_documents if d["id"] == doc_id), None)
                if doc:
                    results.append({
                        "document": doc,
                        "score": score,
                        "relevance": "high" if score > 0.8 else "medium" if score > 0.6 else "low"
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            # Fallback to mock search
            return await self._mock_search(query, accessible_documents)

    async def _mock_search(self, query: str, accessible_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mock search for demo purposes
        """
        try:
            query_lower = query.lower()
            results = []
            
            for doc in accessible_documents:
                score = 0.0
                
                # Simple keyword matching for demo
                title_match = sum(1 for word in query_lower.split() if word in doc["title"].lower())
                content_match = sum(1 for word in query_lower.split() if word in doc["content"].lower())
                tag_match = sum(1 for word in query_lower.split() if word in doc["tags"])
                
                # Calculate relevance score
                score = (title_match * 0.4 + content_match * 0.4 + tag_match * 0.2) / len(query.split())
                
                if score > 0.1:  # Minimum relevance threshold
                    results.append({
                        "document": doc,
                        "score": score,
                        "relevance": "high" if score > 0.5 else "medium" if score > 0.3 else "low"
                    })
            
            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return results[:5]  # Return top 5 results
            
        except Exception as e:
            logger.error(f"Mock search error: {e}")
            return []

    async def _generate_response(self, query: str, search_results: List[Dict[str, Any]], user_info: Dict[str, Any]) -> str:
        """
        Generate response with citations
        """
        try:
            if not search_results:
                return "I couldn't find any relevant documents matching your query. Please try different keywords or contact support for assistance."
            
            # Prepare context for LLM
            context_docs = []
            for result in search_results[:3]:  # Use top 3 results
                doc = result["document"]
                context_docs.append(f"""
**{doc['title']}** (Category: {doc['category']})
{doc['content'][:500]}...
Last Updated: {doc['last_updated']}
                """)
            
            context = "\n".join(context_docs)
            
            # Generate response using LLM
            prompt = f"""
            Based on the following documents, answer the user's question: "{query}"
            
            Documents:
            {context}
            
            Provide a helpful, accurate response with specific citations to the relevant documents.
            If the information is not available in the documents, clearly state that.
            """
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Add citations
            citations = []
            for i, result in enumerate(search_results[:3], 1):
                doc = result["document"]
                citations.append(f"[{i}] {doc['title']} - {doc['category']}")
            
            if citations:
                response.content += f"\n\n**Sources:**\n" + "\n".join(citations)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "I found relevant documents but encountered an error generating the response. Please try again."

    async def add_document(self, document: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new document to the repository
        """
        try:
            # Verify DPOP proof
            dpop_valid = await self._verify_dpop_proof(user_info)
            if not dpop_valid:
                return {
                    "status": "error",
                    "message": "Access denied: Invalid DPOP proof"
                }
            
            # Check permissions for document addition
            user_permissions = await self._get_user_permissions(user_info)
            if "admin" not in user_permissions.get("departments", []):
                return {
                    "status": "error",
                    "message": "Access denied: Insufficient permissions to add documents"
                }
            
            # Generate document ID
            doc_id = f"doc-{len(self.mock_documents) + 1:03d}"
            document["id"] = doc_id
            document["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            
            # Add to mock documents
            self.mock_documents.append(document)
            
            # In production, you'd also add to Pinecone
            if self.index:
                # Generate embedding and add to Pinecone
                embedding = await self.embeddings.aembed_query(document["content"])
                self.index.upsert([(doc_id, embedding, document)])
            
            return {
                "status": "success",
                "message": f"Document '{document['title']}' added successfully",
                "document_id": doc_id
            }
            
        except Exception as e:
            logger.error(f"Add document error: {e}")
            return {
                "status": "error",
                "message": f"Error adding document: {str(e)}"
            }

    async def get_document(self, document_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a specific document by ID
        """
        try:
            # Verify DPOP proof
            dpop_valid = await self._verify_dpop_proof(user_info)
            if not dpop_valid:
                return {
                    "status": "error",
                    "message": "Access denied: Invalid DPOP proof"
                }
            
            # Find document
            document = next((d for d in self.mock_documents if d["id"] == document_id), None)
            if not document:
                return {
                    "status": "error",
                    "message": "Document not found"
                }
            
            # Check permissions
            user_permissions = await self._get_user_permissions(user_info)
            accessible_docs = self._filter_documents_by_permissions([document], user_permissions)
            
            if not accessible_docs:
                return {
                    "status": "error",
                    "message": "Access denied: Insufficient permissions to view this document"
                }
            
            return {
                "status": "success",
                "document": document
            }
            
        except Exception as e:
            logger.error(f"Get document error: {e}")
            return {
                "status": "error",
                "message": f"Error retrieving document: {str(e)}"
            }
