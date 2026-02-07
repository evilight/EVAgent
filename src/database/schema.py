"""
Schema definitions for RAG system data structures.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator


class DocumentSchema(BaseModel):
    """
    Schema for document metadata in the RAG system.
    """
    
    # Core fields
    source: str = Field(..., description="Data source (jira, confluence, etc.)")
    source_id: str = Field(..., description="Original ID from source")
    title: str = Field(..., description="Document title")
    type: str = Field(..., description="Document type (issue, page, etc.)")
    
    # Content fields
    description: Optional[str] = Field(None, description="Document description or content")
    content: Optional[str] = Field(None, description="Full document content")
    
    # Classification fields
    project: Optional[str] = Field(None, description="Project or space")
    project_name: Optional[str] = Field(None, description="Project display name")
    status: Optional[str] = Field(None, description="Document status")
    priority: Optional[str] = Field(None, description="Document priority")
    
    # People fields
    author: Optional[str] = Field(None, description="Document author")
    assignee: Optional[str] = Field(None, description="Assigned person")
    reporter: Optional[str] = Field(None, description="Reporter (for issues)")
    
    # Timestamp fields
    created_date: Optional[str] = Field(None, description="Creation timestamp")
    updated_date: Optional[str] = Field(None, description="Last update timestamp")
    resolution_date: Optional[str] = Field(None, description="Resolution timestamp")
    
    # Categorization fields
    labels: List[str] = Field(default_factory=list, description="Tags or labels")
    components: List[str] = Field(default_factory=list, description="Components or categories")
    fix_versions: List[str] = Field(default_factory=list, description="Fix versions")
    affects_versions: List[str] = Field(default_factory=list, description="Affected versions")
    
    # Technical fields
    error_types: List[str] = Field(default_factory=list, description="Error types found")
    stack_traces: List[str] = Field(default_factory=list, description="Stack traces")
    file_paths: List[str] = Field(default_factory=list, description="File paths mentioned")
    class_names: List[str] = Field(default_factory=list, description="Class names mentioned")
    urls: List[str] = Field(default_factory=list, description="URLs mentioned")
    versions: List[str] = Field(default_factory=list, description="Version numbers")
    
    # Attachment fields
    attachment_count: int = Field(0, description="Number of attachments")
    comment_count: int = Field(0, description="Number of comments")
    
    # URL and reference fields
    url: Optional[str] = Field(None, description="URL to original document")
    
    # Search and ranking fields
    search_text: Optional[str] = Field(None, description="Combined text for searching")
    priority_score: float = Field(5.0, description="Priority score for ranking")
    recency_score: float = Field(5.0, description="Recency score for ranking")
    
    # System fields
    indexed_at: Optional[str] = Field(None, description="When document was indexed")
    updated_at: Optional[str] = Field(None, description="When document was last updated")
    
    # Custom fields
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom fields from source")
    
    class Config:
        extra = "allow"  # Allow additional fields
    
    @validator('created_date', 'updated_date', 'resolution_date', 'indexed_at', 'updated_at')
    def validate_timestamps(cls, v):
        """Validate timestamp fields."""
        if v is None:
            return v
        try:
            # Try to parse as ISO 8601
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except:
            raise ValueError(f"Invalid timestamp format: {v}")
    
    @validator('priority_score', 'recency_score')
    def validate_scores(cls, v):
        """Validate score fields."""
        if not 0 <= v <= 10:
            raise ValueError("Score must be between 0 and 10")
        return v
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean data according to schema.
        
        Args:
            data: Raw data dictionary
            
        Returns:
            Validated data dictionary with empty lists removed for ChromaDB compatibility
        """
        try:
            # Create model instance to validate
            validated = cls(**data)
            result = validated.dict()
            # Remove None values, empty lists and empty dicts for ChromaDB compatibility
            # ChromaDB only accepts: str, int, float, bool
            cleaned_result = {}
            for k, v in result.items():
                if v is None or v == [] or v == {}:
                    continue
                # Ensure value is a supported type
                if isinstance(v, (str, int, float, bool)):
                    cleaned_result[k] = v
                elif isinstance(v, list) and v:
                    # Convert list to comma-separated string for ChromaDB
                    cleaned_result[k] = ', '.join(str(item) for item in v)
                else:
                    cleaned_result[k] = str(v)
            return cleaned_result
        except Exception as e:
            # Log validation error but return cleaned data
            logger = logging.getLogger(cls.__name__)
            logger.warning(f"Schema validation failed: {e}")
            
            # Return cleaned data with basic validation
            cleaned = cls._clean_data(data)
            return cleaned
    
    @staticmethod
    def _clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean data to ensure basic compatibility.
        
        Args:
            data: Raw data dictionary
            
        Returns:
            Cleaned data dictionary
        """
        cleaned = {}
        
        # String fields
        string_fields = [
            'source', 'source_id', 'title', 'type', 'description', 'content',
            'project', 'project_name', 'status', 'priority', 'author',
            'assignee', 'reporter', 'created_date', 'updated_date',
            'resolution_date', 'url', 'search_text', 'indexed_at', 'updated_at'
        ]
        
        for field in string_fields:
            value = data.get(field)
            if value is not None:
                cleaned[field] = str(value)
        
        # List fields - convert to comma-separated string for ChromaDB
        list_fields = [
            'labels', 'components', 'fix_versions', 'affects_versions',
            'error_types', 'stack_traces', 'file_paths', 'class_names', 'urls', 'versions'
        ]
        
        for field in list_fields:
            value = data.get(field)
            if isinstance(value, list) and value:  # Convert non-empty list to string
                cleaned[field] = ', '.join(str(item) for item in value if item is not None)
            elif isinstance(value, str) and value:  # Already a string, keep as-is
                cleaned[field] = value
            # Skip empty values - ChromaDB doesn't accept them
        
        # Numeric fields
        numeric_fields = ['attachment_count', 'comment_count', 'priority_score', 'recency_score']
        
        for field in numeric_fields:
            value = data.get(field)
            try:
                cleaned[field] = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                cleaned[field] = 0.0
        
        # Dict fields - only include if they have actual data
        dict_fields = ['custom_fields']
        
        for field in dict_fields:
            value = data.get(field)
            if isinstance(value, dict) and value:  # Only include non-empty dicts
                cleaned[field] = value
            # Skip empty dicts - ChromaDB doesn't accept them
        
        return cleaned


class FileReferenceSchema(BaseModel):
    """
    Schema for file reference metadata.
    """
    
    # Core fields
    source: str = Field(..., description="Data source")
    source_id: str = Field(..., description="File ID from source")
    parent_id: str = Field(..., description="Parent document ID")
    parent_type: str = Field(..., description="Parent document type")
    
    # File information
    filename: str = Field(..., description="Original filename")
    title: str = Field(..., description="File title (usually same as filename)")
    type: str = Field(default="attachment", description="File type")
    mime_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    
    # Processing information
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    file_type: Optional[str] = Field(None, description="File category")
    format: Optional[str] = Field(None, description="File format")
    
    # Image-specific fields
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    mode: Optional[str] = Field(None, description="Image color mode")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence score")
    
    # Document-specific fields
    pages: Optional[int] = Field(None, description="Number of pages")
    paragraphs: Optional[List[str]] = Field(None, description="Extracted paragraphs")
    page_texts: Optional[List[Dict[str, Any]]] = Field(None, description="Page-by-page text")
    
    # Spreadsheet-specific fields
    sheets: Optional[List[Dict[str, Any]]] = Field(None, description="Sheet information")
    
    # Log-specific fields
    log_patterns: Optional[List[str]] = Field(None, description="Detected log patterns")
    
    # People and timestamps
    author: Optional[str] = Field(None, description="File author")
    created_date: Optional[str] = Field(None, description="Creation timestamp")
    
    # URL fields
    url: Optional[str] = Field(None, description="File URL")
    download_url: Optional[str] = Field(None, description="Download URL")
    
    # Inherited fields from parent
    parent_labels: Optional[List[str]] = Field(None, description="Parent document labels")
    parent_components: Optional[List[str]] = Field(None, description="Parent document components")
    parent_priority: Optional[str] = Field(None, description="Parent document priority")
    parent_status: Optional[str] = Field(None, description="Parent document status")
    
    # Project/space information
    project: Optional[str] = Field(None, description="Project name")
    space: Optional[str] = Field(None, description="Space name")
    
    # System fields
    indexed_at: Optional[str] = Field(None, description="When file was indexed")
    hash: Optional[str] = Field(None, description="File hash")
    
    # Error handling
    error: Optional[str] = Field(None, description="Processing error if any")
    ocr_error: Optional[str] = Field(None, description="OCR error if any")
    
    class Config:
        extra = "allow"  # Allow additional fields
    
    @validator('size')
    def validate_size(cls, v):
        """Validate file size."""
        if v < 0:
            raise ValueError("File size must be non-negative")
        return v
    
    @validator('width', 'height', 'pages')
    def validate_positive_int(cls, v):
        """Validate positive integer fields."""
        if v is not None and v < 0:
            raise ValueError("Value must be non-negative")
        return v
    
    @validator('ocr_confidence')
    def validate_confidence(cls, v):
        """Validate confidence score."""
        if v is not None and not 0 <= v <= 100:
            raise ValueError("Confidence must be between 0 and 100")
        return v
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean file reference data.
        
        Args:
            data: Raw data dictionary
            
        Returns:
            Validated data dictionary
        """
        try:
            # Create model instance to validate
            validated = cls(**data)
            return validated.dict()
        except Exception as e:
            # Log validation error but return cleaned data
            logger = logging.getLogger(cls.__name__)
            logger.warning(f"File schema validation failed: {e}")
            
            # Return cleaned data with basic validation
            cleaned = cls._clean_data(data)
            return cleaned
    
    @staticmethod
    def _clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean file reference data.
        
        Args:
            data: Raw data dictionary
            
        Returns:
            Cleaned data dictionary
        """
        cleaned = {}
        
        # String fields
        string_fields = [
            'source', 'source_id', 'parent_id', 'parent_type', 'filename',
            'title', 'type', 'mime_type', 'file_type', 'format', 'mode',
            'author', 'created_date', 'url', 'download_url', 'project',
            'space', 'indexed_at', 'hash', 'error', 'ocr_error',
            'parent_priority', 'parent_status'
        ]
        
        for field in string_fields:
            value = data.get(field)
            if value is not None:
                cleaned[field] = str(value)
        
        # Numeric fields
        numeric_fields = ['size', 'width', 'height', 'pages', 'ocr_confidence']
        
        for field in numeric_fields:
            value = data.get(field)
            try:
                cleaned[field] = float(value) if value is not None else None
            except (ValueError, TypeError):
                cleaned[field] = None
        
        # List fields
        list_fields = [
            'paragraphs', 'page_texts', 'sheets', 'log_patterns',
            'parent_labels', 'parent_components'
        ]
        
        for field in list_fields:
            value = data.get(field)
            if isinstance(value, list):
                cleaned[field] = value
            elif value is not None:
                cleaned[field] = [value]
            else:
                cleaned[field] = []
        
        # Text content
        if 'extracted_text' in data and data['extracted_text'] is not None:
            cleaned['extracted_text'] = str(data['extracted_text'])
        
        return cleaned


class SearchQuerySchema(BaseModel):
    """
    Schema for search queries.
    """
    
    query: str = Field(..., description="Search query text")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    limit: int = Field(10, description="Maximum number of results")
    include_attachments: bool = Field(False, description="Include attachment results")
    similarity_threshold: float = Field(0.7, description="Minimum similarity threshold")
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate result limit."""
        if v <= 0 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v
    
    @validator('similarity_threshold')
    def validate_threshold(cls, v):
        """Validate similarity threshold."""
        if not 0 <= v <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        return v


class SearchResultSchema(BaseModel):
    """
    Schema for search results.
    """
    
    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    similarity: float = Field(..., description="Similarity score")
    distance: float = Field(..., description="Distance score")
    
    # Optional file references
    files: Optional[List[Dict[str, Any]]] = Field(None, description="Associated files")
    
    @validator('similarity', 'distance')
    def validate_scores(cls, v):
        """Validate score fields."""
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v
