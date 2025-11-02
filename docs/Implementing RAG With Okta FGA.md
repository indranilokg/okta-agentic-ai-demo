# Implementing RAG with Okta Fine-Grained Authorization (FGA) and Vector Databases

## Overview

This technical guide demonstrates how to implement a Retrieval-Augmented Generation (RAG) system with Okta Fine-Grained Authorization (FGA) using a vector database (Pinecone) and LangChain agents. This architecture ensures that users can only access documents they are authorized to view, even when using AI-powered search.

**Note**: This guide uses the [Auth0 AI for LangChain Python SDK](https://auth0.com/ai/docs/sdks/langchain-sdk#auth0-ai-for-langchain-2), which provides building blocks for using Auth0 for AI Agents with LangChain and LangGraph, including a RAG Retriever for OpenFGA integration.

## Architecture

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │
       │ 1. User Query
       ▼
┌─────────────────────────────────────┐
│      LangChain Agent                │
│  (with RAG Tool)                    │
└──────┬───────────────────────────────┘
       │
       │ 2. Search Request
       ▼
┌─────────────────────────────────────┐
│   Vector Database (Pinecone)        │
│   ┌─────────────────────────────┐  │
│   │ Semantic Search              │  │
│   │ Returns: Candidate Docs      │  │
│   └─────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       │ 3. Candidate Documents
       ▼
┌─────────────────────────────────────┐
│   FGA Authorization Layer           │
│   ┌─────────────────────────────┐  │
│   │ Check Permissions            │  │
│   │ Filter: Authorized Docs    │  │
│   └─────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       │ 4. Authorized Documents
       ▼
┌─────────────────────────────────────┐
│   LLM (OpenAI)                      │
│   ┌─────────────────────────────┐  │
│   │ Generate Response            │  │
│   │ with Context                 │  │
│   └─────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       │ 5. Final Answer
       ▼
┌─────────────────────────────────────┐
│   Client (Frontend)                 │
└─────────────────────────────────────┘
```

## Key Components

### 1. Vector Database Store (Pinecone)

The vector database stores document embeddings and enables semantic search.

### 2. Okta FGA Authorization Manager

Manages fine-grained access control using Okta Fine-Grained Authorization (OpenFGA).

### 3. Document Retriever

Combines vector search with FGA filtering to return only authorized documents.

### 4. LangChain Tool

Integrates the RAG system with LangChain agents.

## Implementation Steps

### Step 1: Set Up Vector Database (Pinecone)

#### 1.1 Initialize Pinecone Client

```python
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

class PineconeDocumentStore:
    def __init__(self):
        self.pc = None
        self.index = None
        self.vectorstore = None
        self.embeddings = None
        
    async def initialize(self):
        """Initialize Pinecone connection and index"""
        # Get configuration
        api_key = os.getenv('PINECONE_API_KEY')
        environment = os.getenv('PINECONE_ENVIRONMENT')
        index_name = os.getenv('PINECONE_INDEX_NAME', 'documents')
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=api_key)
        
        # Initialize embeddings
        openai_api_key = os.getenv('OPENAI_API_KEY')
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model="text-embedding-3-small"
        )
        
        # Create index if it doesn't exist
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=1536,  # text-embedding-3-small dimension
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=environment
                )
            )
            
        # Get index
        self.index = self.pc.Index(index_name)
        
        # Initialize vector store
        self.vectorstore = PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings
        )
```

#### 1.2 Add Documents to Vector Database

```python
async def add_document(
    self, 
    content: str, 
    metadata: Dict[str, Any], 
    document_id: Optional[str] = None
) -> str:
    """Add a document to Pinecone"""
    if not self.index or not self.embeddings:
        raise ValueError("Pinecone not initialized")
    
    # Generate embedding for the content
    embedding = self.embeddings.embed_query(content)
    
    # Use provided document_id or generate a new one
    doc_id = document_id or str(uuid.uuid4())
    
    # Prepare metadata (ensure document_id is included)
    doc_metadata = {
        **metadata,
        'document_id': doc_id,
        'created_at': datetime.now().isoformat(),
        'content': content  # Store content in metadata for retrieval
    }
    
    # Use Pinecone's upsert method directly with custom ID
    self.index.upsert(
        vectors=[{
            'id': doc_id,
            'values': embedding,
            'metadata': doc_metadata
        }]
    )
    
    return doc_id
```

#### 1.3 Search Documents

```python
async def search_documents(self, query: str, k: int = 5) -> List[Document]:
    """Search for similar documents"""
    # Generate embedding for the query
    query_embedding = self.embeddings.embed_query(query)
    
    # Query Pinecone
    query_response = self.index.query(
        vector=query_embedding,
        top_k=k,
        include_metadata=True
    )
    
    # Convert to Document objects
    documents = []
    for match in query_response.matches:
        doc = Document(
            page_content=match.metadata.get('content', ''),
            metadata=match.metadata
        )
        documents.append(doc)
    
    return documents
