"""
Search router for EVAgent RAG system with authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from api.middleware.auth import get_current_user_token
from api.models.search import SearchRequest, SearchResponse, SearchResult
from api.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    username: str = Depends(get_current_user_token)
):
    """
    Search documents with semantic similarity.
    
    Args:
        request: Search request with query and filters
        username: Current authenticated user
        
    Returns:
        Search results
    """
    try:
        # Initialize RAG service
        rag_service = RAGService()
        
        # Add user context to filters
        filters = request.filters or {}
        filters["username"] = username
        
        # Perform search
        results = await rag_service.search(
            query=request.query,
            filters=filters,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        logger.info(f"Search performed for user {username}: '{request.query[:50]}...'")
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            username=username
        )
        
    except Exception as e:
        logger.error(f"Search error for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing search"
        )


@router.post("/advanced")
async def advanced_search(
    query: str = Field(..., description="Search query"),
    filters: Optional[Dict[str, Any]] = Field(None, description="Advanced filters"),
    limit: int = Field(10, description="Maximum results"),
    include_content: bool = Field(False, description="Include full content"),
    username: str = Depends(get_current_user_token)
):
    """
    Advanced search with more options.
    
    Args:
        query: Search query
        filters: Advanced filters
        limit: Maximum results
        include_content: Include full document content
        username: Current authenticated user
        
    Returns:
        Advanced search results
    """
    try:
        rag_service = RAGService()
        
        # Add user context
        search_filters = filters or {}
        search_filters["username"] = username
        
        results = await rag_service.advanced_search(
            query=query,
            filters=search_filters,
            limit=limit,
            include_content=include_content
        )
        
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "filters": search_filters,
            "username": username
        }
        
    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing advanced search"
        )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Field(..., description="Partial query for suggestions"),
    username: str = Depends(get_current_user_token)
):
    """
    Get search suggestions based on partial query.
    
    Args:
        q: Partial query
        username: Current authenticated user
        
    Returns:
        Search suggestions
    """
    try:
        rag_service = RAGService()
        suggestions = await rag_service.get_search_suggestions(q, username)
        
        return {
            "query": q,
            "suggestions": suggestions,
            "username": username
        }
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting search suggestions"
        )


@router.get("/history")
async def get_search_history(
    username: str = Depends(get_current_user_token),
    limit: int = 10
):
    """
    Get user's search history.
    
    Args:
        username: Current authenticated user
        limit: Maximum history items
        
    Returns:
        Search history
    """
    try:
        rag_service = RAGService()
        history = await rag_service.get_search_history(username, limit)
        
        return {
            "history": history,
            "username": username,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Search history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving search history"
        )
