"""Test and import data from Jira and Confluence"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from connectors.jira_connector import JiraConnector
from connectors.confluence_connector import ConfluenceConnector
from knowledge.knowledge_base import KnowledgeBase
from utils.config_loader import ConfigLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataImporter:
    """Import data from Jira and Confluence into the knowledge base"""
    
    def __init__(self):
        self.knowledge_base = None
        self.jira_connector = None
        self.confluence_connector = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from files"""
        try:
            config_loader = ConfigLoader()
            config = {
                'jira': config_loader.load_config('jira_config.yaml'),
                'confluence': config_loader.load_config('confluence_config.yaml')
            }
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def setup_connectors(self, config: Dict[str, Any]):
        """Setup Jira and Confluence connectors"""
        try:
            # Setup Jira connector
            if config.get('jira'):
                jira_config = config['jira']
                # Replace environment variables
                jira_config['username'] = os.getenv('JIRA_USERNAME', jira_config['username'])
                jira_config['api_token'] = os.getenv('JIRA_API_TOKEN', jira_config['api_token'])
                
                self.jira_connector = JiraConnector(jira_config)
                logger.info("Jira connector initialized")
            
            # Setup Confluence connector
            if config.get('confluence'):
                confluence_config = config['confluence']
                confluence_config['username'] = os.getenv('CONFLUENCE_USERNAME', confluence_config['username'])
                confluence_config['api_token'] = os.getenv('CONFLUENCE_API_TOKEN', confluence_config['api_token'])
                
                self.confluence_connector = ConfluenceConnector(confluence_config)
                logger.info("Confluence connector initialized")
                
        except Exception as e:
            logger.error(f"Error setting up connectors: {e}")
    
    def setup_knowledge_base(self):
        """Setup knowledge base"""
        try:
            kb_config = {
                'persist_directory': './storage/rag_import_db',
                'collection_name': 'evagent_imported',
                'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
                'chunk_size': 300,
                'chunk_overlap': 30
            }
            self.knowledge_base = KnowledgeBase(kb_config)
            logger.info("Knowledge base initialized")
            
        except Exception as e:
            logger.error(f"Error setting up knowledge base: {e}")
    
    async def test_jira_connection(self) -> bool:
        """Test Jira connection"""
        if not self.jira_connector:
            logger.warning("Jira connector not initialized")
            return False
        
        try:
            # Test basic connection
            projects = await self.jira_connector.get_projects()
            logger.info(f"✓ Jira connection successful. Found {len(projects)} projects")
            
            # Test fetching issues
            issues = await self.jira_connector.get_issues(limit=5)
            logger.info(f"✓ Successfully fetched {len(issues)} sample issues")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Jira connection failed: {e}")
            return False
    
    async def test_confluence_connection(self) -> bool:
        """Test Confluence connection"""
        if not self.confluence_connector:
            logger.warning("Confluence connector not initialized")
            return False
        
        try:
            # Test basic connection
            spaces = await self.confluence_connector.get_spaces()
            logger.info(f"✓ Confluence connection successful. Found {len(spaces)} spaces")
            
            # Test fetching pages
            pages = await self.confluence_connector.get_pages(limit=5)
            logger.info(f"✓ Successfully fetched {len(pages)} sample pages")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Confluence connection failed: {e}")
            return False
    
    async def import_jira_data(self, limit: int = 50) -> int:
        """Import data from Jira"""
        if not self.jira_connector or not self.knowledge_base:
            logger.error("Jira connector or knowledge base not initialized")
            return 0
        
        try:
            logger.info("Starting Jira data import...")
            
            # Get issues
            issues = await self.jira_connector.get_issues(limit=limit)
            imported_count = 0
            
            for issue in issues:
                try:
                    # Prepare document metadata
                    metadata = {
                        'source': 'jira',
                        'type': 'issue',
                        'id': issue.get('key'),
                        'project': issue.get('fields', {}).get('project', {}).get('key'),
                        'status': issue.get('fields', {}).get('status', {}).get('name'),
                        'priority': issue.get('fields', {}).get('priority', {}).get('name'),
                        'issue_type': issue.get('fields', {}).get('issuetype', {}).get('name'),
                        'url': f"https://evilight.atlassian.net/browse/{issue.get('key')}"
                    }
                    
                    # Prepare content
                    title = issue.get('fields', {}).get('summary', '')
                    description = issue.get('fields', {}).get('description', '') or ''
                    content = f"Title: {title}\n\nDescription: {description}"
                    
                    # Add comments
                    comments = issue.get('fields', {}).get('comment', {}).get('comments', [])
                    if comments:
                        content += "\n\nComments:\n"
                        for comment in comments[:5]:  # Limit comments
                            content += f"- {comment.get('body', '')}\n"
                    
                    # Import to knowledge base
                    await self.knowledge_base.add_document(
                        content=content,
                        metadata=metadata,
                        document_id=f"jira-{issue.get('key')}"
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing Jira issue {issue.get('key')}: {e}")
                    continue
            
            logger.info(f"✓ Successfully imported {imported_count} Jira issues")
            return imported_count
            
        except Exception as e:
            logger.error(f"✗ Jira import failed: {e}")
            return 0
    
    async def import_confluence_data(self, limit: int = 25) -> int:
        """Import data from Confluence"""
        if not self.confluence_connector or not self.knowledge_base:
            logger.error("Confluence connector or knowledge base not initialized")
            return 0
        
        try:
            logger.info("Starting Confluence data import...")
            
            # Get pages
            pages = await self.confluence_connector.get_pages(limit=limit)
            imported_count = 0
            
            for page in pages:
                try:
                    # Prepare document metadata
                    metadata = {
                        'source': 'confluence',
                        'type': 'page',
                        'id': page.get('id'),
                        'title': page.get('title'),
                        'space': page.get('space', {}).get('key'),
                        'url': page.get('_links', {}).get('webui')
                    }
                    
                    # Get full page content
                    page_content = await self.confluence_connector.get_page_content(page.get('id'))
                    content = f"Title: {page.get('title')}\n\nContent: {page_content}"
                    
                    # Import to knowledge base
                    await self.knowledge_base.add_document(
                        content=content,
                        metadata=metadata,
                        document_id=f"confluence-{page.get('id')}"
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing Confluence page {page.get('id')}: {e}")
                    continue
            
            logger.info(f"✓ Successfully imported {imported_count} Confluence pages")
            return imported_count
            
        except Exception as e:
            logger.error(f"✗ Confluence import failed: {e}")
            return 0
    
    async def run_import(self, jira_limit: int = 50, confluence_limit: int = 25):
        """Run the complete import process"""
        logger.info("Starting data import process...")
        
        # Load config
        config = self.load_config()
        if not config:
            logger.error("Failed to load configuration")
            return
        
        # Setup components
        self.setup_connectors(config)
        self.setup_knowledge_base()
        
        # Test connections
        jira_ok = await self.test_jira_connection()
        confluence_ok = await self.test_confluence_connection()
        
        if not jira_ok and not confluence_ok:
            logger.error("Both connections failed. Please check your credentials.")
            return
        
        # Import data
        total_imported = 0
        if jira_ok:
            total_imported += await self.import_jira_data(jira_limit)
        
        if confluence_ok:
            total_imported += await self.import_confluence_data(confluence_limit)
        
        logger.info(f"Import complete. Total documents imported: {total_imported}")
        
        # Get knowledge base stats
        if self.knowledge_base:
            stats = self.knowledge_base.get_stats()
            logger.info(f"Knowledge base now contains {stats.get('document_count', 0)} documents")

if __name__ == "__main__":
    importer = DataImporter()
    asyncio.run(importer.run_import())
