"""
Fresh API with forced RAG reinitialization.
"""

import os
import sys
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer
from pydantic import BaseModel
import jwt
import uvicorn

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG components
from api.services.rag_service import RAGService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBasic()
bearer = HTTPBearer()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "admin123")

# Simple user store
USERS = {DEFAULT_USERNAME: DEFAULT_PASSWORD}

# Global RAG service (will be reinitialized on demand)
rag_service = None

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    conversation_id: str

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    username: str

class UserInfo(BaseModel):
    username: str
    roles: List[str]

# Helper functions
def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def authenticate_user(username: str, password: str) -> bool:
    return USERS.get(username) == password

def get_current_user_token(credentials: HTTPBasicCredentials = Depends(security)):
    if authenticate_user(credentials.username, credentials.password):
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
        )

def get_current_user_token_from_bearer(token: str = Depends(bearer)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

def get_rag_service():
    """Get or initialize RAG service with sample data"""
    global rag_service
    if rag_service is None:
        logger.info("*** INITIALIZING FRESH RAG SERVICE WITH SAMPLE DATA ***")
        
        # Create fresh knowledge base first
        kb_config = {
            'persist_directory': 'd:/EVAgent/storage/rag_sample_db',
            'collection_name': 'evagent_sample',
            'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
            'chunk_size': 300,
            'chunk_overlap': 30
        }
        from knowledge.knowledge_base import KnowledgeBase
        fresh_kb = KnowledgeBase(kb_config)
        
        # Create RAG service components with fresh knowledge base
        from langchain_integration.vector_store import ChromaLangChainVectorStore
        from langchain_integration.llm_integration import LLMManager
        from langchain_integration.rag_chain import RAGChain
        
        llm_manager = LLMManager()
        vector_store = ChromaLangChainVectorStore(
            chroma_manager=fresh_kb.chroma_manager,
            embedding_service=fresh_kb.embedding_service
        )
        
        rag_chain = RAGChain(
            vector_store=vector_store,
            llm_manager=llm_manager,
            search_k=5,
            similarity_threshold=0.0,  # Use same as disabled in RAG chain
            enable_hybrid_search=False,  # Disable temporarily
            enable_query_expansion=False,  # Disable temporarily
        )
        
        # Create RAG service manually with fresh components
        from api.services.rag_service import RAGService
        rag_service = RAGService.__new__(RAGService)
        rag_service.knowledge_base = fresh_kb
        rag_service.llm_manager = llm_manager
        rag_service.vector_store = vector_store
        rag_service.rag_chain = rag_chain
        
        logger.info("*** RAG SERVICE REINITIALIZED WITH SAMPLE DATA ***")
    return rag_service

# Routers
auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
search_router = APIRouter(prefix="/api/v1/search", tags=["search"])
system_router = APIRouter(prefix="/api/v1/system", tags=["system"])

@auth_router.post("/login")
async def login(credentials: HTTPBasicCredentials = Depends(get_current_user_token)):
    username = credentials.username
    access_token = create_access_token(username)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400
    )

@auth_router.post("/login-json", response_model=LoginResponse)
async def login_json(request: LoginRequest):
    if not authenticate_user(request.username, request.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(request.username)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400
    )

@auth_router.get("/me", response_model=UserInfo)
async def get_current_user_info(username: str = Depends(get_current_user_token_from_bearer)):
    return UserInfo(username=username, roles=["user"])

@auth_router.post("/logout")
async def logout(username: str = Depends(get_current_user_token_from_bearer)):
    logger.info(f"User {username} logged out")
    return {"message": "Successfully logged out"}

@chat_router.post("/")
async def chat_message(request: ChatRequest, username: str = Depends(get_current_user_token_from_bearer)):
    """Process chat message using RAG."""
    try:
        rag = get_rag_service()
        result = await rag.ask(
            question=request.message,
            conversation_id=request.conversation_id,
            filters=request.filters,
            user_context={"username": username}
        )
        
        return ChatResponse(
            answer=result.get("answer", "I'm sorry, I couldn't process your request."),
            sources=result.get("sources", []),
            conversation_id=result.get("conversation_id")
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message"
        )

@chat_router.post("/simple")
async def simple_chat_message(request: ChatRequest, username: str = Depends(get_current_user_token_from_bearer)):
    """Simple chat endpoint that bypasses RAG chain issues."""
    try:
        rag = get_rag_service()
        
        # Use working search functionality
        search_results = await rag.search(
            query=request.message,
            filters=request.filters,
            limit=5
        )
        
        # Create simple response from search results
        import uuid
        if not search_results:
            response = {
                "answer": "I couldn't find any relevant information to answer your question. Please try different keywords or check your search terms.",
                "sources": [],
                "conversation_id": str(uuid.uuid4())
            }
        else:
            # Extract key information from search results
            relevant_docs = []
            for result in search_results[:3]:  # Use top 3 results
                title = result.get('metadata', {}).get('title', 'Untitled')
                content = result.get('content', '')
                score = result.get('score', 0.0)
                
                # Create a brief summary of each document
                if len(content) > 200:
                    content_preview = content[:200] + "..."
                else:
                    content_preview = content
                    
                relevant_docs.append({
                    "title": title,
                    "content": content_preview,
                    "score": score,
                    "id": result.get('id', 'unknown')
                })
            
            # Generate a simple answer based on the documents found
            if len(relevant_docs) == 1:
                answer = f"Based on the document '{relevant_docs[0]['title']}', I found relevant information. "
                answer += f"The document has a relevance score of {relevant_docs[0]['score']:.2f}. "
                answer += "You can find more details in the search results below."
            elif len(relevant_docs) == 2:
                answer = f"I found 2 relevant documents: '{relevant_docs[0]['title']}' and '{relevant_docs[1]['title']}'. "
                answer += f"The first document has a relevance score of {relevant_docs[0]['score']:.2f} and the second has {relevant_docs[1]['score']:.2f}. "
                answer += "Please review both documents for complete information."
            else:
                answer = f"I found {len(relevant_docs)} relevant documents related to your question. "
                answer += f"The most relevant is '{relevant_docs[0]['title']}' with a score of {relevant_docs[0]['score']:.2f}. "
                answer += "Please review all the search results below for comprehensive information."
            
            response = {
                "answer": answer,
                "sources": relevant_docs,
                "conversation_id": str(uuid.uuid4())
            }
        
        return ChatResponse(
            answer=response.get("answer", "I'm sorry, I couldn't process your request."),
            sources=response.get("sources", []),
            conversation_id=response.get("conversation_id")
        )
        
    except Exception as e:
        logger.error(f"Simple chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing simple chat message"
        )

@search_router.post("/")
async def search_documents(request: SearchRequest, username: str = Depends(get_current_user_token_from_bearer)):
    """Search documents using RAG."""
    try:
        rag = get_rag_service()
        results = await rag.search(
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            username=username
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing search"
        )

@system_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "EVAgent RAG API", "version": "2.0.0"}

@system_router.get("/stats")
async def get_system_stats(username: str = Depends(get_current_user_token_from_bearer)):
    """Get system statistics from RAG service."""
    try:
        rag = get_rag_service()
        stats = await rag.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system statistics"
        )

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EVAgent RAG API v2...")
    logger.info(f"Default user: {DEFAULT_USERNAME}")
    for route in app.routes:
        if hasattr(route, 'methods') and route.path.startswith('/api'):
            logger.info(f"  Route: {route.path} {route.methods}")
    yield

# Create FastAPI app
app = FastAPI(
    title="EVAgent RAG API",
    description="RAG-powered question answering and document search",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(system_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "EVAgent RAG API v2.0", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
