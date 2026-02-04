"""
RAG query interface for semantic search and retrieval.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
import numpy as np
from datetime import datetime, timezone

from ..embeddings.embedding_service import EmbeddingService
from ..database.chroma_manager import ChromaManager
from ..processors.text_processor import TextProcessor
from ..processors.metadata_extractor import MetadataExtractor
from .search_api import SearchAPI


class RAGQueryInterface:
    """
    Main interface for RAG system queries and search operations.
    
    Provides semantic search, metadata filtering, and result assembly.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_manager: ChromaManager,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize RAG query interface.
        
        Args:
            embedding_service: Embedding service instance
            chroma_manager: ChromaDB manager instance
            config: Configuration dictionary
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.embedding_service = embedding_service
        self.chroma_manager = chroma_manager
        self.config = config or {}
        
        # Initialize processors
        self.text_processor = TextProcessor(logger)
        self.metadata_extractor = MetadataExtractor(logger)
        
        # Search configuration
        self.default_limit = self.config.get('default_limit', 10)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        self.max_results = self.config.get('max_results', 50)
        
        # Initialize search API
        self.search_api = SearchAPI(
            embedding_service=self.embedding_service,
            chroma_manager=self.chroma_manager,
            config=self.config,
            logger=self.logger
        )
    
    async def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_attachments: bool = False,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform semantic search with optional metadata filtering.
        
        Args:
            query: Search query text
            filters: Metadata filters (e.g., project, status, priority)
            limit: Maximum number of results
            include_attachments: Whether to include attachment results
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Set defaults
            limit = limit or self.default_limit
            similarity_threshold = similarity_threshold or self.similarity_threshold
            
            self.logger.info(f"Performing semantic search: '{query[:100]}...'")
            
            # Preprocess query
            processed_query = self.text_processor.preprocess_for_embedding(query, 'mixed')
            
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(processed_query)
            if query_embedding.size == 0:
                return {'results': [], 'total': 0, 'query': query, 'error': 'Failed to generate query embedding'}
            
            # Build metadata filters
            where_filter = self._build_metadata_filters(filters) if filters else None
            
            # Perform search
            search_results = self.chroma_manager.search(
                query_embedding=query_embedding,
                n_results=min(limit, self.max_results),
                where=where_filter,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Process results
            processed_results = []
            for i, doc_id in enumerate(search_results['ids']):
                if i >= len(search_results['similarities']):
                    break
                
                similarity = search_results['similarities'][i]
                if similarity < similarity_threshold:
                    continue
                
                result = {
                    'id': doc_id,
                    'content': search_results['documents'][i] if i < len(search_results['documents']) else '',
                    'metadata': search_results['metadatas'][i] if i < len(search_results['metadatas']) else {},
                    'similarity': similarity,
                    'distance': search_results['distances'][i] if i < len(search_results['distances']) else 0.0
                }
                
                # Add file references if requested
                if include_attachments:
                    files = self.chroma_manager.get_files_by_parent(doc_id)
                    result['files'] = files
                
                processed_results.append(result)
            
            # Sort by similarity
            processed_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            self.logger.info(f"Found {len(processed_results)} results above threshold")
            
            return {
                'results': processed_results,
                'total': len(processed_results),
                'query': query,
                'filters': filters,
                'threshold': similarity_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'query': query,
                'error': str(e)
            }
    
    async def find_similar_bugs(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find similar bugs based on error message and context.
        
        Args:
            error_message: Error message to search for
            stack_trace: Optional stack trace
            context: Additional context (project, component, etc.)
            limit: Maximum number of results
            
        Returns:
            Dictionary with similar bug results
        """
        try:
            self.logger.info(f"Searching for similar bugs: {error_message[:100]}...")
            
            # Build enhanced query for bug search
            query_parts = [error_message]
            
            if stack_trace:
                # Extract key information from stack trace
                stack_lines = stack_trace.split('\n')
                # Include class names and method names from stack trace
                for line in stack_lines:
                    if 'at ' in line and '(' in line:
                        method_part = line.split('at ')[1].split('(')[0]
                        query_parts.append(method_part)
            
            if context:
                # Add context information
                if context.get('project'):
                    query_parts.append(f"project:{context['project']}")
                if context.get('component'):
                    query_parts.append(f"component:{context['component']}")
                if context.get('environment'):
                    query_parts.append(f"environment:{context['environment']}")
            
            enhanced_query = ' '.join(query_parts)
            
            # Build filters for bug-specific search
            filters = {
                'type': 'issue',  # Only search issues
                'source': 'jira'  # Only Jira issues
            }
            
            # Add context filters
            if context:
                if context.get('project'):
                    filters['project'] = context['project']
                if context.get('components'):
                    filters['components'] = {'$in': context['components']}
                if context.get('status'):
                    filters['status'] = {'$in': context['status']}
            
            # Perform search
            results = await self.semantic_search(
                query=enhanced_query,
                filters=filters,
                limit=limit,
                similarity_threshold=0.6,  # Lower threshold for bug search
                include_attachments=True
            )
            
            # Enhance results with bug-specific analysis
            for result in results['results']:
                metadata = result['metadata']
                
                # Add bug-specific scores
                bug_score = self._calculate_bug_similarity_score(
                    error_message, stack_trace, metadata
                )
                result['bug_score'] = bug_score
                
                # Extract relevant error types
                if 'error_types' in metadata:
                    result['matching_errors'] = self._find_matching_errors(
                        error_message, metadata['error_types']
                    )
            
            # Re-sort by bug score
            results['results'].sort(key=lambda x: x.get('bug_score', 0), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Bug similarity search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'error': str(e)
            }
    
    async def get_attachments(
        self,
        content_id: str,
        file_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Retrieve attachments for a specific content item.
        
        Args:
            content_id: Parent content ID
            file_type: Filter by file type (image, document, etc.)
            limit: Maximum number of results
            
        Returns:
            List of attachment metadata
        """
        try:
            files = self.chroma_manager.get_files_by_parent(content_id)
            
            # Filter by file type if specified
            if file_type:
                files = [f for f in files if f['metadata'].get('file_type') == file_type]
            
            # Limit results
            files = files[:limit]
            
            self.logger.info(f"Retrieved {len(files)} attachments for {content_id}")
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get attachments for {content_id}: {e}")
            return []
    
    async def search_by_metadata(
        self,
        **filters
    ) -> Dict[str, Any]:
        """
        Search documents using exact metadata matching.
        
        Args:
            **filters: Metadata fields to filter by
            
        Returns:
            Dictionary with search results
        """
        try:
            self.logger.info(f"Searching by metadata: {filters}")
            
            # Build metadata filters
            where_filter = self._build_metadata_filters(filters)
            
            # Use a dummy embedding for metadata-only search
            dummy_embedding = np.ones(self.embedding_service.embedding_dim)
            
            # Perform search with high limit
            search_results = self.chroma_manager.search(
                query_embedding=dummy_embedding,
                n_results=self.max_results,
                where=where_filter,
                include=['metadatas', 'documents']
            )
            
            # Process results (similarity not relevant for metadata search)
            processed_results = []
            for i, doc_id in enumerate(search_results['ids']):
                result = {
                    'id': doc_id,
                    'content': search_results['documents'][i] if i < len(search_results['documents']) else '',
                    'metadata': search_results['metadatas'][i] if i < len(search_results['metadatas']) else {},
                    'similarity': 1.0,  # Perfect match for metadata search
                    'distance': 0.0
                }
                processed_results.append(result)
            
            self.logger.info(f"Found {len(processed_results)} documents matching metadata")
            
            return {
                'results': processed_results,
                'total': len(processed_results),
                'filters': filters
            }
            
        except Exception as e:
            self.logger.error(f"Metadata search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'filters': filters,
                'error': str(e)
            }
    
    async def hybrid_search(
        self,
        query: str,
        keyword_filters: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        semantic_weight: float = 0.7
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining semantic and keyword matching.
        
        Args:
            query: Search query
            keyword_filters: List of keywords that must be present
            metadata_filters: Metadata filters
            limit: Maximum number of results
            semantic_weight: Weight for semantic similarity (0-1)
            
        Returns:
            Dictionary with hybrid search results
        """
        try:
            self.logger.info(f"Performing hybrid search: '{query[:100]}...'")
            
            # Perform semantic search
            semantic_results = await self.semantic_search(
                query=query,
                filters=metadata_filters,
                limit=limit * 2,  # Get more results for re-ranking
                similarity_threshold=0.5  # Lower threshold for hybrid search
            )
            
            # Filter by keywords if specified
            if keyword_filters:
                filtered_results = []
                for result in semantic_results['results']:
                    content = result['content'].lower()
                    metadata_text = ' '.join(str(v).lower() for v in result['metadata'].values())
                    combined_text = f"{content} {metadata_text}"
                    
                    # Check if all keywords are present
                    if all(keyword.lower() in combined_text for keyword in keyword_filters):
                        # Calculate keyword match score
                        keyword_score = sum(1 for keyword in keyword_filters 
                                          if keyword.lower() in combined_text) / len(keyword_filters)
                        
                        # Combine scores
                        semantic_score = result['similarity']
                        combined_score = (semantic_weight * semantic_score + 
                                        (1 - semantic_weight) * keyword_score)
                        
                        result['combined_score'] = combined_score
                        result['keyword_score'] = keyword_score
                        filtered_results.append(result)
                
                semantic_results['results'] = filtered_results
            
            # Re-sort by combined score or semantic score
            if keyword_filters:
                semantic_results['results'].sort(key=lambda x: x.get('combined_score', x['similarity']), reverse=True)
            else:
                semantic_results['results'].sort(key=lambda x: x['similarity'], reverse=True)
            
            # Limit final results
            semantic_results['results'] = semantic_results['results'][:limit]
            semantic_results['total'] = len(semantic_results['results'])
            
            return semantic_results
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'error': str(e)
            }
    
    def _build_metadata_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build ChromaDB metadata filters from filter dictionary.
        
        Args:
            filters: Filter dictionary
            
        Returns:
            ChromaDB-compatible filter dictionary
        """
        chroma_filters = {}
        
        for field, value in filters.items():
            if isinstance(value, list):
                # Handle list filters (e.g., multiple projects)
                chroma_filters[field] = {'$in': value}
            elif isinstance(value, dict):
                # Handle complex filters
                chroma_filters[field] = value
            else:
                # Handle simple equality filters
                chroma_filters[field] = value
        
        return chroma_filters
    
    def _calculate_bug_similarity_score(
        self,
        error_message: str,
        stack_trace: Optional[str],
        metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate bug-specific similarity score.
        
        Args:
            error_message: Target error message
            stack_trace: Target stack trace
            metadata: Document metadata
            
        Returns:
            Bug similarity score (0-1)
        """
        score = 0.0
        
        # Error type matching
        if 'error_types' in metadata:
            target_errors = set(error_message.split())
            metadata_errors = set(' '.join(metadata['error_types']).lower().split())
            error_overlap = len(target_errors & metadata_errors)
            if target_errors:
                score += (error_overlap / len(target_errors)) * 0.4
        
        # Stack trace similarity
        if stack_trace and 'stack_traces' in metadata:
            target_methods = set()
            for line in stack_trace.split('\n'):
                if 'at ' in line:
                    method = line.split('at ')[1].split('(')[0]
                    target_methods.add(method.lower())
            
            metadata_methods = set()
            for trace in metadata['stack_traces']:
                if 'at ' in trace:
                    method = trace.split('at ')[1].split('(')[0]
                    metadata_methods.add(method.lower())
            
            if target_methods:
                method_overlap = len(target_methods & metadata_methods)
                score += (method_overlap / len(target_methods)) * 0.3
        
        # File path matching
        if 'file_paths' in metadata:
            target_files = set()
            for line in (stack_trace or '').split('\n'):
                if '.' in line and ('/' in line or '\\' in line):
                    target_files.add(line.lower())
            
            metadata_files = set(f.lower() for f in metadata['file_paths'])
            if target_files:
                file_overlap = len(target_files & metadata_files)
                score += (file_overlap / len(target_files)) * 0.2
        
        # Priority and recency bonuses
        if 'priority_score' in metadata:
            score += (metadata['priority_score'] / 10) * 0.05
        
        if 'recency_score' in metadata:
            score += (metadata['recency_score'] / 10) * 0.05
        
        return min(score, 1.0)
    
    def _find_matching_errors(
        self,
        error_message: str,
        error_types: List[str]
    ) -> List[str]:
        """
        Find matching error types between query and metadata.
        
        Args:
            error_message: Target error message
            error_types: List of error types from metadata
            
        Returns:
            List of matching error types
        """
        matching = []
        error_lower = error_message.lower()
        
        for error_type in error_types:
            if error_type.lower() in error_lower:
                matching.append(error_type)
        
        return matching
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            return self.chroma_manager.get_document_by_id(document_id)
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics and information.
        
        Returns:
            Dictionary with system statistics
        """
        try:
            # Get database stats
            db_stats = self.chroma_manager.get_collection_stats()
            
            # Get embedding service info
            embedding_info = self.embedding_service.get_embedding_info()
            
            return {
                'database': db_stats,
                'embeddings': embedding_info,
                'search_config': {
                    'default_limit': self.default_limit,
                    'similarity_threshold': self.similarity_threshold,
                    'max_results': self.max_results
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            return {'error': str(e)}