```

### Step 2: Set Up Okta FGA Authorization

**Installation**: First, install the Auth0 AI for LangChain Python SDK:

```bash
pip install auth0-ai-langchain
```

For more information about the SDK, see the [Auth0 AI for LangChain Python SDK documentation](https://auth0.com/ai/docs/sdks/langchain-sdk#auth0-ai-for-langchain-2).

#### 2.1 Initialize Okta FGA Client

```python
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.credentials import Credentials, CredentialConfiguration

class AuthorizationManager:
    """Manages Okta FGA authorization for document access control"""
    
    def __init__(self):
        self.openfga_client: Optional[OpenFgaClient] = None
        self._connect()
    
    def _connect(self):
        """Connect to Okta FGA"""
        fga_store_id = os.getenv('FGA_STORE_ID')
        fga_client_id = os.getenv('FGA_CLIENT_ID')
        fga_client_secret = os.getenv('FGA_CLIENT_SECRET')
        
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
        
        self.openfga_client = OpenFgaClient(openfga_client_config)
```

#### 2.2 Add FGA Relations

```python
async def add_relation(
    self, 
    user_email: str, 
    document_id: str, 
    relation: str = "owner"
) -> bool:
    """Add a relation between user and document"""
    from openfga_sdk.client.models import ClientTuple, ClientWriteRequest
    
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
    return True
```

#### 2.3 Check Permissions

```python
async def check_access(
    self, 
    user_email: str, 
    document_id: str, 
    relation: str = "viewer"
) -> bool:
    """Check if user has permission to access document"""
    from openfga_sdk.client.models import ClientCheckRequest
    
    response = await self.openfga_client.check(
        ClientCheckRequest(
            user=f"user:{user_email}",
            relation=relation,
            object=f"doc:{document_id}"
        )
    )
    return response.allowed
```

### Step 3: Combine Vector Search with FGA Filtering

```python
class DocumentRetriever:
    """Document retriever with Okta FGA authorization filtering"""
    
    def __init__(self):
        self.pinecone_store = pinecone_store
    
    async def search_documents(
        self, 
        query: str, 
        user_email: str
    ) -> List[str]:
        """Search documents with FGA authorization filtering"""
        # Step 1: Search Pinecone for similar documents
        documents = await self.pinecone_store.search_documents(query, k=10)
        
        # Step 2: Filter by FGA permissions
        authorized_docs = []
        for doc in documents:
            doc_id = doc.metadata.get("document_id")
            if doc_id:
                # Check FGA permission
                from auth.fga_manager import authorization_manager
                has_permission = await authorization_manager.check_access(
                    user_email, doc_id, "viewer"
                )
                
                if has_permission:
                    authorized_docs.append(doc.page_content)
        
        return authorized_docs
```

### Step 4: Create LangChain Tool

The [Auth0 AI for LangChain Python SDK](https://auth0.com/ai/docs/sdks/langchain-sdk#auth0-ai-for-langchain-2) provides a `FGARetriever` class that can be used directly with LangChain. Alternatively, you can create a custom tool as shown below:

```python
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
# Alternative: from auth0_ai_langchain import FGARetriever

class GetContextDocsSchema(BaseModel):
    question: str

async def get_context_docs_fn(question: str, config: RunnableConfig):
    """RAG tool that retrieves authorized documents based on user permissions"""
    
    # Extract user information from config
    credentials = config["configurable"]["_credentials"]
    user = credentials.get("user")
    user_email = user.get("email")
    
    if not user_email:
        return "User email not found in credentials."
    
    # Search documents with FGA filtering
    document_retriever = DocumentRetriever()
    documents = await document_retriever.search_documents(question, user_email)
    
    if not documents:
        return "No authorized documents found for this query."
    
    # Combine documents into context
    context = "\n\n".join(documents)
    return context

# Create the LangChain tool
get_context_docs = StructuredTool(
    name="get_context_docs",
    description="Use this tool when user asks for documents, projects, or anything stored in the knowledge base. This tool respects user permissions.",
    args_schema=GetContextDocsSchema,
    coroutine=get_context_docs_fn,
)
```

### Step 5: Integrate with LangChain Agent

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Create agent with RAG tool
tools = [get_context_docs]  # Your FGA-protected RAG tool

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to authorized documents."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run agent with user context
result = await agent_executor.ainvoke(
    {
        "input": "What documents do I have access to about security?",
        "chat_history": [],
    },
    config={
        "configurable": {
            "_credentials": {
                "user": {
                    "email": "user@example.com"  # From authenticated session
                }
            }
        }
    }
)
```

