"""
System router for health checks and statistics with authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime

from api.middleware.auth import get_current_user_token
from api.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    uptime: Optional[float] = None


class SystemStats(BaseModel):
    """System statistics."""
    total_documents: int
    total_conversations: int
    total_searches: int
    uptime: float
    memory_usage: Optional[Dict[str, Any]] = None
    model_info: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint (no authentication required).
    
    Returns:
        System health status
    """
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime=0.0  # Would calculate actual uptime
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(username: str = Depends(get_current_user_token)):
    """
    Get system statistics (authentication required).
    
    Args:
        username: Current authenticated user
        
    Returns:
        System statistics
    """
    try:
        rag_service = RAGService()
        stats = await rag_service.get_system_stats()
        
        # Add user-specific stats
        user_stats = await rag_service.get_user_stats(username)
        stats.update(user_stats)
        
        logger.info(f"System stats retrieved for user {username}")
        
        return SystemStats(**stats)
        
    except Exception as e:
        logger.error(f"System stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system statistics"
        )


@router.get("/info")
async def get_system_info(username: str = Depends(get_current_user_token)):
    """
    Get system information.
    
    Args:
        username: Current authenticated user
        
    Returns:
        System information
    """
    try:
        rag_service = RAGService()
        info = await rag_service.get_system_info()
        
        return {
            "system": info,
            "user": username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system information"
        )


@router.post("/reset")
async def reset_system(
    confirm: bool = False,
    username: str = Depends(get_current_user_token)
):
    """
    Reset system (admin only - would need role check).
    
    Args:
        confirm: Confirmation flag
        username: Current authenticated user
        
    Returns:
        Reset status
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required"
            )
        
        # Would check if user has admin role
        if username != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        rag_service = RAGService()
        await rag_service.reset_system()
        
        logger.warning(f"System reset performed by user {username}")
        
        return {"message": "System reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting system"
        )
