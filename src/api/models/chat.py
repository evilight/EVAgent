"""
Pydantic models for chat API.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class SourceDocument(BaseModel):
    """Source document model."""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str = Field(..., description="RAG-generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    timestamp: Optional[datetime] = Field(None, description="Response timestamp")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context")


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    sources: Optional[List[SourceDocument]] = Field(None, description="Source documents for assistant messages")


class Conversation(BaseModel):
    """Conversation model."""
    id: str
    username: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    messages: List[ChatMessage] = Field(default_factory=list)
