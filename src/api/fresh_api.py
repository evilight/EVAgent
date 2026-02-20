"""
Fresh FastAPI application for EVAgent RAG system.
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

# Add EVAgent src to path for imports
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

# Initialize RAG service
rag_service = RAGService()

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

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

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict] = []
    conversation_id: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10

class SearchResponse(BaseModel):
    query: str
    results: List[Dict]
    total: int
    username: str

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

@chat_router.post("/")
async def chat_message(request: ChatRequest, username: str = Depends(get_current_user_token)):
    """Process chat message using RAG."""
    try:
        result = await rag_service.ask(
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

@search_router.post("/")
async def search_documents(request: SearchRequest, username: str = Depends(get_current_user_token)):
    """Search documents using RAG."""
    try:
        results = await rag_service.search(
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
    return {"status": "healthy", "timestamp": datetime.utcnow(), "version": "1.0.0"}

@system_router.get("/stats")
async def get_system_stats(username: str = Depends(get_current_user_token)):
    """Get system statistics from RAG service."""
    try:
        stats = await rag_service.get_system_stats()
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
    logger.info("Shutting down EVAgent RAG API...")

app = FastAPI(
    title="EVAgent RAG API",
    description="RAG API for EVAgent system",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "EVAgent RAG API v2", "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
async def simple_health_check():
    return {"status": "healthy", "service": "EVAgent RAG API", "version": "2.0.0"}

if __name__ == "__main__":
    uvicorn.run("fresh_api:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
