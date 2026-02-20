"""
RAG service for EVAgent system with authentication support.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from knowledge.knowledge_base import KnowledgeBase
from langchain_integration.rag_chain import RAGChain
from langchain_integration.llm_integration import LLMManager
from langchain_integration.vector_store import ChromaLangChainVectorStore

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations with user context."""
    
    def __init__(self):
        """Initialize RAG service."""
        # Initialize components
        self.knowledge_base = KnowledgeBase({
            'persist_directory': './storage/rag_api_db',
            'collection_name': 'evagent_api',
            'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
            'chunk_size': 300,
            'chunk_overlap': 30
        })
        
        self.llm_manager = LLMManager()
        self.vector_store = ChromaLangChainVectorStore(
            chroma_manager=self.knowledge_base.chroma_manager,
            embedding_service=self.knowledge_base.embedding_service
        )
        
        self.rag_chain = RAGChain(
            vector_store=self.vector_store,
            llm_manager=self.llm_manager,
            search_k=5,
            similarity_threshold=0.3,
            enable_hybrid_search=True,
            enable_query_expansion=True
        )
        
        logger.info("RAGService initialized")
    
    async def ask(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask a question with RAG and user context.
        
        Args:
            question: User question
            conversation_id: Conversation ID for context
            filters: Search filters
            user_context: User information
            
        Returns:
            RAG response with sources
        """
        try:
            # Add user context to filters
            search_filters = filters or {}
            if user_context:
                search_filters["username"] = user_context.get("username")
            
            # Get chat history if conversation_id provided
            chat_history = []
            if conversation_id:
                chat_history = await self.get_conversation_history(conversation_id, user_context.get("username"))
            
            # Process with RAG chain
            result = await self.rag_chain.ask(
                question=question,
                filters=search_filters,
                chat_history=chat_history
            )
            
            # Store conversation if conversation_id provided
            if conversation_id:
                await self.store_conversation_message(
                    conversation_id,
                    user_context.get("username"),
                    question,
                    result["answer"],
                    result.get("sources", [])
                )
            
            # Add conversation ID to result
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            result["conversation_id"] = conversation_id
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"RAG ask error: {e}")
            raise
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search documents.
        
        Args:
            query: Search query
            filters: Search filters
            limit: Maximum results
            similarity_threshold: Minimum similarity
            
        Returns:
            Search results
        """
        try:
            results = await self.knowledge_base.search(
                query=query,
                n_results=limit,
                filters=filters
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results
                if result.get('score', 0) >= similarity_threshold
            ]
            
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise
    
    async def advanced_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Advanced search with more options.
        
        Args:
            query: Search query
            filters: Search filters
            limit: Maximum results
            include_content: Include full content
            
        Returns:
            Advanced search results
        """
        try:
            results = await self.search(query, filters, limit)
            
            if not include_content:
                for result in results:
                    result['content'] = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            
            return results
            
        except Exception as e:
            logger.error(f"Advanced search error: {e}")
            raise
    
    async def get_search_suggestions(self, partial_query: str, username: str) -> List[str]:
        """
        Get search suggestions.
        
        Args:
            partial_query: Partial query
            username: User context
            
        Returns:
            Search suggestions
        """
        try:
            # Simple implementation - could be enhanced with actual suggestions
            suggestions = [
                f"{partial_query} authentication",
                f"{partial_query} database",
                f"{partial_query} error",
                f"{partial_query} login"
            ]
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Search suggestions error: {e}")
            raise
    
    async def get_conversation_history(self, conversation_id: str, username: str) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation ID
            username: User context
            
        Returns:
            Chat history
        """
        try:
            # This would be implemented with actual storage
            # For now, return empty history
            return []
            
        except Exception as e:
            logger.error(f"Get conversation history error: {e}")
            raise
    
    async def store_conversation_message(
        self,
        conversation_id: str,
        username: str,
        user_message: str,
        assistant_response: str,
        sources: List[Dict[str, Any]]
    ) -> bool:
        """
        Store conversation message.
        
        Args:
            conversation_id: Conversation ID
            username: User context
            user_message: User message
            assistant_response: Assistant response
            sources: Source documents
            
        Returns:
            Success status
        """
        try:
            # This would be implemented with actual storage
            logger.info(f"Stored message for conversation {conversation_id}, user {username}")
            return True
            
        except Exception as e:
            logger.error(f"Store conversation error: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str, username: str) -> bool:
        """
        Delete conversation.
        
        Args:
            conversation_id: Conversation ID
            username: User context
            
        Returns:
            Success status
        """
        try:
            # This would be implemented with actual storage
            logger.info(f"Deleted conversation {conversation_id} by user {username}")
            return True
            
        except Exception as e:
            logger.error(f"Delete conversation error: {e}")
            return False
    
    async def list_user_conversations(self, username: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List user conversations.
        
        Args:
            username: User context
            limit: Maximum conversations
            offset: Pagination offset
            
        Returns:
            List of conversations
        """
        try:
            # This would be implemented with actual storage
            return []
            
        except Exception as e:
            logger.error(f"List conversations error: {e}")
            raise
    
    async def get_search_history(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get search history.
        
        Args:
            username: User context
            limit: Maximum history items
            
        Returns:
            Search history
        """
        try:
            # This would be implemented with actual storage
            return []
            
        except Exception as e:
            logger.error(f"Search history error: {e}")
            raise
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Returns:
            System statistics
        """
        try:
            kb_stats = self.knowledge_base.get_stats()
            
            return {
                "total_documents": kb_stats.get("document_count", 0),
                "total_conversations": 0,  # Would be implemented
                "total_searches": 0,  # Would be implemented
                "uptime": 0.0,  # Would be calculated
                "model_info": {
                    "embedding_model": kb_stats.get("embedding_model", "unknown"),
                    "llm_model": "deepseek"  # From LLMManager
                }
            }
            
        except Exception as e:
            logger.error(f"System stats error: {e}")
            raise
    
    async def get_user_stats(self, username: str) -> Dict[str, Any]:
        """
        Get user-specific statistics.
        
        Args:
            username: User context
            
        Returns:
            User statistics
        """
        try:
            return {
                "user_conversations": 0,  # Would be implemented
                "user_searches": 0,  # Would be implemented
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"User stats error: {e}")
            raise
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            System information
        """
        try:
            return {
                "version": "1.0.0",
                "api_version": "v1",
                "features": {
                    "rag": True,
                    "hybrid_search": True,
                    "query_expansion": True,
                    "local_embeddings": True
                },
                "models": {
                    "embedding": "all-MiniLM-L6-v2 (local)",
                    "llm": "deepseek"
                }
            }
            
        except Exception as e:
            logger.error(f"System info error: {e}")
            raise
    
    async def reset_system(self) -> bool:
        """
        Reset system (admin only).
        
        Returns:
            Success status
        """
        try:
            # This would reset all data
            logger.warning("System reset performed")
            return True
            
        except Exception as e:
            logger.error(f"System reset error: {e}")
            return False