## Complete Flow Example

### Document Upload with FGA

```python
@router.post("/api/documents/upload")
async def upload_document(
    document: DocumentUpload,
    current_user: dict = Depends(get_current_user)
):
    """Upload a document and create FGA relations"""
    user_email = current_user.get("email")
    document_id = str(uuid.uuid4())
    
    # Add document to vector database
    metadata = {
        "title": document.title,
        "owner": user_email,
        "created_at": datetime.now().isoformat(),
    }
    
    await document_retriever.add_document(
        document_id, 
        document.content, 
        metadata
    )
    
    # Add FGA relations (owner and viewer)
    await authorization_manager.add_relation(
        user_email, document_id, "owner"
    )
    await authorization_manager.add_relation(
        user_email, document_id, "viewer"
    )
    
    return {"document_id": document_id, "status": "uploaded"}
```

### Document Search with Authorization

```python
@router.get("/api/documents/search")
async def search_documents(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """Search documents with FGA filtering"""
    user_email = current_user.get("email")
    
    # This automatically filters by FGA permissions
    documents = await document_retriever.search_documents(query, user_email)
    
    return {"documents": documents, "count": len(documents)}
```

## FGA Authorization Model

Your Okta FGA authorization model should define relations like:

```python
model = """
type user

type doc
  relations
    define owner: [user]
    define viewer: [user] or owner
"""
```

This model allows:
- Users to be explicitly assigned as `owner` or `viewer`
- `viewer` relation to be inherited from `owner` (via `or owner`)

## Key Considerations

### 1. User Identity Extraction

Always extract the user's email from the authenticated session/token:

```python
# From JWT token
user_email = current_user.get("email")

# Or from LangChain config
credentials = config["configurable"]["_credentials"]
user_email = credentials.get("user", {}).get("email")
```

### 2. Document ID Consistency

Ensure the `document_id` used in Pinecone matches the ID used in FGA relations:

```python
# Use the same document_id everywhere
document_id = str(uuid.uuid4())

# In Pinecone
self.index.upsert(vectors=[{'id': document_id, ...}])

# In FGA
await authorization_manager.add_relation(
    user_email, document_id, "owner"
)
```

### 3. Error Handling

Implement graceful fallbacks for FGA checks:

```python
async def check_access(...) -> bool:
    """Check if user has permission to access document"""
    if not self.openfga_client:
        # Demo mode - allow access
        return True
        
    try:
        response = await self.openfga_client.check(...)
        return response.allowed
    except Exception as e:
        logger.warning(f"FGA check failed ({e}) - denying access")
        return False  # Fail closed for security
```

### 4. Performance Optimization

- **Batch FGA Checks**: Use batch check API for multiple documents
- **Caching**: Cache FGA permission results for short durations
- **Index Optimization**: Ensure Pinecone index is properly configured

## Environment Variables

```bash
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=documents

# Okta FGA Configuration
FGA_STORE_ID=your_fga_store_id
FGA_CLIENT_ID=your_fga_client_id
FGA_CLIENT_SECRET=your_fga_client_secret
FGA_API_URL=https://api.us1.fga.dev
FGA_AUTHORIZATION_MODEL_ID=your_model_id

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
```

## Testing

### Test Document Upload

```python
# Upload a document
response = await client.post(
    "/api/documents/upload",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "title": "Security Policy",
        "content": "Document content here..."
    }
)
document_id = response.json()["document_id"]
```

### Test FGA Filtering

```python
# Search as different users
user1_docs = await document_retriever.search_documents(
    "security", 
    "user1@example.com"
)

user2_docs = await document_retriever.search_documents(
    "security", 
    "user2@example.com"
)

# user1_docs and user2_docs will be different based on FGA permissions
```

## Best Practices

1. **Always Check Permissions**: Never skip FGA checks, even in demo mode (fail closed)

2. **Consistent Document IDs**: Use the same UUID format across Pinecone and FGA

3. **Store Content in Metadata**: Store document content in Pinecone metadata for efficient retrieval

4. **Log Authorization Decisions**: Log all FGA checks for audit trails

5. **Handle Errors Gracefully**: Implement proper error handling and fallbacks

6. **Test Authorization**: Always test with multiple users to verify FGA filtering works

7. **Monitor Performance**: Track FGA check latency and optimize if needed

## Conclusion

This implementation provides a secure RAG system where:
- Documents are stored in a vector database for semantic search
- Okta Fine-Grained Authorization controls access at query time
- LangChain agents seamlessly integrate authorization checks
- Users only see documents they are authorized to view

The combination of vector search and Okta FGA ensures both powerful semantic search capabilities and strong security boundaries.


