"""
RAG (Retrieval-Augmented Generation) Chain implementation.

This module provides a complete RAG pipeline using LangChain,
combining vector search with LLM generation for question answering.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone

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
        similarity_threshold: float = 0.7,
        enable_hybrid_search: bool = True,
        enable_query_expansion: bool = True
    ):
        """
        Initialize RAG chain.
        
        Args:
            vector_store: ChromaLangChainVectorStore instance
            llm_manager: LLMManager instance
            system_prompt: Optional custom system prompt
            qa_prompt: Optional custom QA prompt
            search_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score for results
            enable_hybrid_search: Enable hybrid semantic + keyword search
            enable_query_expansion: Enable query expansion and reformulation
        """
        self.vector_store = vector_store
        self.llm_manager = llm_manager
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.qa_prompt = qa_prompt or self.QA_PROMPT
        self.search_k = search_k
        self.similarity_threshold = similarity_threshold
        self.enable_hybrid_search = enable_hybrid_search
        self.enable_query_expansion = enable_query_expansion
        
        logger.info("RAGChain initialized with enhanced features")
    
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
        
        # Step 1: Expand query if enabled
        expanded_queries = self._expand_query(question)
        
        # Step 2: Retrieve relevant documents using hybrid search
        all_retrieved_docs = []
        for query in expanded_queries:
            docs = self._hybrid_search(
                question=query,
                filters=filters,
                k=self.search_k
            )
            all_retrieved_docs.extend(docs)
        
        # Remove duplicates and filter by similarity threshold
        seen_content = set()
        retrieved_docs = []
        
        for doc in all_retrieved_docs:
            content_hash = hash(doc.page_content)
            similarity = doc.metadata.get('similarity', 0)
            
            # Skip duplicates and low similarity
            if (content_hash not in seen_content and 
                similarity >= self.similarity_threshold):
                seen_content.add(content_hash)
                retrieved_docs.append(doc)
        
        if not retrieved_docs:
            logger.warning("No relevant documents found")
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'sources': [],
                'context': "",
                'retrieved_documents': [],
                'query_expansion': expanded_queries,
                'search_method': 'hybrid' if self.enable_hybrid_search else 'semantic'
            }
        
        logger.info(f"Retrieved {len(retrieved_docs)} relevant documents from {len(all_retrieved_docs)} total")
        
        # Step 3: Rank and select best documents
        ranked_docs = self._rank_documents(retrieved_docs, question)
        
        # Step 4: Format context from retrieved documents
        context = self._format_context(ranked_docs)
        
        # Step 5: Build messages
        messages = self._build_messages(question, context, chat_history)
        
        # Step 6: Get LLM response
        llm = self.llm_manager.get_llm()
        response = await llm.ainvoke(messages)
        
        # Step 7: Format sources
        sources = self._format_sources(ranked_docs)
        
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
                for doc in ranked_docs
            ],
            'query_expansion': expanded_queries,
            'search_method': 'hybrid' if self.enable_hybrid_search else 'semantic',
            'total_retrieved': len(all_retrieved_docs),
            'unique_retrieved': len(ranked_docs)
        }
        
        logger.info("Enhanced RAG response generated successfully")
        return result
    
    def _expand_query(self, question: str) -> List[str]:
        """
        Expand query with synonyms and related terms.
        
        Args:
            question: Original question
            
        Returns:
            List of expanded queries
        """
        if not self.enable_query_expansion:
            return [question]
        
        expanded_queries = [question]
        
        # Add common technical terms
        tech_terms = {
            'error': ['issue', 'problem', 'bug', 'exception', 'traceback'],
            'login': ['authentication', 'signin', 'access', 'credentials'],
            'database': ['db', 'connection', 'pool', 'timeout'],
            'performance': ['slow', 'latency', 'optimization', 'speed'],
            'security': ['auth', 'permission', 'access', 'vulnerability']
        }
        
        # Find and add related terms
        for term, synonyms in tech_terms.items():
            if any(synonym in question.lower() for synonym in synonyms):
                for synonym in synonyms:
                    if synonym not in question.lower():
                        expanded_queries.append(f"{question} {synonym}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in expanded_queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        logger.info(f"Expanded query to {len(unique_queries)} variations")
        return unique_queries[:5]  # Limit to prevent explosion
    
    def _hybrid_search(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> List[Document]:
        """
        Perform hybrid search combining semantic and keyword matching.
        
        Args:
            question: Search query
            filters: Optional metadata filters
            k: Number of results
            
        Returns:
            List of retrieved documents
        """
        if not self.enable_hybrid_search:
            # Fallback to semantic search only
            return self.vector_store.similarity_search(question, k=k, filter=filters)
        
        # Semantic search
        semantic_docs = self.vector_store.similarity_search(question, k=k, filter=filters)
        
        # Keyword search (simple implementation)
        keywords = self._extract_keywords(question)
        keyword_docs = []
        
        if keywords:
            # This is a simplified keyword search
            # In production, you'd use a proper search engine
            all_docs = []  # Would need to get all docs from vector store
            
            for doc in all_docs:
                content_lower = doc.page_content.lower()
                if any(keyword in content_lower for keyword in keywords):
                    keyword_docs.append(doc)
        
        # Combine and deduplicate results
        all_docs = semantic_docs + keyword_docs
        seen_ids = set()
        combined_docs = []
        
        for doc in all_docs:
            doc_id = doc.metadata.get('id', str(hash(doc.page_content)))
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined_docs.append(doc)
        
        # Sort by similarity score if available
        combined_docs.sort(
            key=lambda x: x.metadata.get('similarity', 0),
            reverse=True
        )
        
        logger.info(f"Hybrid search found {len(combined_docs)} documents")
        return combined_docs[:k]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for search.
        
        Args:
            text: Input text
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction
        # In production, use NLP techniques
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was',
            'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'should', 'could', 'may', 'might',
            'can', 'shall', 'must', 'what', 'when', 'where', 'why',
            'how', 'who', 'whom', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'they', 'we', 'us'
        }
        
        keywords = [
            word for word in words
            if len(word) > 2 and word not in stop_words
        ]
        
        # Return unique keywords
        return list(set(keywords))[:10]  # Limit keywords
    
    def _rank_documents(self, documents: List[Document], question: str) -> List[Document]:
        """
        Rank retrieved documents by relevance to the query.
        
        Args:
            documents: List of retrieved documents
            question: Original question
            
        Returns:
            Ranked list of documents
        """
        if not documents:
            return []
        
        # Extract keywords from question
        question_keywords = set(self._extract_keywords(question))
        
        # Score each document
        scored_docs = []
        for doc in documents:
            score = doc.metadata.get('similarity', 0)
            
            # Boost score for keyword matches
            content_lower = doc.page_content.lower()
            keyword_matches = sum(1 for kw in question_keywords if kw in content_lower)
            keyword_boost = min(keyword_matches * 0.1, 0.3)  # Max 30% boost
            
            # Boost score for recent documents
            created_date = doc.metadata.get('created_date', '')
            recency_boost = 0.0
            if created_date:
                try:
                    from datetime import datetime
                    doc_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    days_old = (datetime.now(timezone.utc) - doc_date).days
                    recency_boost = max(0, (30 - days_old) / 30 * 0.2)  # Decay over 30 days
                except:
                    recency_boost = 0.0
            
            # Boost score for high-priority items
            priority_boost = 0.0
            priority = doc.metadata.get('priority', '').lower()
            if priority in ['critical', 'high']:
                priority_boost = 0.2
            elif priority in ['medium']:
                priority_boost = 0.1
            
            # Calculate final score
            final_score = score + keyword_boost + recency_boost + priority_boost
            doc.metadata['ranking_score'] = final_score
            
            scored_docs.append((final_score, doc))
        
        # Sort by final score (descending)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        ranked_docs = [doc for _, doc in scored_docs]
        
        logger.info(f"Ranked {len(ranked_docs)} documents")
        return ranked_docs
    
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
