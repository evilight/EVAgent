"""
ChromaDB manager for vector storage and retrieval.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Union
import numpy as np
from datetime import datetime, timezone
import json

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .schema import DocumentSchema, FileReferenceSchema


class ChromaManager:
    """
    Manager for ChromaDB vector database operations.
    
    Handles document storage, retrieval, and management for the RAG system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize ChromaDB manager.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance (optional)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required but not installed")
        
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        
        # Database configuration
        self.persist_directory = self.config.get('persist_directory', './storage/chroma_db')
        self.collection_name = self.config.get('collection_name', 'rag_documents')
        self.file_collection_name = self.config.get('file_collection_name', 'file_references')
        
        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        self.file_collection = None
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize ChromaDB client and collections."""
        try:
            # Initialize client with persistence
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # Get or create main document collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "RAG system documents"}
            )
            
            # Get or create file reference collection
            self.file_collection = self.client.get_or_create_collection(
                name=self.file_collection_name,
                metadata={"description": "File references and metadata"}
            )
            
            self.logger.info(f"ChromaDB initialized at {self.persist_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_document(
        self,
        content: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector database.
        
        Args:
            content: Document content
            embedding: Document embedding vector
            metadata: Document metadata
            document_id: Optional document ID (generated if not provided)
            
        Returns:
            Document ID
        """
        try:
            # Generate ID if not provided
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Validate and prepare metadata
            validated_metadata = DocumentSchema.validate(metadata)
            
            # Add timestamp
            validated_metadata['indexed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Convert embedding to list if needed
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            # Add to collection
            self.collection.add(
                ids=[document_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[validated_metadata]
            )
            
            self.logger.debug(f"Added document {document_id} to collection")
            return document_id
            
        except Exception as e:
            self.logger.error(f"Failed to add document: {e}")
            raise
    
    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with keys:
                      - content: Document content
                      - embedding: Document embedding
                      - metadata: Document metadata
                      - id: Optional document ID
                      
        Returns:
            List of document IDs
        """
        try:
            ids = []
            embeddings = []
            contents = []
            metadatas = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.get('id', str(uuid.uuid4()))
                ids.append(doc_id)
                
                # Prepare embedding
                embedding = doc['embedding']
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                embeddings.append(embedding)
                
                # Prepare content and metadata
                contents.append(doc['content'])
                
                validated_metadata = DocumentSchema.validate(doc['metadata'])
                validated_metadata['indexed_at'] = datetime.now(timezone.utc).isoformat()
                metadatas.append(validated_metadata)
            
            # Add batch to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas
            )
            
            self.logger.info(f"Added {len(documents)} documents to collection")
            return ids
            
        except Exception as e:
            self.logger.error(f"Failed to add documents batch: {e}")
            raise
    
    def add_file_reference(
        self,
        file_metadata: Dict[str, Any],
        file_reference_id: Optional[str] = None
    ) -> str:
        """
        Add a file reference to the file collection.
        
        Args:
            file_metadata: File metadata dictionary
            file_reference_id: Optional file reference ID
            
        Returns:
            File reference ID
        """
        try:
            # Generate ID if not provided
            if not file_reference_id:
                file_reference_id = str(uuid.uuid4())
            
            # Validate metadata
            validated_metadata = FileReferenceSchema.validate(file_metadata)
            validated_metadata['indexed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add dummy embedding (not used for file references)
            dummy_embedding = [0.0] * 384  # Standard embedding dimension
            
            # Add to file collection
            self.file_collection.add(
                ids=[file_reference_id],
                embeddings=[dummy_embedding],
                documents=[json.dumps(validated_metadata)],  # Store metadata as document
                metadatas=[validated_metadata]
            )
            
            self.logger.debug(f"Added file reference {file_reference_id}")
            return file_reference_id
            
        except Exception as e:
            self.logger.error(f"Failed to add file reference: {e}")
            raise
    
    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter conditions
            where_document: Document content filter conditions
            include: Fields to include in results
            
        Returns:
            Search results dictionary
        """
        try:
            # Convert embedding to list if needed
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.tolist()
            
            # Default include fields
            if include is None:
                include = ['metadatas', 'documents', 'distances']
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include
            )
            
            # Process results
            processed_results = {
                'ids': results['ids'][0] if results['ids'] else [],
                'distances': results['distances'][0] if results['distances'] else [],
                'metadatas': results['metadatas'][0] if results['metadatas'] else [],
                'documents': results['documents'][0] if results['documents'] else []
            }
            
            # Convert distances to similarities
            similarities = []
            for distance in processed_results['distances']:
                # ChromaDB uses cosine distance, convert to similarity
                similarity = 1 - distance
                similarities.append(similarity)
            
            processed_results['similarities'] = similarities
            
            self.logger.debug(f"Search returned {len(processed_results['ids'])} results")
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {'ids': [], 'distances': [], 'metadatas': [], 'documents': [], 'similarities': []}
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            results = self.collection.get(
                ids=[document_id],
                include=['metadatas', 'documents']
            )
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'metadata': results['metadatas'][0] if results['metadatas'] else {},
                    'content': results['documents'][0] if results['documents'] else ''
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    def get_file_reference(self, file_reference_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file reference by its ID.
        
        Args:
            file_reference_id: File reference ID
            
        Returns:
            File reference dictionary or None if not found
        """
        try:
            results = self.file_collection.get(
                ids=[file_reference_id],
                include=['metadatas', 'documents']
            )
            
            if results['ids']:
                metadata = results['metadatas'][0] if results['metadatas'] else {}
                # Parse document content if it contains JSON
                document_content = results['documents'][0] if results['documents'] else '{}'
                try:
                    additional_metadata = json.loads(document_content)
                    metadata.update(additional_metadata)
                except:
                    pass
                
                return {
                    'id': results['ids'][0],
                    'metadata': metadata
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get file reference {file_reference_id}: {e}")
            return None
    
    def get_files_by_parent(self, parent_id: str) -> List[Dict[str, Any]]:
        """
        Get all file references for a parent document.
        
        Args:
            parent_id: Parent document ID
            
        Returns:
            List of file reference dictionaries
        """
        try:
            results = self.file_collection.get(
                where={'parent_id': parent_id},
                include=['metadatas', 'documents']
            )
            
            files = []
            for i, file_id in enumerate(results['ids']):
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                document_content = results['documents'][i] if results['documents'] else '{}'
                
                try:
                    additional_metadata = json.loads(document_content)
                    metadata.update(additional_metadata)
                except:
                    pass
                
                files.append({
                    'id': file_id,
                    'metadata': metadata
                })
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get files for parent {parent_id}: {e}")
            return []
    
    def update_document(
        self,
        document_id: str,
        content: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing document.
        
        Args:
            document_id: Document ID
            content: New content (optional)
            embedding: New embedding (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {}
            
            if content is not None:
                update_data['documents'] = [content]
            
            if embedding is not None:
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                update_data['embeddings'] = [embedding]
            
            if metadata is not None:
                validated_metadata = DocumentSchema.validate(metadata)
                validated_metadata['updated_at'] = datetime.now(timezone.utc).isoformat()
                update_data['metadatas'] = [validated_metadata]
            
            if update_data:
                update_data['ids'] = [document_id]
                self.collection.update(**update_data)
                
                self.logger.debug(f"Updated document {document_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document_id}: {e}")
            return False
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the collection.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[document_id])
            
            # Also delete associated file references
            files = self.get_files_by_parent(document_id)
            for file_ref in files:
                self.file_collection.delete(ids=[file_ref['id']])
            
            self.logger.debug(f"Deleted document {document_id} and associated files")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def delete_file_reference(self, file_reference_id: str) -> bool:
        """
        Delete a file reference.
        
        Args:
            file_reference_id: File reference ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.file_collection.delete(ids=[file_reference_id])
            self.logger.debug(f"Deleted file reference {file_reference_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file reference {file_reference_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collections.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            doc_count = self.collection.count()
            file_count = self.file_collection.count()
            
            return {
                'document_count': doc_count,
                'file_count': file_count,
                'collection_name': self.collection_name,
                'file_collection_name': self.file_collection_name,
                'persist_directory': self.persist_directory
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def list_collections(self) -> List[str]:
        """
        List all collections in the database.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [collection.name for collection in collections]
            
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []
    
    def reset_database(self) -> bool:
        """
        Reset the entire database (use with caution).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.reset()
            self._initialize_database()  # Reinitialize collections
            self.logger.warning("Database reset completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            return False
