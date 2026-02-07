"""
Document Loaders for Jira and Confluence data sources.

This module provides LangChain-compatible document loaders
for loading data from Jira and Confluence into the RAG system.
"""

from typing import Any, Dict, Iterator, List, Optional
import logging

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from src.connectors import JiraConnector, ConfluenceConnector
from src.utils import ConfigLoader

logger = logging.getLogger(__name__)


class JiraDocumentLoader(BaseLoader):
    """
    LangChain Document Loader for Jira issues.
    
    This loader fetches Jira issues and converts them to LangChain Document objects.
    
    Example:
        >>> loader = JiraDocumentLoader(jira_connector)
        >>> documents = loader.load()
        >>> 
        >>> # Or lazy load for memory efficiency
        >>> for doc in loader.lazy_load():
        ...     print(doc.metadata['title'])
    """
    
    def __init__(
        self,
        jira_connector: JiraConnector,
        jql_filter: Optional[str] = None,
        max_results: Optional[int] = None
    ):
        """
        Initialize the Jira document loader.
        
        Args:
            jira_connector: Configured JiraConnector instance
            jql_filter: Optional JQL query to filter issues
            max_results: Maximum number of issues to load
        """
        self.connector = jira_connector
        self.jql_filter = jql_filter or "type = Bug or type = Story or type = Task"
        self.max_results = max_results or 100
        
        logger.info(f"JiraDocumentLoader initialized with filter: {self.jql_filter}")
    
    def load(self) -> List[Document]:
        """
        Load all Jira issues as documents.
        
        Returns:
            List of Document objects
        """
        return list(self.lazy_load())
    
    def lazy_load(self) -> Iterator[Document]:
        """
        Lazily load Jira issues as documents.
        
        Yields:
            Document objects one at a time
        """
        import asyncio
        
        try:
            # Run the async search in sync context
            issues = asyncio.run(self._fetch_issues())
            
            for issue in issues:
                document = self._convert_issue_to_document(issue)
                if document:
                    yield document
                    
        except Exception as e:
            logger.error(f"Error loading Jira documents: {e}")
            raise
    
    async def _fetch_issues(self) -> List[Dict[str, Any]]:
        """
        Fetch issues from Jira.
        
        Returns:
            List of issue dictionaries
        """
        await self.connector.connect()
        
        try:
            issues = await self.connector.search_issues(
                jql=self.jql_filter,
                max_results=self.max_results
            )
            
            logger.info(f"Fetched {len(issues)} Jira issues")
            return issues
            
        finally:
            await self.connector.disconnect()
    
    def _convert_issue_to_document(self, issue: Dict[str, Any]) -> Optional[Document]:
        """
        Convert a Jira issue to a LangChain Document.
        
        Args:
            issue: Jira issue dictionary
            
        Returns:
            Document object or None if conversion fails
        """
        try:
            fields = issue.get('fields', {})
            
            # Extract content
            title = fields.get('summary', 'Untitled')
            description = self._extract_description(fields.get('description', {}))
            
            content = f"Title: {title}\n\nDescription:\n{description}"
            
            # Extract metadata
            metadata = {
                'source': 'jira',
                'source_id': issue.get('key', 'unknown'),
                'title': title,
                'type': fields.get('issuetype', {}).get('name', 'Unknown'),
                'status': fields.get('status', {}).get('name', 'Unknown'),
                'priority': fields.get('priority', {}).get('name', 'Unknown'),
                'project': fields.get('project', {}).get('name', 'Unknown'),
                'created_date': fields.get('created', ''),
                'updated_date': fields.get('updated', ''),
                'url': f"{self.connector.base_url}/browse/{issue.get('key', '')}"
            }
            
            # Add labels if present
            labels = fields.get('labels', [])
            if labels:
                metadata['labels'] = labels
            
            return Document(page_content=content, metadata=metadata)
            
        except Exception as e:
            logger.warning(f"Failed to convert issue to document: {e}")
            return None
    
    def _extract_description(self, description: Any) -> str:
        """
        Extract text from Jira description field.
        
        Args:
            description: Description field (can be string or Atlassian Document Format)
            
        Returns:
            Extracted text
        """
        if isinstance(description, str):
            return description
        
        if isinstance(description, dict):
            # Atlassian Document Format - extract text content
            return self._extract_text_from_adf(description)
        
        return str(description)
    
    def _extract_text_from_adf(self, adf: Dict[str, Any]) -> str:
        """
        Extract text from Atlassian Document Format.
        
        Args:
            adf: ADF document structure
            
        Returns:
            Extracted text
        """
        texts = []
        
        def extract_recursive(node):
            if isinstance(node, dict):
                if 'text' in node:
                    texts.append(node['text'])
                
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        extract_recursive(value)
            
            elif isinstance(node, list):
                for item in node:
                    extract_recursive(item)
        
        extract_recursive(adf)
        return ' '.join(texts)


