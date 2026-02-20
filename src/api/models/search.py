"""
Pydantic models for search API.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    limit: int = Field(10, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, description="Minimum similarity threshold")
    include_content: bool = Field(False, description="Include full document content")


class SearchResult(BaseModel):
    """Search result model."""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str
    created_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Search response model."""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    username: str = Field(..., description="User who performed search")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class SearchSuggestion(BaseModel):
    """Search suggestion model."""
    text: str
    score: float
    type: str = Field(..., description="Suggestion type (query/document/term)")


class AdvancedSearchRequest(BaseModel):
    """Advanced search request model."""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Advanced filters")
    limit: int = Field(10, description="Maximum results")
    offset: int = Field(0, description="Results offset")
    sort_by: str = Field("score", description="Sort field")
    sort_order: str = Field("desc", description="Sort order")
    include_content: bool = Field(False, description="Include full content")
    highlight: bool = Field(False, description="Highlight search terms")
