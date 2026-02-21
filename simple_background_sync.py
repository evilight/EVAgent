#!/usr/bin/env python3
"""
Simplified background synchronization service for EVAgent.
Tests the sync functionality without requiring ChromaDB.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
import signal
import json
import aiohttp

# Add EVAgent src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import services
try:
    from src.connectors.jira_connector import JiraConnector
    from src.connectors.confluence_connector import ConfluenceConnector
except ImportError as e:
    print(f"Failed to import connectors: {e}")
    print("Please ensure all required packages are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_service.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SimpleBackgroundSyncService:
    """Simplified background synchronization service."""
    
    def __init__(self):
        self.running = False
        self.jira_connector = None
        self.confluence_connector = None
        
    async def initialize(self):
        """Initialize the sync service."""
        logger.info("Initializing simplified background sync service...")
        
        # Load environment variables from .env file
        def load_env_from_file():
            """Load environment variables from .env file."""
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, "r", encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ[key] = value
        
        load_env_from_file()
        
        # Load sync configuration
        try:
            with open("sync_config.json", "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.warning("sync_config.json not found, using defaults")
            self.config = {
                "sync_interval": 300,
                "sync_batch_size": 50,
                "max_retries": 3
            }
        
        sync_interval = self.config.get('sync_interval', 300)
        
        # Create Jira connector
        jira_url = os.getenv('JIRA_URL', '')
        jira_username = os.getenv('JIRA_USERNAME', '')
        jira_api_token = os.getenv('JIRA_API_TOKEN', '')
        
        if jira_url and jira_username and jira_api_token:
            try:
                self.jira_connector = JiraConnector({
                    'url': jira_url,
                    'username': jira_username,
                    'api_token': jira_api_token,
                    'api': {'version': '3'}
                })
                logger.info("Jira connector created successfully")
            except Exception as e:
                logger.error(f"Failed to create Jira connector: {e}")
        
        # Create Confluence connector
        confluence_url = os.getenv('CONFLUENCE_URL', '')
        confluence_username = os.getenv('CONFLUENCE_USERNAME', '')
        confluence_api_token = os.getenv('CONFLUENCE_API_TOKEN', '')
        
        if confluence_url and confluence_username and confluence_api_token:
            try:
                self.confluence_connector = ConfluenceConnector({
                    'url': confluence_url,
                    'username': confluence_username,
                    'api_token': confluence_api_token,
                    'api': {'version': '2'}
                })
                logger.info("Confluence connector created successfully")
            except Exception as e:
                logger.error(f"Failed to create Confluence connector: {e}")
        
        logger.info("Simplified background sync service initialized successfully")
        return True
    
    async def run_sync_cycle(self):
        """Run a single synchronization cycle."""
        logger.info("Starting synchronization cycle...")
        
        try:
            # Test Jira connectivity
            if self.jira_connector:
                logger.info("Testing Jira connectivity...")
                try:
                    # Use direct API calls instead of connector test
                    jira_url = os.getenv('JIRA_URL', '')
                    jira_username = os.getenv('JIRA_USERNAME', '')
                    jira_api_token = os.getenv('JIRA_API_TOKEN', '')
                    
                    import base64
                    auth_string = f'{jira_username}:{jira_api_token}'
                    auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
                    
                    headers = {
                        'Authorization': f'Basic {auth_b64}',
                        'Accept': 'application/json',
                        'User-Agent': 'EVAgent-RAG/1.0'
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        # Test server info
                        async with session.get(f'{jira_url}/rest/api/2/serverInfo', headers=headers) as response:
                            if response.status == 200:
                                server_info = await response.json()
                                logger.info(f"Jira server: {server_info.get('serverTitle', 'Unknown')}")
                            else:
                                raise Exception(f"Server info failed: {response.status}")
                        
                        # Test projects
                        async with session.get(f'{jira_url}/rest/api/3/project', headers=headers) as response:
                            if response.status == 200:
                                projects = await response.json()
                                logger.info(f"Jira projects found: {len(projects)}")
                            else:
                                raise Exception(f"Projects failed: {response.status}")
                        
                        # Test search
                        search_url = f'{jira_url}/rest/api/3/search/jql'
                        params = {
                            'jql': 'updated >= -1d ORDER BY updated DESC',
                            'maxResults': 10,
                            'fields': 'key,summary,description,status,priority,assignee,reporter,created,updated,project,issuetype,components,labels,attachment,comment'
                        }
                        
                        async with session.get(search_url, headers=headers, params=params) as response:
                            if response.status == 200:
                                issues_result = await response.json()
                                issues = issues_result.get('issues', [])
                                logger.info(f"Recent Jira issues: {len(issues)}")
                                
                                if issues:
                                    for issue in issues[:3]:  # Log first 3 issues
                                        key = issue.get('key', 'Unknown')
                                        fields = issue.get('fields', {})
                                        
                                        # Get standard fields with fallbacks
                                        summary = fields.get('summary', 'No summary')[:50]
                                        description = fields.get('description', 'No description')[:50]
                                        status = fields.get('status', {}).get('name', 'No status')
                                        priority = fields.get('priority', {}).get('name', 'No priority')
                                        assignee = fields.get('assignee', {}).get('displayName', 'Unassigned')
                                        reporter = fields.get('reporter', {}).get('displayName', 'No reporter')
                                        project = fields.get('project', {}).get('name', 'No project')
                                        issuetype = fields.get('issuetype', {}).get('name', 'No type')
                                        created = fields.get('created', 'No date')[:10]
                                        updated = fields.get('updated', 'No date')[:10]
                                        components = [c.get('name', 'Unknown') for c in fields.get('components', [])]
                                        labels = fields.get('labels', [])
                                        attachment_count = len(fields.get('attachment', []))
                                        comment_count = fields.get('comment', {}).get('total', 0)
                                        
                                        logger.info(f"  - {key}: {summary}")
                                        logger.info(f"    Status: {status}, Priority: {priority}, Type: {issuetype}")
                                        logger.info(f"    Assignee: {assignee}, Reporter: {reporter}")
                                        logger.info(f"    Project: {project}, Created: {created}, Updated: {updated}")
                                        logger.info(f"    Components: {components}, Labels: {labels}")
                                        logger.info(f"    Attachments: {attachment_count}, Comments: {comment_count}")
                                        if description != 'No description':
                                            logger.info(f"    Description: {description}")
                                        logger.info("")
                            else:
                                raise Exception(f"Search failed: {response.status}")
                    
                except Exception as e:
                    logger.error(f"Jira sync error: {e}")
                    # Exit on authentication errors
                    if "401" in str(e) or "403" in str(e) or "unauthorized" in str(e).lower():
                        logger.error("Authentication failed - stopping sync service")
                        return False
            
            # Skip Confluence testing for now (permission issues)
            if False and self.confluence_connector:
                logger.info("Testing Confluence connectivity...")
                try:
                    await self.confluence_connector.connect()
                    
                    # Get spaces
                    spaces = await self.confluence_connector.get_spaces()
                    logger.info(f"Confluence spaces found: {len(spaces)}")
                    
                    # Get recent pages
                    if spaces:
                        pages = await self.confluence_connector.get_spaces()
                        logger.info(f"Recent Confluence pages: {len(pages)}")
                        
                except Exception as e:
                    logger.error(f"Confluence sync error: {e}")
                    # Exit on authentication errors
                    if "401" in str(e) or "403" in str(e) or "unauthorized" in str(e).lower() or "not permitted" in str(e).lower():
                        logger.error("Authentication failed - stopping sync service")
                        return False
            
            logger.info("Sync cycle completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            return False
    
    async def run_background_sync(self):
        """Run continuous background synchronization."""
        logger.info("Starting background synchronization service...")
        self.running = True
        
        # Run initial sync
        initial_result = await self.run_sync_cycle()
        if not initial_result:
            logger.error("Initial sync failed - stopping service")
            return
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main sync loop - run only 2 rounds
        sync_interval = 10  # 10 seconds between rounds
        max_rounds = 2
        current_round = 0
        
        while self.running and current_round < max_rounds:
            current_round += 1
            logger.info(f"Starting sync round {current_round}/{max_rounds}")
            
            try:
                if current_round > 1:  # Don't sleep before first round
                    logger.info(f"Waiting {sync_interval} seconds before next round...")
                    await asyncio.sleep(sync_interval)
                
                if self.running:
                    sync_result = await self.run_sync_cycle()
                    if not sync_result:
                        logger.error("Sync cycle failed - stopping service")
                        break
                    
                    if current_round >= max_rounds:
                        logger.info(f"Completed {max_rounds} sync rounds - stopping service")
                        self.running = False
                    
            except asyncio.CancelledError:
                logger.info("Background sync cancelled")
                break
            except Exception as e:
                logger.error(f"Background sync error: {e}")
                # Continue to next round if possible
                if current_round >= max_rounds:
                    break
        
        logger.info("Background synchronization service stopped")
    
    async def start(self):
        """Start the background sync service."""
        if not await self.initialize():
            logger.error("Failed to initialize sync service")
            return False
        
        await self.run_background_sync()
        return True
    
    def stop(self):
        """Stop the background sync service."""
        logger.info("Stopping background sync service...")
        self.running = False

async def main():
    """Main entry point."""
    print("=" * 60)
    print("EVAgent Simplified Background Synchronization Service")
    print("=" * 60)
    print()
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Create and start sync service
    sync_service = SimpleBackgroundSyncService()
    
    try:
        await sync_service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sync_service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sync_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