class ConfluenceDocumentLoader(BaseLoader):
    """
    LangChain Document Loader for Confluence pages.
    
    This loader fetches Confluence pages and converts them to LangChain Document objects.
    
    Example:
        >>> loader = ConfluenceDocumentLoader(confluence_connector)
        >>> documents = loader.load()
        >>> 
        >>> # Or lazy load
        >>> for doc in loader.lazy_load():
        ...     print(doc.metadata['title'])
    """
    
    def __init__(
        self,
        confluence_connector: ConfluenceConnector,
        space_key: Optional[str] = None,
        max_results: Optional[int] = None
    ):
        """
        Initialize the Confluence document loader.
        
        Args:
            confluence_connector: Configured ConfluenceConnector instance
            space_key: Optional space key to filter pages
            max_results: Maximum number of pages to load
        """
        self.connector = confluence_connector
        self.space_key = space_key
        self.max_results = max_results or 50
        
        logger.info(f"ConfluenceDocumentLoader initialized (space: {space_key or 'all'})")
    
    def load(self) -> List[Document]:
        """
        Load all Confluence pages as documents.
        
        Returns:
            List of Document objects
        """
        return list(self.lazy_load())
    
    def lazy_load(self) -> Iterator[Document]:
        """
        Lazily load Confluence pages as documents.
        
        Yields:
            Document objects one at a time
        """
        import asyncio
        
        try:
            pages = asyncio.run(self._fetch_pages())
            
            for page in pages:
                document = self._convert_page_to_document(page)
                if document:
                    yield document
                    
        except Exception as e:
            logger.error(f"Error loading Confluence documents: {e}")
            raise
    
    async def _fetch_pages(self) -> List[Dict[str, Any]]:
        """
        Fetch pages from Confluence.
        
        Returns:
            List of page dictionaries
        """
        await self.connector.connect()
        
        try:
            # Build CQL query
            cql = "type = page"
            if self.space_key:
                cql += f" AND space = {self.space_key}"
            
            pages = await self.connector.search_pages(
                cql=cql,
                limit=self.max_results
            )
            
            logger.info(f"Fetched {len(pages)} Confluence pages")
            return pages
            
        finally:
            await self.connector.disconnect()
    
    def _convert_page_to_document(self, page: Dict[str, Any]) -> Optional[Document]:
        """
        Convert a Confluence page to a LangChain Document.
        
        Args:
            page: Confluence page dictionary
            
        Returns:
            Document object or None if conversion fails
        """
        try:
            # Extract content
            title = page.get('title', 'Untitled')
            content = self._extract_content(page.get('body', {}))
            
            full_content = f"Title: {title}\n\nContent:\n{content}"
            
            # Extract metadata
            space = page.get('space', {})
            version = page.get('version', {})
            
            metadata = {
                'source': 'confluence',
                'source_id': page.get('id', 'unknown'),
                'title': title,
                'type': 'page',
                'space': space.get('name', 'Unknown'),
                'space_key': space.get('key', ''),
                'author': version.get('by', {}).get('displayName', 'Unknown'),
                'created_date': page.get('history', {}).get('createdDate', ''),
                'version': version.get('number', 1),
                'url': page.get('_links', {}).get('webui', '')
            }
            
            # Add labels if present
            labels = page.get('metadata', {}).get('labels', {}).get('results', [])
            if labels:
                metadata['labels'] = [label.get('name') for label in labels]
            
            return Document(page_content=full_content, metadata=metadata)
            
        except Exception as e:
            logger.warning(f"Failed to convert page to document: {e}")
            return None
    
    def _extract_content(self, body: Dict[str, Any]) -> str:
        """
        Extract text content from Confluence page body.
        
        Args:
            body: Page body structure
            
        Returns:
            Extracted text content
        """
        # Try to get storage format (HTML) or view format
        storage = body.get('storage', {})
        view = body.get('view', {})
        
        content = storage.get('value', '') or view.get('value', '')
        
        # Basic HTML tag removal (could be improved with BeautifulSoup)
        import re
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
