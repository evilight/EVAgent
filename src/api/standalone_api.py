"""
Standalone FastAPI application for EVAgent RAG system.
This version works without the complex relative import issues in the main codebase.
Version: 1.1.0 - Added JSON login
"""

import os
import sys
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer
from pydantic import BaseModel
import jwt
import uvicorn

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

# Pydantic Models
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserInfo(BaseModel):
    username: str
    roles: List[str] = ["user"]

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class SourceDocument(BaseModel):
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument] = []
    conversation_id: Optional[str] = None
    timestamp: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    similarity_threshold: float = 0.7

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int
    username: str

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str

# Auth functions
def authenticate_user(username: str, password: str) -> bool:
    return USERS.get(username) == password

def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_current_user_token(token: str = Depends(bearer)) -> str:
    return verify_token(token.credentials)

# Router setup
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
chat_router = APIRouter(prefix="/chat", tags=["chat"])
search_router = APIRouter(prefix="/search", tags=["search"])
system_router = APIRouter(prefix="/system", tags=["system"])

@auth_router.post("/login", response_model=LoginResponse)
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    """Login with Basic Auth to get JWT token."""
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    access_token = create_access_token(credentials.username)
    logger.info(f"User {credentials.username} logged in successfully")
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 3600
    )

# JSON-based login for easier testing - v2
class LoginRequest(BaseModel):
    username: str
    password: str

@auth_router.post("/login-json", response_model=LoginResponse)
async def login_json(request: LoginRequest):
    """Login with JSON credentials to get JWT token."""
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token = create_access_token(request.username)
    logger.info(f"User {request.username} logged in successfully (JSON)")
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 3600
    )

@auth_router.get("/me", response_model=UserInfo)
async def get_current_user_info(username: str = Depends(get_current_user_token)):
    return UserInfo(username=username, roles=["user"])

@auth_router.post("/logout")
async def logout(username: str = Depends(get_current_user_token)):
    logger.info(f"User {username} logged out")
    return {"message": "Successfully logged out"}

@chat_router.post("/", response_model=ChatResponse)
async def chat_message(request: ChatRequest, username: str = Depends(get_current_user_token)):
    # Mock response for now - integrate real RAG later
    answer = f"This is a mock response to: '{request.message}'. Real RAG integration coming soon."
    
    return ChatResponse(
        answer=answer,
        sources=[],
        conversation_id=request.conversation_id or "mock-conv-id",
        timestamp=datetime.utcnow().isoformat()
    )

@search_router.post("/", response_model=SearchResponse)
async def search_documents(request: SearchRequest, username: str = Depends(get_current_user_token)):
    # Mock search results for now
    mock_results = [
        SearchResult(
            id="doc-1",
            title="Mock Document 1",
            content="This is mock content for testing.",
            score=0.85,
            metadata={"source": "test"},
            source="mock"
        )
    ]
    
    return SearchResponse(
        query=request.query,
        results=mock_results,
        total=len(mock_results),
        username=username
    )

@system_router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )

@system_router.get("/stats")
async def get_system_stats(username: str = Depends(get_current_user_token)):
    return {
        "total_documents": 0,
        "total_conversations": 0,
        "total_searches": 0,
        "uptime": 0.0,
        "model_info": {
            "embedding_model": "all-MiniLM-L6-v2 (local)",
            "llm_model": "deepseek"
        }
    }

# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EVAgent RAG API...")
    logger.info(f"Default user: {DEFAULT_USERNAME}")
    # Log all registered routes
    for route in app.routes:
        if hasattr(route, 'methods') and route.path.startswith('/api'):
            logger.info(f"  Route: {route.path} {route.methods}")
    yield
    logger.info("Shutting down EVAgent RAG API...")

app = FastAPI(
    title="EVAgent RAG API",
    description="RAG (Retrieval-Augmented Generation) API for EVAgent system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "EVAgent RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/system/health"
    }

@app.get("/health")
async def simple_health_check():
    return {"status": "healthy", "service": "EVAgent RAG API", "version": "1.0.0"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    uvicorn.run("standalone_api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
