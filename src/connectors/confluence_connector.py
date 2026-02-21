"""
Confluence connector for fetching pages, content, and attachments.
"""

import os
import sys
import asyncio
import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urljoin, quote

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_connector import BaseConnector
from utils.rate_limiter import RateLimiter


class ConfluenceConnector(BaseConnector):
    """
    Connector for Confluence API to fetch pages, content, and attachments.
    
    Supports Confluence Cloud and Server with proper authentication and rate limiting.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize Confluence connector.
        
        Args:
            config: Confluence configuration dictionary
            logger: Logger instance (optional)
        """
        super().__init__(config, logger)
        self.base_url = config['url'].rstrip('/')
        self.username = config['username']
        self.api_token = config['api_token']
        self.api_version = config.get('api', {}).get('version', '2')
        
        # Use standard rate limiter for Confluence
        self.rate_limiter = RateLimiter(max_requests=1000, time_window=3600)  # 1000/hour
        
        # Authentication header
        auth_string = f"{self.username}:{self.api_token}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default HTTP headers for Confluence API requests.
        
        Returns:
            Dictionary of default headers
        """
        return {
            'Authorization': f'Basic {self.auth_header}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'EVAgent-RAG/1.0'
        }
    
    async def _test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Confluence API.
        
        Returns:
            Dictionary with connection status and message
        """
        # Use /rest/api/content without version (confirmed working)
        url = f"{self.base_url}/rest/api/content"
        
        # Make a direct request without using _make_request to avoid circular dependency
        try:
            headers = self._get_default_headers()
            params = {'limit': 1}
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    self.logger.info("Confluence connection test successful")
                    try:
                        content_data = await response.json()
                        return {
                            "status": "success",
                            "message": "Connected to Confluence successfully",
                            "content": content_data
                        }
                    except Exception as json_error:
                        return {
                            "status": "success",
                            "message": "Connected to Confluence successfully",
                            "content": None
                        }
                else:
                    error_text = await response.text()
                    raise Exception(f"Connection test failed with status {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"Confluence connection test failed: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Public method to test connection.
        
        Returns:
            Dictionary with connection status and message
        """
        try:
            return await self._test_connection()
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 50,
        start: int = 0,
        expand: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search pages using Confluence search API.
        
        Args:
            query: Search query string (CQL)
            space_key: Optional space key to limit search
            limit: Maximum number of results
            start: Starting index for pagination
            expand: List of fields to expand
            
        Returns:
            Dictionary containing search results
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/search"
        
        params = {
            'cql': query,
            'limit': limit,
            'start': start
        }
        
        if space_key:
            params['cql'] = f"space.key = {space_key} AND {query}"
        
        if expand:
            params['expand'] = ','.join(expand)
        
        self.logger.info(f"Searching Confluence pages with CQL: {query}")
        return await self._make_request('GET', url, params=params)
    
    async def get_page_content(self, page_id: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get detailed content of a specific page.
        
        Args:
            page_id: Page ID
            expand: List of fields to expand (e.g., ['body.storage', 'version', 'history'])
            
        Returns:
            Page content dictionary
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/content/{page_id}"
        
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        self.logger.debug(f"Getting page content for {page_id}")
        return await self._make_request('GET', url, params=params)
    
    async def get_child_pages(self, page_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get child pages of a specific page.
        
        Args:
            page_id: Parent page ID
            limit: Maximum number of child pages
            
        Returns:
            List of child page dictionaries
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/content/{page_id}/child/page"
        
        params = {'limit': limit}
        
        self.logger.debug(f"Getting child pages for {page_id}")
        response = await self._make_request('GET', url, params=params)
        return response.get('results', [])
    
    async def get_page_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get all attachments for a page.
        
        Args:
            page_id: Page ID
            
        Returns:
            List of attachment dictionaries
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/content/{page_id}/child/attachment"
        
        params = {
            'expand': 'version',
            'limit': 100
        }
        
        self.logger.debug(f"Getting attachments for page {page_id}")
        response = await self._make_request('GET', url, params=params)
        return response.get('results', [])
    
    async def get_attachment_content(self, attachment_id: str, file_name: str) -> bytes:
        """
        Download attachment content.
        
        Args:
            attachment_id: Attachment ID
            file_name: Original file name
            
        Returns:
            Attachment content as bytes
        """
        # Use download endpoint
        url = f"{self.base_url}/download/attachments/{attachment_id}/{quote(file_name)}"
        
        # Use a separate session without JSON content type for binary downloads
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'User-Agent': 'EVAgent-RAG/1.0'
        }
        
        await self.rate_limiter.acquire('confluence')
        
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"Failed to download attachment: {response.status}")
    
    async def get_space_pages(
        self,
        space_key: str,
        limit: int = 100,
        status: str = 'current'
    ) -> List[Dict[str, Any]]:
        """
        Get all pages in a space.
        
        Args:
            space_key: Space key
            limit: Maximum number of pages
            status: Page status (current, archived, trashed)
            
        Returns:
            List of page dictionaries
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/content"
        
        params = {
            'spaceKey': space_key,
            'type': 'page',
            'status': status,
            'limit': limit,
            'expand': 'history'
        }
        
        self.logger.debug(f"Getting pages for space {space_key}")
        response = await self._make_request('GET', url, params=params)
        return response.get('results', [])
    
    async def get_updated_pages(
        self,
        since: datetime,
        spaces: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get pages updated since a specific timestamp.
        
        Args:
            since: DateTime to fetch updates since
            spaces: List of space keys to filter by
            limit: Maximum number of pages
            
        Returns:
            List of updated pages
        """
        # Build CQL query
        cql_parts = [f"modified >= '{since.strftime('%Y-%m-%d %H:%M')}'"]
        
        if spaces:
            space_filter = " OR ".join([f"space.key = {space}" for space in spaces])
            cql_parts.append(f"({space_filter})")
        
        cql = " AND ".join(cql_parts)
        
        # Search for updated pages
        response = await self.search_pages(
            query=cql,
            limit=limit,
            expand=['history', 'version']
        )
        
        pages = response.get('results', [])
        self.logger.info(f"Found {len(pages)} pages updated since {since}")
        return pages
    
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from Confluence based on configuration.
        
        Args:
            **kwargs: Additional parameters (spaces, page_filters, etc.)
            
        Returns:
            List of pages with attachments and content
        """
        spaces = kwargs.get('spaces', self.config.get('spaces', []))
        page_filters = kwargs.get('page_filters', self.config.get('page_filters', []))
        
        all_pages = []
        
        for space in spaces:
            self.logger.info(f"Fetching pages from space: {space}")
            
            # Get pages in space
            pages = await self.get_space_pages(space_key=space, limit=1000)
            
            # Apply page filters if specified
            for page_filter in page_filters:
                # This is a simplified approach - in practice, you might want to use CQL
                filtered_pages = [p for p in pages if self._matches_filter(p, page_filter)]
                pages = filtered_pages
            
            # Enrich pages with content and attachments
            for page in pages:
                page_id = page['id']
                
                try:
                    # Get full page content
                    full_page = await self.get_page_content(
                        page_id=page_id,
                        expand=['body.storage', 'history', 'version']
                    )
                    
                    # Get attachments
                    attachments = await self.get_page_attachments(page_id)
                    full_page['attachments'] = attachments
                    
                    # Get child pages if needed
                    if self.config.get('include_child_pages', False):
                        child_pages = await self.get_child_pages(page_id, limit=50)
                        full_page['child_pages'] = child_pages
                    
                    all_pages.append(full_page)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to enrich page {page_id}: {e}")
                    # Add basic page info even if enrichment failed
                    all_pages.append(page)
        
        self.logger.info(f"Fetched {len(all_pages)} pages from Confluence")
        return all_pages
    
    def _matches_filter(self, page: Dict[str, Any], filter_condition: str) -> bool:
        """
        Check if a page matches a filter condition.
        
        Args:
            page: Page dictionary from Confluence API
            filter_condition: Filter condition string
            
        Returns:
            True if page matches filter
        """
        # Simple implementation - could be enhanced for complex CQL
        if 'status' in filter_condition.lower():
            page_status = page.get('status', 'current')
            return page_status in filter_condition
        
        if 'type' in filter_condition.lower():
            page_type = page.get('type', 'page')
            return page_type in filter_condition
        
        return True  # Default to passing if filter is not recognized
    
    def extract_page_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from a Confluence page.
        
        Args:
            page: Page dictionary from Confluence API
            
        Returns:
            Structured metadata dictionary
        """
        history = page.get('history', {})
        space = page.get('space', {})
        version = page.get('version', {})
        
        return {
            'source': 'confluence',
            'source_id': page.get('id', ''),
            'title': page.get('title', ''),
            'content': self._extract_content(page),
            'type': 'page',
            'status': page.get('status', 'current'),
            'space': space.get('key', ''),
            'space_name': space.get('name', ''),
            'author': self._safe_get_nested(history, ['createdBy', 'displayName'], ''),
            'created_date': history.get('createdDate', ''),
            'updated_date': history.get('lastUpdated', {}).get('when', ''),
            'version': version.get('number', 1),
            'labels': [label.get('name', '') for label in page.get('metadata', {}).get('labels', [])],
            'attachment_count': len(page.get('attachments', [])),
            'child_page_count': len(page.get('child_pages', [])),
            'url': f"{self.base_url}/wiki/pages/viewpage.action?pageId={page.get('id', '')}"
        }
    
    def _extract_content(self, page: Dict[str, Any]) -> str:
        """
        Extract text content from page body.
        
        Args:
            page: Page dictionary
            
        Returns:
            Extracted text content
        """
        body = page.get('body', {})
        storage_content = body.get('storage', {}).get('value', '')
        
        if storage_content:
            return storage_content
        
        # Fallback to other body representations
        for body_type in ['view', 'export_view', 'styled_view']:
            content = body.get(body_type, {}).get('value', '')
            if content:
                return content
        
        return ''
    
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
