"""
RAG (Retrieval-Augmented Generation) Chain implementation.

This module provides a complete RAG pipeline using LangChain,
combining vector search with LLM generation for question answering.
"""

from typing import Any, Dict, List, Optional, Callable
import logging

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
try:
    from langchain.chains import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    # Newer versions of langchain have different imports
    create_retrieval_chain = None
    create_stuff_documents_chain = None

from .vector_store import ChromaLangChainVectorStore
from .llm_integration import LLMManager

logger = logging.getLogger(__name__)


class RAGChain:
    """
    Retrieval-Augmented Generation Chain for EVAgent.
    
    This class implements a complete RAG pipeline that:
    1. Retrieves relevant documents from the vector store
    2. Combines them with the user's question
    3. Generates an answer using an LLM
    
    Example:
        >>> from src.langchain_integration import RAGChain
        >>> 
        >>> rag = RAGChain(
        ...     vector_store=vector_store,
        ...     llm_manager=llm_manager
        ... )
        >>> 
        >>> # Ask a question
        >>> result = await rag.ask("How do I configure the Jira connector?")
        >>> print(result['answer'])
        >>> print(f"Sources: {result['sources']}")
    """
    
    # Default system prompt for the RAG chain
    DEFAULT_SYSTEM_PROMPT = """You are an intelligent assistant for the EVAgent RAG system.
You help users find information from Jira issues, Confluence pages, and other documentation.

Use the following retrieved context to answer the user's question.
If you don't know the answer based on the context, say so clearly.
Always cite your sources by referencing the document IDs or titles.

Retrieved Context:
{context}
"""
    
    # Prompt for combining retrieved documents
    QA_PROMPT = """Answer the following question based on the provided context.

Context:
{context}

Question: {input}

Provide a clear, concise answer. If the context doesn't contain enough information,
say "I don't have enough information to answer that question."

Answer:"""
    
    def __init__(
        self,
        vector_store: ChromaLangChainVectorStore,
        llm_manager: LLMManager,
        system_prompt: Optional[str] = None,
        qa_prompt: Optional[str] = None,
        search_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize the RAG chain.
        
        Args:
            vector_store: ChromaLangChainVectorStore instance
            llm_manager: LLMManager instance
            system_prompt: Optional custom system prompt
            qa_prompt: Optional custom QA prompt
            search_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score for results
        """
        self.vector_store = vector_store
        self.llm_manager = llm_manager
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.qa_prompt = qa_prompt or self.QA_PROMPT
        self.search_k = search_k
        self.similarity_threshold = similarity_threshold
        
        logger.info("RAGChain initialized")
    
    async def ask(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Ask a question and get an answer with retrieved context.
        
        Args:
            question: The user's question
            filters: Optional metadata filters for search
            chat_history: Optional list of previous messages [{'role': 'user'/'assistant', 'content': '...'}]
            
        Returns:
            Dictionary with 'answer', 'sources', 'context', and 'retrieved_documents'
        """
        logger.info(f"Processing question: {question[:50]}...")
        
        # Step 1: Retrieve relevant documents
        retrieved_docs = self.vector_store.similarity_search(
            query=question,
            k=self.search_k,
            filter=filters
        )
        
        # Filter by similarity threshold
        retrieved_docs = [
            doc for doc in retrieved_docs
            if doc.metadata.get('similarity', 0) >= self.similarity_threshold
        ]
        
        if not retrieved_docs:
            logger.warning("No relevant documents found")
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'sources': [],
                'context': "",
                'retrieved_documents': []
            }
        
        logger.info(f"Retrieved {len(retrieved_docs)} relevant documents")
        
        # Step 2: Format context from retrieved documents
        context = self._format_context(retrieved_docs)
        
        # Step 3: Build messages
        messages = self._build_messages(question, context, chat_history)
        
        # Step 4: Get LLM response
        llm = self.llm_manager.get_llm()
        response = await llm.ainvoke(messages)
        
        # Step 5: Format sources
        sources = self._format_sources(retrieved_docs)
        
        result = {
            'answer': response.content,
            'sources': sources,
            'context': context,
            'retrieved_documents': [
                {
                    'id': doc.metadata.get('id', 'unknown'),
                    'title': doc.metadata.get('title', 'Untitled'),
                    'source': doc.metadata.get('source', 'unknown'),
                    'similarity': doc.metadata.get('similarity', 0),
                    'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                for doc in retrieved_docs
            ]
        }
        
        logger.info("RAG response generated successfully")
        return result
    
    def _format_context(self, documents: List[Document]) -> str:
        """
        Format retrieved documents into context string.
        
        Args:
            documents: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', 'Unknown')
            title = doc.metadata.get('title', 'Untitled')
            content = doc.page_content
            
            context_parts.append(
                f"[Document {i}] Source: {source} | Title: {title}\n{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _build_messages(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Any]:
        """
        Build message list for LLM.
        
        Args:
            question: User question
            context: Formatted context string
            chat_history: Optional chat history
            
        Returns:
            List of messages
        """
        messages = []
        
        # System message with context
        system_content = self.system_prompt.format(context=context)
        messages.append(SystemMessage(content=system_content))
        
        # Chat history if provided
        if chat_history:
            for msg in chat_history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'user':
                    messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    messages.append(AIMessage(content=content))
        
        # Current question
        messages.append(HumanMessage(content=question))
        
        return messages
    
    def _format_sources(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Format source information from documents.
        
        Args:
            documents: List of documents
            
        Returns:
            List of source dictionaries
        """
        sources = []
        seen = set()
        
        for doc in documents:
            source_id = doc.metadata.get('source_id') or doc.metadata.get('id', 'unknown')
            
            # Avoid duplicates
            if source_id in seen:
                continue
            seen.add(source_id)
            
            sources.append({
                'id': source_id,
                'title': doc.metadata.get('title', 'Untitled'),
                'source': doc.metadata.get('source', 'unknown'),
                'type': doc.metadata.get('type', 'document'),
                'url': doc.metadata.get('url', None),
                'similarity': doc.metadata.get('similarity', 0)
            })
        
        return sources
    
    async def search_only(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform search only without LLM generation.
        
        Args:
            query: Search query
            filters: Optional metadata filters
            k: Number of results
            
        Returns:
            List of search results
        """
        documents = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filters
        )
        
        return [
            {
                'id': doc.metadata.get('id', 'unknown'),
                'title': doc.metadata.get('title', 'Untitled'),
                'source': doc.metadata.get('source', 'unknown'),
                'content': doc.page_content,
                'similarity': doc.metadata.get('similarity', 0),
                'metadata': doc.metadata
            }
            for doc in documents
        ]
    
    def update_prompts(
        self,
        system_prompt: Optional[str] = None,
        qa_prompt: Optional[str] = None
    ) -> None:
        """
        Update the prompts used by the RAG chain.
        
        Args:
            system_prompt: New system prompt
            qa_prompt: New QA prompt
        """
        if system_prompt:
            self.system_prompt = system_prompt
            logger.info("System prompt updated")
        
        if qa_prompt:
            self.qa_prompt = qa_prompt
            logger.info("QA prompt updated")
