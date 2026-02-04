"""
Metadata extractor for extracting structured metadata from various data sources.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from urllib.parse import urlparse


class MetadataExtractor:
    """
    Extracts and enriches metadata from various data sources.
    
    Handles Jira issues, Confluence pages, and other structured data sources.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize metadata extractor.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def extract_jira_metadata(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from Jira issue.
        
        Args:
            issue: Jira issue dictionary from API
            
        Returns:
            Structured metadata dictionary
        """
        fields = issue.get('fields', {})
        
        metadata = {
            'source': 'jira',
            'source_id': issue.get('key', ''),
            'title': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'type': self._safe_get_nested(fields, ['issuetype', 'name'], ''),
            'status': self._safe_get_nested(fields, ['status', 'name'], ''),
            'priority': self._safe_get_nested(fields, ['priority', 'name'], ''),
            'project': self._safe_get_nested(fields, ['project', 'key'], ''),
            'project_name': self._safe_get_nested(fields, ['project', 'name'], ''),
            'assignee': self._safe_get_nested(fields, ['assignee', 'displayName'], ''),
            'reporter': self._safe_get_nested(fields, ['reporter', 'displayName'], ''),
            'created_date': fields.get('created', ''),
            'updated_date': fields.get('updated', ''),
            'resolution_date': fields.get('resolutiondate', ''),
            'labels': fields.get('labels', []),
            'components': [c.get('name', '') for c in fields.get('components', [])],
            'fix_versions': [v.get('name', '') for v in fields.get('fixVersions', [])],
            'affects_versions': [v.get('name', '') for v in fields.get('versions', [])],
            'environment': fields.get('environment', ''),
            'attachment_count': len(fields.get('attachment', [])),
            'comment_count': len(issue.get('comments', [])),
            'url': f"{self._extract_base_url(issue)}/browse/{issue.get('key', '')}"
        }
        
        # Extract custom fields
        custom_fields = self._extract_custom_fields(fields)
        if custom_fields:
            metadata['custom_fields'] = custom_fields
        
        # Extract technical details
        technical_metadata = self._extract_technical_metadata(issue)
        metadata.update(technical_metadata)
        
        # Add search-friendly fields
        metadata['search_text'] = self._create_search_text(metadata)
        
        return metadata
    
    def extract_confluence_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from Confluence page.
        
        Args:
            page: Confluence page dictionary from API
            
        Returns:
            Structured metadata dictionary
        """
        metadata = {
            'source': 'confluence',
            'source_id': page.get('id', ''),
            'title': page.get('title', ''),
            'content': self._safe_get_nested(page, ['body', 'storage', 'value'], ''),
            'type': 'page',
            'status': self._safe_get_nested(page, ['status', 'name'], 'current'),
            'space': self._safe_get_nested(page, ['space', 'key'], ''),
            'space_name': self._safe_get_nested(page, ['space', 'name'], ''),
            'author': self._safe_get_nested(page, ['history', 'createdBy', 'displayName'], ''),
            'created_date': self._safe_get_nested(page, ['history', 'createdDate'], ''),
            'updated_date': self._safe_get_nested(page, ['history', 'lastUpdated', 'when'], ''),
            'version': self._safe_get_nested(page, ['version', 'number'], 1),
            'labels': [label.get('name', '') for label in page.get('metadata', {}).get('labels', [])],
            'attachment_count': len(page.get('children', {}).get('attachment', {}).get('results', [])),
            'child_page_count': len(page.get('children', {}).get('page', {}).get('results', [])),
            'url': self._safe_get_nested(page, ['_links', 'base'], '') + page.get('_links', {}).get('webui', '')
        }
        
        # Extract page hierarchy
        ancestors = page.get('ancestors', [])
        if ancestors:
            metadata['parent_id'] = ancestors[-1].get('id', '')
            metadata['ancestors'] = [a.get('id', '') for a in ancestors]
        
        # Extract technical details
        technical_metadata = self._extract_technical_metadata(page)
        metadata.update(technical_metadata)
        
        # Add search-friendly fields
        metadata['search_text'] = self._create_search_text(metadata)
        
        return metadata
    
    def extract_attachment_metadata(self, attachment: Dict[str, Any], parent_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata for attachment files.
        
        Args:
            attachment: Attachment dictionary from API
            parent_metadata: Metadata of the parent (issue/page)
            
        Returns:
            Structured metadata dictionary
        """
        metadata = {
            'source': parent_metadata.get('source', ''),
            'source_id': attachment.get('id', ''),
            'parent_id': parent_metadata.get('source_id', ''),
            'parent_type': parent_metadata.get('type', ''),
            'filename': attachment.get('filename', ''),
            'title': attachment.get('filename', ''),  # Use filename as title for attachments
            'type': 'attachment',
            'mime_type': attachment.get('mimeType', ''),
            'size': attachment.get('size', 0),
            'created_date': attachment.get('created', ''),
            'author': self._safe_get_nested(attachment, ['author', 'displayName'], ''),
            'url': self._safe_get_nested(attachment, ['_links', 'content'], ''),
            'download_url': self._safe_get_nested(attachment, ['_links', 'download'], ''),
            'project': parent_metadata.get('project', ''),
            'space': parent_metadata.get('space', '')
        }
        
        # Inherit some metadata from parent
        for field in ['labels', 'components', 'priority', 'status']:
            if field in parent_metadata:
                metadata[f'parent_{field}'] = parent_metadata[field]
        
        return metadata
    
    def _extract_custom_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract custom fields from Jira issue.
        
        Args:
            fields: Fields dictionary from Jira API
            
        Returns:
            Dictionary of custom fields
        """
        custom_fields = {}
        
        # Custom fields typically have pattern like 'customfield_10010'
        for key, value in fields.items():
            if key.startswith('customfield_'):
                field_name = key
                field_value = value
                
                # Handle different custom field types
                if isinstance(field_value, dict):
                    if 'name' in field_value:
                        field_value = field_value['name']
                    elif 'value' in field_value:
                        field_value = field_value['value']
                elif isinstance(field_value, list):
                    field_value = [item.get('name', item) if isinstance(item, dict) else item 
                                 for item in field_value]
                
                custom_fields[field_name] = field_value
        
        return custom_fields
    
    def _extract_technical_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract technical metadata useful for bug analysis.
        
        Args:
            item: Data item dictionary
            
        Returns:
            Dictionary of technical metadata
        """
        technical = {}
        
        # Extract error patterns and stack traces
        text_content = self._get_all_text_content(item)
        
        # Error patterns
        error_patterns = [
            r'NullPointerException',
            r'IndexOutOfBoundsException',
            r'ArrayIndexOutOfBoundsException',
            r'ClassCastException',
            r'NumberFormatException',
            r'SQLException',
            r'IOException',
            r'TimeoutException',
            r'OutOfMemoryError',
            r'StackOverflowError'
        ]
        
        found_errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                found_errors.extend(matches)
        
        if found_errors:
            technical['error_types'] = list(set(found_errors))
        
        # Stack traces
        stack_trace_pattern = r'at\s+[\w.$]+\([^)]*\)'
        stack_traces = re.findall(stack_trace_pattern, text_content)
        if stack_traces:
            technical['stack_traces'] = stack_traces[:10]  # Limit to first 10
        
        # File paths and class names
        file_path_pattern = r'[/\\][\w/\\.-]+\.(java|py|js|cpp|c|h|cs|php|rb|go|rs|kt|scala)'
        file_paths = re.findall(file_path_pattern, text_content)
        if file_paths:
            technical['file_paths'] = list(set(file_paths))
        
        # Class names
        class_pattern = r'\b[A-Z][a-zA-Z0-9_]*\b'
        classes = re.findall(class_pattern, text_content)
        # Filter common words
        classes = [c for c in classes if len(c) > 3 and c not in ['The', 'This', 'That', 'With', 'From', 'When']]
        if classes:
            technical['class_names'] = list(set(classes[:20]))  # Limit to first 20
        
        # URLs and endpoints
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text_content)
        if urls:
            technical['urls'] = urls
        
        # Version numbers
        version_pattern = r'\d+\.\d+(\.\d+)?([.-][a-zA-Z0-9]+)?'
        versions = re.findall(version_pattern, text_content)
        if versions:
            technical['versions'] = [v[0] + v[1] if v[1] else v[0] for v in versions[:10]]
        
        return technical
    
    def _get_all_text_content(self, item: Dict[str, Any]) -> str:
        """
        Extract all text content from an item for analysis.
        
        Args:
            item: Data item dictionary
            
        Returns:
            Combined text content
        """
        text_parts = []
        
        # Common text fields
        text_fields = ['summary', 'description', 'title', 'content', 'body']
        for field in text_fields:
            if field in item and item[field]:
                text_parts.append(str(item[field]))
        
        # Check nested fields
        if 'fields' in item:
            fields = item['fields']
            for field in text_fields:
                if field in fields and fields[field]:
                    text_parts.append(str(fields[field]))
        
        # Check comments
        if 'comments' in item:
            for comment in item['comments']:
                if isinstance(comment, dict):
                    comment_text = comment.get('body', '') or comment.get('text', '')
                    if comment_text:
                        text_parts.append(str(comment_text))
        
        return ' '.join(text_parts)
    
    def _create_search_text(self, metadata: Dict[str, Any]) -> str:
        """
        Create search-friendly text from metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Combined text for searching
        """
        search_parts = []
        
        # Add key fields
        for field in ['title', 'description', 'content']:
            if field in metadata and metadata[field]:
                search_parts.append(str(metadata[field]))
        
        # Add labels and components
        for field in ['labels', 'components']:
            if field in metadata and metadata[field]:
                if isinstance(metadata[field], list):
                    search_parts.extend([str(item) for item in metadata[field]])
                else:
                    search_parts.append(str(metadata[field]))
        
        # Add technical metadata
        for field in ['error_types', 'file_paths', 'class_names']:
            if field in metadata and metadata[field]:
                if isinstance(metadata[field], list):
                    search_parts.extend([str(item) for item in metadata[field]])
        
        return ' '.join(search_parts)
    
    def _safe_get_nested(self, data: Dict[str, Any], keys: List[str], default: Any = '') -> Any:
        """
        Safely get nested dictionary value.
        
        Args:
            data: Dictionary to search
            keys: List of keys to traverse
            default: Default value if not found
            
        Returns:
            Found value or default
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def _extract_base_url(self, item: Dict[str, Any]) -> str:
        """
        Extract base URL from item for constructing full URLs.
        
        Args:
            item: Data item dictionary
            
        Returns:
            Base URL string
        """
        # Try to extract from self URL
        if 'self' in item:
            parsed = urlparse(item['self'])
            return f"{parsed.scheme}://{parsed.netloc}"
        
        # Try from other URL fields
        url_fields = ['url', 'webUrl', '_links.base']
        for field in url_fields:
            if field in item:
                url = item[field]
                if isinstance(url, str):
                    parsed = urlparse(url)
                    return f"{parsed.scheme}://{parsed.netloc}"
        
        return ''
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich metadata with additional computed fields.
        
        Args:
            metadata: Original metadata
            
        Returns:
            Enriched metadata
        """
        enriched = metadata.copy()
        
        # Add timestamps in different formats
        for date_field in ['created_date', 'updated_date', 'resolution_date']:
            if date_field in enriched and enriched[date_field]:
                try:
                    # Parse ISO 8601 date
                    dt = datetime.fromisoformat(enriched[date_field].replace('Z', '+00:00'))
                    enriched[f'{date_field}_timestamp'] = int(dt.timestamp())
                    enriched[f'{date_field}_date'] = dt.strftime('%Y-%m-%d')
                except:
                    pass
        
        # Add computed fields
        if 'created_date' in enriched and 'updated_date' in enriched:
            try:
                created = datetime.fromisoformat(enriched['created_date'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(enriched['updated_date'].replace('Z', '+00:00'))
                enriched['days_open'] = (updated - created).days
            except:
                pass
        
        # Add priority/weight for search ranking
        priority_scores = {
            'highest': 10,
            'high': 8,
            'medium': 5,
            'low': 3,
            'lowest': 1
        }
        
        priority = enriched.get('priority', '').lower()
        enriched['priority_score'] = priority_scores.get(priority, 5)
        
        # Add recency score (newer items get higher scores)
        if 'updated_date_timestamp' in enriched:
            now = datetime.now(timezone.utc).timestamp()
            age_days = (now - enriched['updated_date_timestamp']) / (24 * 3600)
            # Recency score decreases with age
            enriched['recency_score'] = max(1, 10 - (age_days / 30))  # Decay over 30 days
        
        return enriched
