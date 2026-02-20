"""
Authentication router for EVAgent RAG system.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from typing import Dict, Any
import logging

from api.middleware.auth import get_auth_service, get_current_user_basic, get_current_user_token
from api.models.chat import ChatRequest, ChatResponse, ChatMessage
from api.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """User information model."""
    username: str
    roles: list[str] = ["user"]


@router.post("/login", response_model=LoginResponse)
async def login(credentials: HTTPBasicCredentials = Depends(get_current_user_basic)):
    """
    Login with Basic Auth and return JWT token.
    
    Args:
        credentials: Basic auth credentials
        
    Returns:
        JWT access token
    """
    try:
        auth_service = get_auth_service()
        username = credentials.username
        
        # Create access token
        access_token = auth_service.create_access_token(username)
        
        logger.info(f"User {username} logged in successfully")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=24 * 3600  # 24 hours in seconds
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(username: str = Depends(get_current_user_token)):
    """
    Get current user information.
    
    Args:
        username: Current username from token
        
    Returns:
        User information
    """
    try:
        return UserInfo(username=username, roles=["user"])
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(username: str = Depends(get_current_user_token)):
    """
    Logout endpoint (token invalidation would need server-side state).
    
    Args:
        username: Current username from token
        
    Returns:
        Success message
    """
    try:
        logger.info(f"User {username} logged out")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )


@router.get("/verify")
async def verify_token(username: str = Depends(get_current_user_token)):
    """
    Verify if token is valid.
    
    Args:
        username: Current username from token
        
    Returns:
        Verification status
    """
    try:
        return {"valid": True, "username": username}
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
