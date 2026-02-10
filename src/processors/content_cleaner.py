"""
Content cleaning utilities for EVAgent RAG system.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from html import unescape
import unicodedata

logger = logging.getLogger(__name__)


class ContentCleaner:
    """
    Advanced content cleaner for various document types.
    
    Handles:
    - HTML and markdown cleaning
    - Text normalization
    - Noise removal
    - Format standardization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize content cleaner.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.preserve_code_blocks = self.config.get('preserve_code_blocks', True)
        self.preserve_tables = self.config.get('preserve_tables', False)
        self.normalize_unicode = self.config.get('normalize_unicode', True)
        
        logger.info("ContentCleaner initialized")
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content to plain text.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned plain text
        """
        if not html_content:
            return ""
        
        # Remove script and style tags with their content
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # Handle code blocks
        if self.preserve_code_blocks:
            # Preserve code blocks temporarily
            code_blocks = []
            def replace_code(match):
                code_blocks.append(match.group(0))
                return f'__CODE_BLOCK_{len(code_blocks)-1}__'
            html_content = re.sub(r'<(pre|code)[^>]*>.*?</\1>', replace_code, html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Handle tables if preserved
        if self.preserve_tables:
            # Preserve tables temporarily
            tables = []
            def replace_table(match):
                tables.append(match.group(0))
                return f'__TABLE_{len(tables)-1}__'
            html_content = re.sub(r'<table[^>]*>.*?</table>', replace_table, html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove remaining HTML tags
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Decode HTML entities
        html_content = unescape(html_content)
        
        # Restore code blocks
        if self.preserve_code_blocks:
            for i, code_block in enumerate(code_blocks):
                # Extract text from code block
                code_text = re.sub(r'<[^>]+>', '', code_block)
                html_content = html_content.replace(f'__CODE_BLOCK_{i}__', f'\n```\n{code_text.strip()}\n```\n')
        
        # Restore tables
        if self.preserve_tables:
            for i, table in enumerate(tables):
                # Simple table to text conversion
                table_text = self._table_to_text(table)
                html_content = html_content.replace(f'__TABLE_{i}__', table_text)
        
        # Clean up whitespace
        html_content = self._clean_whitespace(html_content)
        
        return html_content.strip()
    
    def clean_markdown(self, markdown_content: str) -> str:
        """
        Clean markdown content to plain text.
        
        Args:
            markdown_content: Raw markdown content
            
        Returns:
            Cleaned plain text
        """
        if not markdown_content:
            return ""
        
        # Handle code blocks
        if self.preserve_code_blocks:
            # Preserve code blocks temporarily
            code_blocks = []
            def replace_code(match):
                code_blocks.append(match.group(0))
                return f'__CODE_BLOCK_{len(code_blocks)-1}__'
            markdown_content = re.sub(r'```[\s\S]*?```', replace_code, markdown_content)
            markdown_content = re.sub(r'`[^`]+`', replace_code, markdown_content)
        
        # Remove markdown headers
        markdown_content = re.sub(r'^#+\s+', '', markdown_content, flags=re.MULTILINE)
        
        # Remove bold/italic formatting
        markdown_content = re.sub(r'\*\*(.*?)\*\*', r'\1', markdown_content)
        markdown_content = re.sub(r'\*(.*?)\*', r'\1', markdown_content)
        markdown_content = re.sub(r'__(.*?)__', r'\1', markdown_content)
        markdown_content = re.sub(r'_(.*?)_', r'\1', markdown_content)
        
        # Remove strikethrough
        markdown_content = re.sub(r'~~(.*?)~~', r'\1', markdown_content)
        
        # Handle links
        markdown_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', markdown_content)
        
        # Handle images
        markdown_content = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', markdown_content)
        
        # Handle blockquotes
        markdown_content = re.sub(r'^>\s+', '', markdown_content, flags=re.MULTILINE)
        
        # Handle lists
        markdown_content = re.sub(r'^[\s]*[-*+]\s+', '', markdown_content, flags=re.MULTILINE)
        markdown_content = re.sub(r'^[\s]*\d+\.\s+', '', markdown_content, flags=re.MULTILINE)
        
        # Handle horizontal rules
        markdown_content = re.sub(r'^[\s]*[-*_]{3,}[\s]*$', '', markdown_content, flags=re.MULTILINE)
        
        # Restore code blocks
        if self.preserve_code_blocks:
            for i, code_block in enumerate(code_blocks):
                markdown_content = markdown_content.replace(f'__CODE_BLOCK_{i}__', code_block)
        
        # Clean up whitespace
        markdown_content = self._clean_whitespace(markdown_content)
        
        return markdown_content.strip()
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text content.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Unicode normalization
        if self.normalize_unicode:
            text = unicodedata.normalize('NFKC', text)
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '--')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def remove_noise(self, text: str) -> str:
        """
        Remove noise and unwanted patterns from text.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove email addresses (optional)
        if self.config.get('remove_emails', False):
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone numbers (optional)
        if self.config.get('remove_phones', False):
            text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Remove URLs (optional)
        if self.config.get('remove_urls', False):
            text = re.sub(r'https?://[^\s]+', '[URL]', text)
            text = re.sub(r'www\.[^\s]+', '[URL]', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!?]{3,}', '!!!', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        # Remove repeated characters
        text = re.sub(r'(.)\1{3,}', r'\1\1\1', text)
        
        # Remove special characters that are likely noise
        text = re.sub(r'[^\w\s\-\.,;:!?()[\]{}"\'`@#$%&*+=<>\\/|~]', '', text)
        
        return text.strip()
    
    def extract_structure(self, content: str) -> Dict[str, Any]:
        """
        Extract structural information from content.
        
        Args:
            content: Input content
            
        Returns:
            Dictionary with structural information
        """
        structure = {
            'headings': [],
            'code_blocks': [],
            'links': [],
            'images': [],
            'tables': 0,
            'lists': 0,
            'word_count': 0,
            'char_count': len(content),
            'line_count': len(content.split('\n'))
        }
        
        # Extract headings
        structure['headings'] = re.findall(r'^#+\s+(.+)$', content, flags=re.MULTILINE)
        
        # Extract code blocks
        structure['code_blocks'] = re.findall(r'```[\s\S]*?```', content)
        
        # Extract links
        structure['links'] = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        # Extract images
        structure['images'] = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        
        # Count tables
        structure['tables'] = len(re.findall(r'<table[^>]*>.*?</table>', content, flags=re.DOTALL | re.IGNORECASE))
        
        # Count lists
        structure['lists'] = len(re.findall(r'^[\s]*[-*+]\s+', content, flags=re.MULTILINE))
        
        # Count words
        structure['word_count'] = len(re.findall(r'\b\w+\b', content))
        
        return structure
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace in text."""
        # Replace multiple newlines with single newline
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Remove leading/trailing whitespace from lines
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        
        # Remove empty lines at start/end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def _table_to_text(self, html_table: str) -> str:
        """Convert HTML table to readable text."""
        # Simple table to text conversion
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_table, flags=re.DOTALL | re.IGNORECASE)
        
        table_text = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, flags=re.DOTALL | re.IGNORECASE)
            cell_text = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
            table_text.append(' | '.join(cell_text))
        
        if table_text:
            return '\n' + '\n'.join(table_text) + '\n'
        return ''
    
    def clean_document(self, content: str, content_type: str = 'auto') -> Dict[str, Any]:
        """
        Clean document content based on type.
        
        Args:
            content: Raw document content
            content_type: Type of content ('html', 'markdown', 'text', 'auto')
            
        Returns:
            Dictionary with cleaned content and metadata
        """
        if not content:
            return {
                'cleaned_content': '',
                'original_length': 0,
                'cleaned_length': 0,
                'structure': self.extract_structure(content)
            }
        
        original_length = len(content)
        
        # Auto-detect content type if needed
        if content_type == 'auto':
            if '<' in content and '>' in content:
                content_type = 'html'
            elif '#' in content or '*' in content or '`' in content:
                content_type = 'markdown'
            else:
                content_type = 'text'
        
        # Clean based on type
        if content_type == 'html':
            cleaned = self.clean_html(content)
        elif content_type == 'markdown':
            cleaned = self.clean_markdown(content)
        else:
            cleaned = content
        
        # Normalize and remove noise
        cleaned = self.normalize_text(cleaned)
        cleaned = self.remove_noise(cleaned)
        
        # Extract structure from cleaned content
        structure = self.extract_structure(cleaned)
        
        return {
            'cleaned_content': cleaned,
            'original_length': original_length,
            'cleaned_length': len(cleaned),
            'compression_ratio': len(cleaned) / original_length if original_length > 0 else 1.0,
            'content_type': content_type,
            'structure': structure
        }
