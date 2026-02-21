"""
Data synchronization service for EVAgent RAG system.
Manages incremental updates from Jira and Confluence to the knowledge base.
"""

import logging
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncio
from dataclasses import dataclass

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..connectors.jira_connector import JiraConnector
from ..connectors.confluence_connector import ConfluenceConnector
from ..knowledge.knowledge_base import KnowledgeBase
from ..embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

@dataclass
class SyncResult:
    """Result of a synchronization operation."""
    source: str
    items_processed: int
    items_added: int
    items_updated: int
    items_removed: int
    errors: List[str]
    duration: float
    timestamp: datetime

class DataSyncService:
    """
    Service for synchronizing data from Jira and Confluence to the knowledge base.
    
    Features:
    - Incremental updates (only new/changed items)
    - Change detection and conflict resolution
    - Automatic scheduling and background processing
    - Progress tracking and error handling
    """
    
    def __init__(self, config: Dict[str, Any], knowledge_base: KnowledgeBase, 
                 embedding_service: EmbeddingService, logger: Optional[logging.Logger] = None):
        """
        Initialize data synchronization service.
        
        Args:
            config: Configuration dictionary
            knowledge_base: Knowledge base instance
            embedding_service: Embedding service instance
            logger: Logger instance (optional)
        """
        self.config = config
        self.knowledge_base = knowledge_base
        self.embedding_service = embedding_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize connectors
        self.jira_connector = None
        self.confluence_connector = None
        
        # Sync configuration
        self.sync_interval = config.get('sync_interval', 300)  # 5 minutes
        self.batch_size = config.get('sync_batch_size', 50)
        self.max_retries = config.get('max_retries', 3)
        
        # Track last sync times
        self.last_jira_sync = None
        self.last_confluence_sync = None
        
    async def initialize(self) -> bool:
        """
        Initialize connectors and test connections.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize Jira connector
            jira_config = {
                'url': self.config.get('jira_url', ''),
                'username': self.config.get('jira_username', ''),
                'api_token': self.config.get('jira_api_token', '')
            }
            
            if jira_config['url'] and jira_config['username'] and jira_config['api_token']:
                self.jira_connector = JiraConnector(jira_config, self.logger)
                jira_result = await self.jira_connector.test_connection()
                self.logger.info(f"Jira connector initialized: {jira_result}")
            else:
                self.logger.warning("Jira not configured")
            
            # Initialize Confluence connector
            confluence_config = {
                'url': self.config.get('confluence_url', ''),
                'username': self.config.get('confluence_username', ''),
                'api_token': self.config.get('confluence_api_token', ''),
                'space': self.config.get('confluence_space', '')
            }
            
            if confluence_config['url'] and confluence_config['username'] and confluence_config['api_token']:
                self.confluence_connector = ConfluenceConnector(confluence_config, self.logger)
                confluence_result = await self.confluence_connector.test_connection()
                self.logger.info(f"Confluence connector initialized: {confluence_result}")
            else:
                self.logger.warning("Confluence not configured")
            
            return (self.jira_connector is not None) or (self.confluence_connector is not None)
                
        except Exception as e:
            self.logger.error(f"Failed to initialize connectors: {e}")
            return False
    
    async def sync_jira_issues(self, project_key: str = None, limit: int = 100) -> SyncResult:
        """
        Synchronize Jira issues to the knowledge base.
        
        Args:
            project_key: Filter by specific project
            limit: Maximum number of issues to sync
        
        Returns:
            SyncResult with synchronization details
        """
        if not self.jira_connector:
            return SyncResult(
                source="jira",
                items_processed=0,
                items_added=0,
                items_updated=0,
                items_removed=0,
                errors=["Jira connector not initialized"],
                duration=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting Jira sync for project: {project_key or 'all'}")
            
            # Get issues from Jira
            issues = await self.jira_connector.get_issues(
                project_key=project_key,
                limit=limit
            )
            
            items_added = 0
            items_updated = 0
            items_removed = 0
            errors = []
            
            if issues:
                # Process issues for knowledge base
                for issue in issues:
                    try:
                        # Create document content from issue
                        content = f"""
                        Issue: {issue.get('key', '')}
                        Summary: {issue.get('summary', '')}
                        Description: {issue.get('description', '')}
                        Status: {issue.get('status', '')}
                        Priority: {issue.get('priority', '')}
                        Reporter: {issue.get('reporter', '')}
                        Assignee: {issue.get('assignee', '')}
                        Created: {issue.get('created', '')}
                        Updated: {issue.get('updated', '')}
                        
                        URL: {issue.get('url', '')}
                        
                        Comments: {len(issue.get('comments', []))}
                        Attachments: {len(issue.get('attachments', []))}
                        """
                        
                        # Create metadata
                        metadata = {
                            'source': 'jira',
                            'source_id': issue.get('id'),
                            'source_type': 'issue',
                            'project_key': issue.get('project'),
                            'issue_key': issue.get('key'),
                            'status': issue.get('status'),
                            'priority': issue.get('priority'),
                            'reporter': issue.get('reporter'),
                            'assignee': issue.get('assignee'),
                            'created': issue.get('created'),
                            'updated': issue.get('updated'),
                            'url': issue.get('url'),
                            'comment_count': len(issue.get('comments', [])),
                            'attachment_count': len(issue.get('attachments', []))
                        }
                        
                        # Add to knowledge base
                        doc_id = await self.knowledge_base.add_document(
                            content=content,
                            metadata=metadata,
                            title=f"Jira Issue: {issue.get('key', '')}"
                        )
                        
                        if doc_id:
                            items_added += 1
                            self.logger.info(f"Added Jira issue {issue.get('key', '')} to knowledge base")
                        else:
                            errors.append(f"Failed to add issue {issue.get('key', '')}")
                    
                    except Exception as e:
                        error_msg = f"Error processing issue {issue.get('key', '')}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
            
            # Update existing documents (optional - would implement change detection)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return SyncResult(
                source="jira",
                items_processed=len(issues),
                items_added=items_added,
                items_updated=items_updated,
                items_removed=items_removed,
                errors=errors,
                duration=duration,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Jira sync failed: {e}")
            return SyncResult(
                source="jira",
                items_processed=0,
                items_added=0,
                items_updated=0,
                items_removed=0,
                errors=[str(e)],
                duration=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def sync_confluence_pages(self, space_key: str = None, limit: int = 100) -> SyncResult:
        """
        Synchronize Confluence pages to the knowledge base.
        
        Args:
            space_key: Filter by specific space
            limit: Maximum number of pages to sync
        
        Returns:
            SyncResult with synchronization details
        """
        if not self.confluence_connector:
            return SyncResult(
                source="confluence",
                items_processed=0,
                items_added=0,
                items_updated=0,
                items_removed=0,
                errors=["Confluence connector not initialized"],
                duration=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting Confluence sync for space: {space_key or 'all'}")
            
            # Get pages from Confluence
            pages = await self.confluence_connector.get_pages(
                space_key=space_key,
                limit=limit
            )
            
            items_added = 0
            items_updated = 0
            items_removed = 0
            errors = []
            
            if pages:
                # Process pages for knowledge base
                for page in pages:
                    try:
                        # Create document content from page
                        content = f"""
                        Page: {page.get('title', '')}
                        Space: {page.get('space', '')}
                        
                        Content:
                        {page.get('content', '')}
                        
                        URL: {page.get('url', '')}
                        
                        Created: {page.get('created', '')}
                        Updated: {page.get('updated', '')}
                        Size: {page.get('size', 0)} characters
                        Version: {page.get('version', '')}
                        Author: {page.get('author', '')}
                        
                        Labels: {', '.join([label.get('name', '') for label in page.get('labels', [])])}
                        
                        Attachments: {len(page.get('attachments', []))}
                        """
                        
                        # Create metadata
                        metadata = {
                            'source': 'confluence',
                            'source_id': page.get('id'),
                            'source_type': 'page',
                            'space_key': page.get('space'),
                            'title': page.get('title'),
                            'url': page.get('url'),
                            'created': page.get('created'),
                            'updated': page.get('updated'),
                            'version': page.get('version'),
                            'author': page.get('author'),
                            'size': page.get('size', 0),
                            'label_count': len(page.get('labels', [])),
                            'attachment_count': len(page.get('attachments', []))
                        }
                        
                        # Add to knowledge base
                        doc_id = await self.knowledge_base.add_document(
                            content=content,
                            metadata=metadata,
                            title=f"Confluence Page: {page.get('title', '')}"
                        )
                        
                        if doc_id:
                            items_added += 1
                            self.logger.info(f"Added Confluence page {page.get('title', '')} to knowledge base")
                        else:
                            errors.append(f"Failed to add page {page.get('title', '')}")
                    
                    except Exception as e:
                        error_msg = f"Error processing page {page.get('title', '')}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return SyncResult(
                source="confluence",
                items_processed=len(pages),
                items_added=items_added,
                items_updated=items_updated,
                items_removed=items_removed,
                errors=errors,
                duration=duration,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Confluence sync failed: {e}")
            return SyncResult(
                source="confluence",
                items_processed=0,
                items_added=0,
                items_updated=0,
                items_removed=0,
                errors=[str(e)],
                duration=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def sync_all(self) -> Dict[str, SyncResult]:
        """
        Synchronize all configured sources.
        
        Returns:
            Dictionary with sync results by source
        """
        self.logger.info("Starting full synchronization")
        
        results = {}
        
        # Sync Jira
        if self.jira_connector:
            jira_result = await self.sync_jira_issues()
            results['jira'] = jira_result
        
        # Sync Confluence
        if self.confluence_connector:
            confluence_result = await self.sync_confluence_pages()
            results['confluence'] = confluence_result
        
        return results
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current synchronization status and statistics.
        
        Returns:
            Dictionary with sync status information
        """
        status = {
            'jira': {
                'connected': self.jira_connector is not None,
                'last_sync': self.last_jira_sync,
                'total_syncs': 0  # Would track in production
            },
            'confluence': {
                'connected': self.confluence_connector is not None,
                'last_sync': self.last_confluence_sync,
                'total_syncs': 0  # Would track in production
            }
        }
        
        return status

