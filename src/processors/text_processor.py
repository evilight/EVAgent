"""
Text processor for cleaning and preparing text data for RAG system.
"""

import re
import html
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from markdownify import markdownify as md


class TextProcessor:
    """
    Processes and cleans text content from various sources.
    
    Handles HTML cleaning, code block extraction, and content chunking.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize text processor.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def clean_html(self, content: str, preserve_formatting: bool = True) -> str:
        """
        Clean HTML content while preserving structure.
        
        Args:
            content: HTML content to clean
            preserve_formatting: Whether to preserve basic formatting
            
        Returns:
            Cleaned text content
        """
        if not content:
            return ""
        
        try:
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            if preserve_formatting:
                # Convert to markdown to preserve structure
                cleaned = md(str(soup), heading_style="ATX")
            else:
                # Extract plain text
                cleaned = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # Decode HTML entities
            cleaned = html.unescape(cleaned)
            
            self.logger.debug(f"Cleaned HTML content: {len(content)} -> {len(cleaned)} chars")
            return cleaned
            
        except Exception as e:
            self.logger.warning(f"Failed to clean HTML content: {e}")
            # Fallback to basic cleaning
            return html.unescape(re.sub(r'<[^>]+>', ' ', content))
    
    def extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from text content.
        
        Args:
            content: Text content potentially containing code blocks
            
        Returns:
            List of dictionaries with code block information
        """
        code_blocks = []
        
        # Match markdown code blocks
        markdown_pattern = r'```(\w+)?\n(.*?)\n```'
        for match in re.finditer(markdown_pattern, content, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                'language': language,
                'code': code,
                'type': 'markdown'
            })
        
        # Match HTML code blocks
        html_pattern = r'<pre[^>]*><code[^>]*class="language-(\w+)"[^>]*>(.*?)</code></pre>'
        for match in re.finditer(html_pattern, content, re.DOTALL):
            language = match.group(1)
            code = html.unescape(match.group(2)).strip()
            code_blocks.append({
                'language': language,
                'code': code,
                'type': 'html'
            })
        
        self.logger.debug(f"Extracted {len(code_blocks)} code blocks")
        return code_blocks
    
    def remove_code_blocks(self, content: str) -> str:
        """
        Remove code blocks from content, leaving placeholder markers.
        
        Args:
            content: Text content with code blocks
            
        Returns:
            Content with code blocks replaced by placeholders
        """
        # Replace markdown code blocks
        content = re.sub(r'```(\w+)?\n.*?\n```', '[CODE_BLOCK]', content, flags=re.DOTALL)
        
        # Replace HTML code blocks
        content = re.sub(r'<pre[^>]*>.*?</pre>', '[CODE_BLOCK]', content, flags=re.DOTALL)
        
        return content
    
    def extract_links(self, content: str) -> List[Dict[str, str]]:
        """
        Extract links from text content.
        
        Args:
            content: Text content containing links
            
        Returns:
            List of dictionaries with link information
        """
        links = []
        
        # Match markdown links
        markdown_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(markdown_pattern):
            text = match.group(1)
            url = match.group(2)
            links.append({'text': text, 'url': url, 'type': 'markdown'})
        
        # Match HTML links
        soup = BeautifulSoup(content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            text = a_tag.get_text(strip=True)
            url = a_tag['href']
            links.append({'text': text, 'url': url, 'type': 'html'})
        
        self.logger.debug(f"Extracted {len(links)} links")
        return links
    
    def chunk_content(
        self,
        content: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        respect_sentences: bool = True
    ) -> List[str]:
        """
        Split content into chunks for embedding.
        
        Args:
            content: Text content to chunk
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            respect_sentences: Whether to avoid splitting sentences
            
        Returns:
            List of text chunks
        """
        if not content or len(content) <= chunk_size:
            return [content] if content else []
        
        chunks = []
        
        if respect_sentences:
            # Split by sentences first
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            current_chunk = ""
            for sentence in sentences:
                # If adding this sentence would exceed chunk size
                if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap
                    if chunk_overlap > 0:
                        # Find overlap point (preferably at sentence boundary)
                        overlap_text = current_chunk[-chunk_overlap:]
                        overlap_sentences = re.split(r'(?<=[.!?])\s+', overlap_text)
                        if len(overlap_sentences) > 1:
                            current_chunk = ' '.join(overlap_sentences[1:]) + ' ' + sentence
                        else:
                            current_chunk = sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk += sentence + ' '
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        else:
            # Simple character-based chunking
            start = 0
            while start < len(content):
                end = start + chunk_size
                if end >= len(content):
                    chunks.append(content[start:])
                    break
                
                chunks.append(content[start:end])
                start = end - chunk_overlap
        
        self.logger.debug(f"Chunked content into {len(chunks)} chunks")
        return chunks
    
    def preprocess_for_embedding(self, content: str) -> str:
        """
        Preprocess content specifically for embedding generation.
        
        Args:
            content: Raw content to preprocess
            
        Returns:
            Preprocessed content suitable for embeddings
        """
        if not content:
            return ""
        
        # Clean HTML if present
        if '<' in content and '>' in content:
            content = self.clean_html(content, preserve_formatting=True)
        
        # Extract and preserve code blocks separately
        code_blocks = self.extract_code_blocks(content)
        
        # Remove code blocks from main content but keep markers
        content_without_code = self.remove_code_blocks(content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # For embedding purposes, we might want to include code block content
        # with special markers to distinguish them
        if code_blocks:
            code_content = ' '.join([f"[CODE:{block['language']}] {block['code']}" 
                                   for block in code_blocks])
            content = f"{content_without_code} {code_content}"
        
        return content
    
    def extract_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from a data item.
        
        Args:
            item: Dictionary containing raw data from source
            
        Returns:
            Structured metadata dictionary
        """
        metadata = {}
        
        # Common fields to extract
        field_mappings = {
            'id': ['id', 'key', 'source_id'],
            'title': ['title', 'summary', 'subject'],
            'description': ['description', 'content', 'body'],
            'author': ['author', 'creator', 'reporter', 'user'],
            'created_date': ['created', 'created_date', 'date'],
            'updated_date': ['updated', 'updated_date', 'modified'],
            'project': ['project', 'space', 'repository'],
            'type': ['type', 'issue_type', 'content_type'],
            'status': ['status', 'state'],
            'priority': ['priority'],
            'labels': ['labels', 'tags'],
            'components': ['components']
        }
        
        for metadata_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                if key in item and item[key] is not None:
                    metadata[metadata_field] = item[key]
                    break
        
        # Handle nested fields (common in Jira/Confluence)
        if 'fields' in item:
            fields = item['fields']
            for metadata_field, possible_keys in field_mappings.items():
                if metadata_field not in metadata:
                    for key in possible_keys:
                        if key in fields and fields[key] is not None:
                            # Handle nested objects (like priority.name)
                            value = fields[key]
                            if isinstance(value, dict) and 'name' in value:
                                value = value['name']
                            metadata[metadata_field] = value
                            break
        
        # Extract URLs
        if 'url' in item:
            metadata['url'] = item['url']
        elif 'self' in item:
            metadata['url'] = item['self']
        
        return metadata
