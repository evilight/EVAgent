"""
Search API for external access to RAG system functionality.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..embeddings.embedding_service import EmbeddingService
from ..database.chroma_manager import ChromaManager
from ..database.schema import SearchQuerySchema, SearchResultSchema


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query text")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    limit: int = Field(10, description="Maximum number of results")
    include_attachments: bool = Field(False, description="Include attachment results")
    similarity_threshold: float = Field(0.7, description="Minimum similarity threshold")


class BugSearchRequest(BaseModel):
    """Bug search request model."""
    error_message: str = Field(..., description="Error message to search for")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    limit: int = Field(10, description="Maximum number of results")


class HybridSearchRequest(BaseModel):
    """Hybrid search request model."""
    query: str = Field(..., description="Search query")
    keyword_filters: Optional[List[str]] = Field(None, description="Required keywords")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    limit: int = Field(10, description="Maximum number of results")
    semantic_weight: float = Field(0.7, description="Weight for semantic similarity")


class SearchAPI:
    """
    FastAPI-based search API for the RAG system.
    
    Provides REST endpoints for semantic search, bug finding, and document retrieval.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_manager: ChromaManager,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Search API.
        
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
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="EVAgent RAG Search API",
            description="Semantic search API for bug finding and document retrieval",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "EVAgent RAG Search API",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Check database connection
                db_stats = self.chroma_manager.get_collection_stats()
                embedding_info = self.embedding_service.get_embedding_info()
                
                return {
                    "status": "healthy",
                    "database": "connected" if db_stats else "disconnected",
                    "embeddings": "loaded" if embedding_info else "not_loaded",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
        
        @self.app.post("/search")
        async def semantic_search(request: SearchRequest):
            """Perform semantic search."""
            try:
                from .query_interface import RAGQueryInterface
                
                # Create query interface
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                # Perform search
                results = await query_interface.semantic_search(
                    query=request.query,
                    filters=request.filters,
                    limit=request.limit,
                    include_attachments=request.include_attachments,
                    similarity_threshold=request.similarity_threshold
                )
                
                return results
                
            except Exception as e:
                self.logger.error(f"Semantic search failed: {e}")
                raise HTTPException(status_code=500, detail=f"Search failed: {e}")
        
        @self.app.post("/search/bugs")
        async def find_similar_bugs(request: BugSearchRequest):
            """Find similar bugs."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                results = await query_interface.find_similar_bugs(
                    error_message=request.error_message,
                    stack_trace=request.stack_trace,
                    context=request.context,
                    limit=request.limit
                )
                
                return results
                
            except Exception as e:
                self.logger.error(f"Bug search failed: {e}")
                raise HTTPException(status_code=500, detail=f"Bug search failed: {e}")
        
        @self.app.post("/search/hybrid")
        async def hybrid_search(request: HybridSearchRequest):
            """Perform hybrid search."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                results = await query_interface.hybrid_search(
                    query=request.query,
                    keyword_filters=request.keyword_filters,
                    metadata_filters=request.metadata_filters,
                    limit=request.limit,
                    semantic_weight=request.semantic_weight
                )
                
                return results
                
            except Exception as e:
                self.logger.error(f"Hybrid search failed: {e}")
                raise HTTPException(status_code=500, detail=f"Hybrid search failed: {e}")
        
        @self.app.get("/search/metadata")
        async def search_by_metadata(
            project: Optional[str] = Query(None),
            status: Optional[str] = Query(None),
            type: Optional[str] = Query(None),
            priority: Optional[str] = Query(None),
            limit: int = Query(10)
        ):
            """Search by metadata filters."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                # Build filters from query parameters
                filters = {}
                if project:
                    filters['project'] = project
                if status:
                    filters['status'] = status
                if type:
                    filters['type'] = type
                if priority:
                    filters['priority'] = priority
                
                results = await query_interface.search_by_metadata(**filters)
                
                return results
                
            except Exception as e:
                self.logger.error(f"Metadata search failed: {e}")
                raise HTTPException(status_code=500, detail=f"Metadata search failed: {e}")
        
        @self.app.get("/documents/{document_id}")
        async def get_document(document_id: str):
            """Get document by ID."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                document = await query_interface.get_document_by_id(document_id)
                
                if not document:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                return document
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get document {document_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {e}")
        
        @self.app.get("/documents/{document_id}/attachments")
        async def get_attachments(
            document_id: str,
            file_type: Optional[str] = Query(None),
            limit: int = Query(20)
        ):
            """Get attachments for a document."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                attachments = await query_interface.get_attachments(
                    content_id=document_id,
                    file_type=file_type,
                    limit=limit
                )
                
                return {
                    "document_id": document_id,
                    "attachments": attachments,
                    "total": len(attachments)
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get attachments for {document_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve attachments: {e}")
        
        @self.app.get("/stats")
        async def get_system_stats():
            """Get system statistics."""
            try:
                from .query_interface import RAGQueryInterface
                
                query_interface = RAGQueryInterface(
                    embedding_service=self.embedding_service,
                    chroma_manager=self.chroma_manager,
                    config=self.config,
                    logger=self.logger
                )
                
                stats = await query_interface.get_system_stats()
                return stats
                
            except Exception as e:
                self.logger.error(f"Failed to get system stats: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {e}")
        
        @self.app.get("/collections")
        async def list_collections():
            """List all collections."""
            try:
                collections = self.chroma_manager.list_collections()
                return {
                    "collections": collections,
                    "total": len(collections)
                }
                
            except Exception as e:
                self.logger.error(f"Failed to list collections: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list collections: {e}")
        
        @self.app.get("/embeddings/info")
        async def get_embedding_info():
            """Get embedding service information."""
            try:
                info = self.embedding_service.get_embedding_info()
                return info
                
            except Exception as e:
                self.logger.error(f"Failed to get embedding info: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve embedding info: {e}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Run the API server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        
        self.logger.info(f"Starting Search API server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
    
    def get_app(self):
        """
        Get the FastAPI app instance.
        
        Returns:
            FastAPI app instance
        """
        return self.app