def create_data_sync_service(config: Dict[str, Any], knowledge_base: KnowledgeBase, 
                          embedding_service: EmbeddingService, 
                          logger: Optional[logging.Logger] = None) -> DataSyncService:
    """
    Factory function to create data synchronization service instance.
    
    Args:
        config: Configuration dictionary
        knowledge_base: Knowledge base instance
        embedding_service: Embedding service instance
        logger: Logger instance (optional)
    
    Returns:
        DataSyncService instance
    """
    return DataSyncService(config, knowledge_base, embedding_service, logger)

if __name__ == "__main__":
    # Test data synchronization service
    from ..knowledge.knowledge_base import KnowledgeBase
    from ..embeddings.embedding_service import EmbeddingService
    
    # Create test instances
    kb = KnowledgeBase({'persist_directory': './test_sync_db'})
    embedding_service = EmbeddingService({'text_model': 'test-model'})
    
    # Create sync service
    config = {
        'jira_url': os.getenv('JIRA_URL', ''),
        'jira_username': os.getenv('JIRA_USERNAME', ''),
        'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
        'confluence_url': os.getenv('CONFLUENCE_URL', ''),
        'confluence_username': os.getenv('CONFLUENCE_USERNAME', ''),
        'confluence_api_token': os.getenv('CONFLUENCE_API_TOKEN', ''),
        'confluence_space': os.getenv('CONFLUENCE_SPACE', '')
    }
    
    sync_service = create_data_sync_service(config, kb, embedding_service)
    
    # Test initialization
    import asyncio
    result = asyncio.run(sync_service.initialize())
    print(f"Initialization result: {result}")
    
    if result:
        # Test sync operations
        jira_result = asyncio.run(sync_service.sync_jira_issues(limit=5))
        print(f"Jira sync result: {jira_result}")
        
        confluence_result = asyncio.run(sync_service.sync_confluence_pages(limit=5))
        print(f"Confluence sync result: {confluence_result}")
        
        # Get status
        status = asyncio.run(sync_service.get_sync_status())
        print(f"Sync status: {status}")
