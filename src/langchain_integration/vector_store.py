"""
LangChain-compatible VectorStore wrapper for ChromaDB.

This module provides a LangChain VectorStore interface for our ChromaManager,
enabling seamless integration with LangChain chains and retrieval systems.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Iterable
import numpy as np
import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class ChromaLangChainVectorStore(VectorStore):
    """
    LangChain-compatible VectorStore wrapper for ChromaDB.
    
    This class wraps our ChromaManager to provide a LangChain VectorStore interface,
    enabling use with LangChain retrieval chains and agents.
    
    Example:
        >>> from src.langchain_integration import ChromaLangChainVectorStore
        >>> from src.embeddings import EmbeddingService
        >>> 
        >>> # Initialize
        >>> embedding_service = EmbeddingService(config)
        >>> vector_store = ChromaLangChainVectorStore(
        ...     chroma_manager=chroma_manager,
        ...     embedding_service=embedding_service
        ... )
        >>> 
        >>> # Add documents
        >>> docs = [Document(page_content="Hello", metadata={"source": "test"})]
        >>> vector_store.add_documents(docs)
        >>> 
        >>> # Search
        >>> results = vector_store.similarity_search("hello", k=3)
    """
    
    def __init__(
        self,
        chroma_manager: ChromaManager,
        embedding_service: Any,  # EmbeddingService
        **kwargs
    ):
        """
        Initialize the vector store.
        
        Args:
            chroma_manager: ChromaManager instance
            embedding_service: EmbeddingService instance for generating embeddings
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(**kwargs)
        self.chroma_manager = chroma_manager
        self.embedding_service = embedding_service
        logger.info("ChromaLangChainVectorStore initialized")
    
    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs: Any
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: Iterable of text strings to add
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs for the texts
            **kwargs: Additional arguments
            
        Returns:
            List of IDs for the added texts
        """
        texts_list = list(texts)
        
        # Generate embeddings - handle async in sync context
        import asyncio
        import concurrent.futures
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # Use thread pool to run in a separate thread to avoid nested loop issues
            with concurrent.futures.ThreadPoolExecutor() as pool:
                coro = self.embedding_service.embed_text(texts_list)
                embeddings = pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            # No event loop running, use asyncio.run directly
            embeddings = asyncio.run(self.embedding_service.embed_text(texts_list))
        
        # Prepare documents
        documents = []
        for i, text in enumerate(texts_list):
            doc_id = ids[i] if ids else f"doc_{i}_{hash(text) % 1000000}"
            
            # Build metadata carefully to avoid empty dicts
            base_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            metadata = {
                'content': text,  # Include content in metadata for retrieval
                'source': base_metadata.get('source', 'langchain'),
                'title': base_metadata.get('title', 'Untitled'),
            }
            # Add any additional metadata fields that aren't empty
            for key, value in base_metadata.items():
                if key not in metadata and value is not None and value != {} and value != []:
                    metadata[key] = value
            
            documents.append({
                'id': doc_id,
                'content': text,
                'embedding': embeddings[i],
                'metadata': metadata
            })
        
        # Add to ChromaDB
        added_ids = self.chroma_manager.add_documents_batch(documents)
        logger.info(f"Added {len(added_ids)} documents to vector store")
        
        return added_ids
    
    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None,
        **kwargs: Any
    ) -> List[str]:
        """
        Add LangChain Document objects to the vector store.
        
        Args:
            documents: List of LangChain Document objects
            ids: Optional list of IDs
            **kwargs: Additional arguments
            
        Returns:
            List of IDs for the added documents
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        return self.add_texts(texts, metadatas=metadatas, ids=ids, **kwargs)
    
    def delete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        """
        Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
            **kwargs: Additional arguments
            
        Returns:
            True if deletion was successful
        """
        if ids is None:
            logger.warning("No IDs provided for deletion")
            return False
        
        for doc_id in ids:
            self.chroma_manager.delete_document(doc_id)
        
        logger.info(f"Deleted {len(ids)} documents from vector store")
        return True
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[Document]:
        """
        Perform similarity search on the vector store.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional metadata filter
            **kwargs: Additional arguments
            
        Returns:
            List of Document objects
        """
        # Generate query embedding - handle async in sync context
        import asyncio
        import concurrent.futures
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # Use thread pool to run in a separate thread
            with concurrent.futures.ThreadPoolExecutor() as pool:
                coro = self.embedding_service.embed_text(query)
                query_embedding = pool.submit(asyncio.run, coro).result()[0]
        except RuntimeError:
            # No event loop running, use asyncio.run directly
            query_embedding = asyncio.run(self.embedding_service.embed_text(query))[0]
        
        # Search in ChromaDB
        results = self.chroma_manager.search(
            query_embedding=query_embedding,
            n_results=k,
            where=filter,
            include=['metadatas', 'documents', 'distances']
        )
        
        # Convert to LangChain Documents
        documents = []
        for i, doc_id in enumerate(results['ids']):
            content = results['documents'][i] if i < len(results['documents']) else ""
            metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
            similarity = results['similarities'][i] if i < len(results['similarities']) else 0.0
            
            # Add similarity to metadata
            metadata = {**metadata, 'similarity': similarity, 'id': doc_id}
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional metadata filter
            **kwargs: Additional arguments
            
        Returns:
            List of (Document, score) tuples
        """
        documents = self.similarity_search(query, k=k, filter=filter, **kwargs)
        
        # Extract scores from metadata
        results = []
        for doc in documents:
            score = doc.metadata.get('similarity', 0.0)
            results.append((doc, score))
        
        return results
    
    def similarity_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[Document]:
        """
        Search by vector embedding.
        
        Args:
            embedding: Query embedding vector
            k: Number of results to return
            filter: Optional metadata filter
            **kwargs: Additional arguments
            
        Returns:
            List of Document objects
        """
        # Convert to numpy array
        query_embedding = np.array(embedding, dtype=np.float32)
        
        # Search in ChromaDB
        results = self.chroma_manager.search(
            query_embedding=query_embedding,
            n_results=k,
            where=filter,
            include=['metadatas', 'documents', 'distances']
        )
        
        # Convert to LangChain Documents
        documents = []
        for i, doc_id in enumerate(results['ids']):
            content = results['documents'][i] if i < len(results['documents']) else ""
            metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
            similarity = results['similarities'][i] if i < len(results['similarities']) else 0.0
            
            metadata = {**metadata, 'similarity': similarity, 'id': doc_id}
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        chroma_manager: Optional[ChromaManager] = None,
        embedding_service: Optional[Any] = None,
        **kwargs: Any
    ) -> "ChromaLangChainVectorStore":
        """
        Create vector store from texts.
        
        Args:
            texts: List of text strings
            embedding: LangChain Embeddings instance (not used, kept for compatibility)
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs
            chroma_manager: ChromaManager instance
            embedding_service: EmbeddingService instance
            **kwargs: Additional arguments
            
        Returns:
            ChromaLangChainVectorStore instance
        """
        if chroma_manager is None or embedding_service is None:
            raise ValueError("chroma_manager and embedding_service are required")
        
        vector_store = cls(
            chroma_manager=chroma_manager,
            embedding_service=embedding_service,
            **kwargs
        )
        
        vector_store.add_texts(texts, metadatas=metadatas, ids=ids)
        
        return vector_store
    
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding: Embeddings,
        chroma_manager: Optional[ChromaManager] = None,
        embedding_service: Optional[Any] = None,
        **kwargs: Any
    ) -> "ChromaLangChainVectorStore":
        """
        Create vector store from LangChain documents.
        
        Args:
            documents: List of LangChain Document objects
            embedding: LangChain Embeddings instance (not used, kept for compatibility)
            chroma_manager: ChromaManager instance
            embedding_service: EmbeddingService instance
            **kwargs: Additional arguments
            
        Returns:
            ChromaLangChainVectorStore instance
        """
        if chroma_manager is None or embedding_service is None:
            raise ValueError("chroma_manager and embedding_service are required")
        
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        return cls.from_texts(
            texts=texts,
            embedding=embedding,
            metadatas=metadatas,
            chroma_manager=chroma_manager,
            embedding_service=embedding_service,
            **kwargs
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with collection statistics
        """
        return self.chroma_manager.get_collection_stats()
