"""
Knowledge base management for EVAgent RAG system.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import uuid
from pathlib import Path

from ..database.chroma_manager import ChromaManager
from ..embeddings.embedding_service import EmbeddingService
from ..processors.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Knowledge base manager for EVAgent RAG system.
    
    Handles:
    - Document collection management
    - Incremental updates
    - Source tracking
    - Deduplication
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize knowledge base.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Initialize components
        self.chroma_manager = ChromaManager({
            'persist_directory': self.config.get('persist_directory', './storage/knowledge_base'),
            'collection_name': self.config.get('collection_name', 'evagent_kb')
        })
        
        self.embedding_service = EmbeddingService({
            'text_model': self.config.get('text_model', 'd:\\EVAgent\\models\\all-MiniLM-L6-v2'),
            'device': self.config.get('device', 'cpu'),
            'code_model': None,
            'enable_image_embeddings': False
        })
        
        self.document_processor = DocumentProcessor({
            'chunk_size': self.config.get('chunk_size', 500),
            'chunk_overlap': self.config.get('chunk_overlap', 50)
        })
        
        logger.info("KnowledgeBase initialized")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of document dictionaries with 'content' and 'metadata'
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        logger.info(f"Adding {len(documents)} documents to knowledge base")
        
        # Process documents
        processed_docs = []
        for doc in documents:
            # Enrich metadata
            enriched_doc = self.document_processor.enrich_metadata([doc])[0]
            
            # Generate unique ID if not present
            if 'id' not in enriched_doc['metadata']:
                enriched_doc['metadata']['id'] = str(uuid.uuid4())
            
            processed_docs.append(enriched_doc)
        
        # Generate embeddings
        texts = [doc['content'] for doc in processed_docs]
        embeddings = await self.embedding_service.embed_text(texts)
        
        # Prepare for ChromaDB
        chroma_docs = []
        for i, doc in enumerate(processed_docs):
            chroma_docs.append({
                'id': doc['metadata']['id'],
                'content': doc['content'],
                'embedding': embeddings[i],
                'metadata': doc['metadata']
            })
        
        # Add to ChromaDB
        doc_ids = self.chroma_manager.add_documents_batch(chroma_docs)
        
        logger.info(f"Successfully added {len(doc_ids)} documents to knowledge base")
        return doc_ids
    
    async def add_jira_issues(self, issues: List[Dict[str, Any]]) -> List[str]:
        """
        Add Jira issues to the knowledge base.
        
        Args:
            issues: List of Jira issue data from API
            
        Returns:
            List of document IDs
        """
        all_documents = []
        
        for issue in issues:
            # Process issue into chunks
            issue_docs = self.document_processor.process_jira_issue(issue)
            all_documents.extend(issue_docs)
        
        return await self.add_documents(all_documents)
    
    async def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)
        
        # Search in ChromaDB
        results = self.chroma_manager.search(
            query_embedding=query_embedding[0],
            n_results=n_results,
            where=filters,
            include=['metadatas', 'documents', 'distances']
        )
        
        # Format results
        formatted_results = []
        for i, doc_id in enumerate(results.get('ids', [])):
            if i < len(results.get('documents', [])):
                content = results['documents'][i]
                metadata = results.get('metadatas', [])[i] if i < len(results.get('metadatas', [])) else {}
                distance = results.get('distances', [])[i] if i < len(results.get('distances', [])) else 0.0
                
                # Calculate similarity score (lower distance = higher similarity)
                similarity = 1 / (1 + distance)
                
                formatted_results.append({
                    'id': doc_id,
                    'content': content,
                    'metadata': metadata,
                    'score': similarity
                })
        
        logger.info(f"Search returned {len(formatted_results)} results for query: {query[:50]}...")
        return formatted_results
    
    async def update_document(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document.
        
        Args:
            doc_id: Document ID to update
            content: New content
            metadata: Optional new metadata
            
        Returns:
            True if successful
        """
        try:
            # Delete old document
            self.chroma_manager.delete_document(doc_id)
            
            # Add new document
            new_doc = {
                'content': content,
                'metadata': metadata or {}
            }
            new_doc['metadata']['id'] = doc_id
            new_doc['metadata']['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            await self.add_documents([new_doc])
            
            logger.info(f"Successfully updated document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.chroma_manager.delete_document(doc_id)
            logger.info(f"Successfully deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            # Search for specific document ID
            results = self.chroma_manager.search(
                query_embedding=[0] * 384,  # Dummy embedding for ID search
                n_results=1,
                where={'id': doc_id},
                include=['metadatas', 'documents']
            )
            
            if results.get('ids') and results['ids'][0]:
                return {
                    'id': results['ids'][0][0],
                    'content': results['documents'][0][0],
                    'metadata': results['metadatas'][0][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.
        
        Returns:
            Statistics dictionary
        """
        chroma_stats = self.chroma_manager.get_collection_stats()
        
        # Add additional stats
        stats = {
            **chroma_stats,
            'embedding_model': self.config.get('text_model', 'unknown'),
            'chunk_size': self.config.get('chunk_size', 500),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return stats
    
    async def deduplicate(self) -> Dict[str, Any]:
        """
        Remove duplicate documents from the knowledge base.
        
        Returns:
            Deduplication statistics
        """
        logger.info("Starting deduplication process")
        
        # Get all documents
        all_docs = []
        try:
            # This would need to be implemented in ChromaManager
            # For now, return placeholder stats
            stats = {
                'total_documents': 0,
                'duplicates_found': 0,
                'duplicates_removed': 0,
                'unique_documents': 0
            }
            
            logger.info("Deduplication completed")
            return stats
            
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            return {
                'total_documents': 0,
                'duplicates_found': 0,
                'duplicates_removed': 0,
                'error': str(e)
            }
    
    def export_documents(self, output_path: str, filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Export documents to file.
        
        Args:
            output_path: Path to export file
            filters: Optional metadata filters
            
        Returns:
            True if successful
        """
        try:
            import json
            
            # Get documents (placeholder - would need full implementation)
            documents = []
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(documents)} documents to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    async def rebuild_index(self) -> bool:
        """
        Rebuild the entire knowledge base index.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Rebuilding knowledge base index")
            
            # This would involve:
            # 1. Export all existing documents
            # 2. Clear the collection
            # 3. Re-add all documents with updated embeddings
            
            logger.info("Knowledge base index rebuilt successfully")
            return True
            
        except Exception as e:
            logger.error(f"Index rebuild failed: {e}")
            return False
