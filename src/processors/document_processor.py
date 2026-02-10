"""
Document processing utilities for EVAgent RAG system.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import base64
from io import BytesIO

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processor for different types of documents from Jira/Confluence.
    
    Handles:
    - Markdown text cleaning
    - OCR for image attachments
    - Text chunking for embedding
    - Metadata enrichment
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize document processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', 500)
        self.chunk_overlap = self.config.get('chunk_overlap', 50)
        self.tesseract_path = self.config.get('tesseract_path', None)
        
        logger.info("DocumentProcessor initialized")
    
    def clean_markdown(self, text: str) -> str:
        """
        Clean markdown text for embedding.
        
        Args:
            text: Raw markdown text
            
        Returns:
            Clean plain text
        """
        if not text:
            return ""
        
        # Remove markdown syntax
        cleaned = text
        
        # Remove headers (# ## ###)
        cleaned = re.sub(r'^#+\s+', '', cleaned, flags=re.MULTILINE)
        
        # Remove bold/italic (* ** __)
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)
        cleaned = re.sub(r'__(.*?)__', r'\1', cleaned)
        
        # Remove inline code (`code`)
        cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)
        
        # Remove code blocks (```code```)
        cleaned = re.sub(r'```[\s\S]*?```', '', cleaned, flags=re.DOTALL)
        
        # Remove links [text](url)
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
        
        # Remove images ![alt](url)
        cleaned = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', cleaned)
        
        # Remove tables
        cleaned = re.sub(r'\|.*\|', '', cleaned, flags=re.MULTILINE)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        return cleaned.strip()
    
    def extract_text_from_image(self, image_data: Union[str, bytes]) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_data: Base64 string or bytes of image
            
        Returns:
            Extracted text
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR not available - pytesseract or PIL not installed")
            return ""
        
        try:
            # Handle base64 input
            if isinstance(image_data, str):
                if image_data.startswith('data:image'):
                    # Extract base64 part
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            # Load image
            image = Image.open(BytesIO(image_bytes))
            
            # Configure tesseract path if provided
            tesseract_config = {}
            if self.tesseract_path:
                tesseract_config['config'] = f'--tesseractdata-dir "{self.tesseract_path}"'
            
            # Extract text
            text = pytesseract.image_to_string(image, **tesseract_config)
            
            # Clean OCR result
            text = text.strip()
            text = re.sub(r'\s+', ' ', text)
            
            logger.info(f"OCR extracted {len(text)} characters from image")
            return text
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks for embedding.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with each chunk
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        
        # Create chunks with overlap
        for i in range(0, text_length, self.chunk_size - self.chunk_overlap):
            chunk_text = text[i:i + self.chunk_size]
            
            if not chunk_text.strip():
                continue
            
            # Create chunk metadata
            chunk_metadata = {
                'chunk_index': len(chunks),
                'chunk_start': i,
                'chunk_end': min(i + self.chunk_size, text_length),
                'chunk_size': len(chunk_text),
                'total_chunks': (text_length // (self.chunk_size - self.chunk_overlap)) + 1
            }
            
            # Add original metadata
            if metadata:
                chunk_metadata.update(metadata)
            
            chunks.append({
                'content': chunk_text.strip(),
                'metadata': chunk_metadata
            })
        
        logger.info(f"Created {len(chunks)} chunks from {text_length} characters")
        return chunks
    
    def process_jira_issue(self, issue_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a Jira issue into document chunks.
        
        Args:
            issue_data: Jira issue data from API
            
        Returns:
            List of processed document chunks
        """
        documents = []
        
        # Process issue description
        if issue_data.get('description'):
            description = self.clean_markdown(issue_data['description'])
            desc_chunks = self.chunk_text(description, {
                'source': 'jira',
                'source_id': issue_data.get('key', 'unknown'),
                'title': issue_data.get('summary', 'Untitled'),
                'type': 'issue',
                'project': issue_data.get('project', {}).get('key', 'unknown'),
                'status': issue_data.get('status', {}).get('name', 'unknown'),
                'priority': issue_data.get('priority', {}).get('name', 'unknown'),
                'labels': [label.get('name') for label in issue_data.get('labels', [])],
                'created_date': issue_data.get('created'),
                'updated_date': issue_data.get('updated'),
                'reporter': issue_data.get('reporter', {}).get('displayName', 'unknown'),
                'assignee': issue_data.get('assignee', {}).get('displayName', None)
            })
            documents.extend(desc_chunks)
        
        # Process comments
        for comment in issue_data.get('comments', []):
            if comment.get('body'):
                comment_text = self.clean_markdown(comment['body'])
                comment_chunks = self.chunk_text(comment_text, {
                    'source': 'jira',
                    'source_id': f"{issue_data.get('key', 'unknown')}-comment-{comment.get('id', 'unknown')}",
                    'title': f"Comment on {issue_data.get('summary', 'Untitled')}",
                    'type': 'comment',
                    'project': issue_data.get('project', {}).get('key', 'unknown'),
                    'author': comment.get('author', {}).get('displayName', 'unknown'),
                    'created_date': comment.get('created'),
                    'updated_date': comment.get('updated'),
                    'parent_issue': issue_data.get('key', 'unknown')
                })
                documents.extend(comment_chunks)
        
        # Process attachments
        for attachment in issue_data.get('attachments', []):
            attachment_docs = self.process_attachment(attachment, issue_data)
            documents.extend(attachment_docs)
        
        logger.info(f"Processed Jira issue {issue_data.get('key', 'unknown')} into {len(documents)} chunks")
        return documents
    
    def process_attachment(self, attachment: Dict[str, Any], issue_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an attachment from Jira.
        
        Args:
            attachment: Attachment data from Jira API
            issue_context: Parent issue data for context
            
        Returns:
            List of document chunks
        """
        documents = []
        
        # Check if it's an image
        if attachment.get('mimeType', '').startswith('image/'):
            # For now, we'll note the image but don't process it
            # OCR would be done separately
            image_doc = {
                'content': f"[Image: {attachment.get('filename', 'unknown')}]",
                'metadata': {
                    'source': 'jira',
                    'source_id': f"{issue_context.get('key', 'unknown')}-attachment-{attachment.get('id', 'unknown')}",
                    'title': attachment.get('filename', 'Unknown Image'),
                    'type': 'attachment',
                    'content_type': 'image',
                    'mimeType': attachment.get('mimeType'),
                    'size': attachment.get('size'),
                    'created_date': attachment.get('created'),
                    'parent_issue': issue_context.get('key', 'unknown')
                }
            }
            documents.append(image_doc)
        
        # Check if it's a text/markdown file
        elif (attachment.get('mimeType', '') in ['text/markdown', 'text/plain'] or 
              attachment.get('filename', '').endswith('.md')):
            
            # Note: We would need to download and process the file content
            # For now, create a placeholder
            text_doc = {
                'content': f"[Document: {attachment.get('filename', 'unknown')}]",
                'metadata': {
                    'source': 'jira',
                    'source_id': f"{issue_context.get('key', 'unknown')}-attachment-{attachment.get('id', 'unknown')}",
                    'title': attachment.get('filename', 'Unknown Document'),
                    'type': 'attachment',
                    'content_type': 'document',
                    'mimeType': attachment.get('mimeType'),
                    'size': attachment.get('size'),
                    'created_date': attachment.get('created'),
                    'parent_issue': issue_context.get('key', 'unknown')
                }
            }
            documents.append(text_doc)
        
        return documents
    
    def enrich_metadata(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich document metadata with additional information.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List with enriched metadata
        """
        for doc in documents:
            metadata = doc.get('metadata', {})
            
            # Add processing timestamp
            from datetime import datetime, timezone
            metadata['processed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add content analysis
            content = doc.get('content', '')
            metadata['content_length'] = len(content)
            metadata['word_count'] = len(content.split())
            
            # Add classification hints
            content_lower = content.lower()
            if any(keyword in content_lower for keyword in ['error', 'exception', 'traceback']):
                metadata['error_types'] = ['technical_error']
            if any(keyword in content_lower for keyword in ['bug', 'issue', 'problem']):
                metadata['error_types'] = metadata.get('error_types', []) + ['bug_report']
            if any(keyword in content_lower for keyword in ['how to', 'tutorial', 'guide']):
                metadata['error_types'] = metadata.get('error_types', []) + ['documentation']
            
            # Update document
            doc['metadata'] = metadata
        
        return documents
