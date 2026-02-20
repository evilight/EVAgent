"""
Main FastAPI application for EVAgent RAG system.
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Include routers
try:
    from routers import auth, chat, search, system
    from middleware.auth import get_auth_service
except ImportError:
    # Fallback for testing - add EVAgent src to path
    import sys
    import os
    # Add the EVAgent/src directory to Python path
    evagent_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if evagent_src not in sys.path:
        sys.path.insert(0, evagent_src)
    from api.routers import auth, chat, search, system
    from api.middleware.auth import get_auth_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting EVAgent RAG API...")
    
    # Initialize auth service
    get_auth_service()
    
    logger.info("EVAgent RAG API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EVAgent RAG API...")


# Create FastAPI application
app = FastAPI(
    title="EVAgent RAG API",
    description="RAG (Retrieval-Augmented Generation) API for EVAgent system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "EVAgent RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/system/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Simple health check."""
    return {
        "status": "healthy",
        "service": "EVAgent RAG API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    # Run the application
    import time
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
