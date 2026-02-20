"""
Chat router for EVAgent RAG system with authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from api.middleware.auth import get_current_user_token
from api.models.chat import ChatRequest, ChatResponse, ChatMessage
from api.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    username: str = Depends(get_current_user_token)
):
    """
    Send a chat message and get RAG response.
    
    Args:
        request: Chat request with message and context
        username: Current authenticated user
        
    Returns:
        Chat response with answer and sources
    """
    try:
        # Initialize RAG service
        rag_service = RAGService()
        
        # Add user context to the request
        user_context = {
            "username": username,
            "timestamp": request.timestamp,
            "conversation_id": request.conversation_id
        }
        
        # Process the message with RAG
        result = await rag_service.ask(
            question=request.message,
            conversation_id=request.conversation_id,
            filters=request.filters,
            user_context=user_context
        )
        
        logger.info(f"Chat message processed for user {username}")
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=result.get("conversation_id"),
            timestamp=result.get("timestamp"),
            user_context=user_context
        )
        
    except Exception as e:
        logger.error(f"Chat message error for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    username: str = Depends(get_current_user_token)
):
    """
    Get conversation history.
    
    Args:
        conversation_id: Conversation ID
        username: Current authenticated user
        
    Returns:
        Conversation history
    """
    try:
        rag_service = RAGService()
        history = await rag_service.get_conversation_history(conversation_id, username)
        
        return {
            "conversation_id": conversation_id,
            "messages": history,
            "username": username
        }
        
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    username: str = Depends(get_current_user_token)
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        username: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        rag_service = RAGService()
        await rag_service.delete_conversation(conversation_id, username)
        
        logger.info(f"Conversation {conversation_id} deleted by user {username}")
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting conversation"
        )


@router.get("/conversations")
async def list_conversations(
    username: str = Depends(get_current_user_token),
    limit: int = 10,
    offset: int = 0
):
    """
    List user's conversations.
    
    Args:
        username: Current authenticated user
        limit: Maximum number of conversations to return
        offset: Offset for pagination
        
    Returns:
        List of conversations
    """
    try:
        rag_service = RAGService()
        conversations = await rag_service.list_user_conversations(username, limit, offset)
        
        return {
            "conversations": conversations,
            "username": username,
            "total": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing conversations"
        )
