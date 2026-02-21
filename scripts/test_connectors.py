"""
Test script for Jira and Confluence connectors.
Tests the complete data synchronization pipeline.
"""

import os
import sys
import sys
import os
from pathlib import Path
import asyncio
import logging
from datetime import datetime

# Add EVAgent src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import services
try:
    from src.services.data_sync_service import create_data_sync_service
    from src.connectors.jira_connector import JiraConnector
    from src.connectors.confluence_connector import ConfluenceConnector
    from src.knowledge.knowledge_base import KnowledgeBase
    from src.embeddings.embedding_service import EmbeddingService
except ImportError as e:
    print(f"Failed to import services: {e}")
    print("Please ensure all required packages are installed:")
    print("   - pip install fastapi uvicorn python-jose requests")
    print("   - pip install python-dotenv")
    print("   - Check that src/services/ directory exists")
    print("   - Verify the connector files are in place")
    sys.exit(1)

logger = logging.getLogger(__name__)

async def test_connectors():
    """Test Jira and Confluence connectors with real configuration."""
    print("=" * 60)
    print("EVAgent Data Synchronization Test")
    print("=" * 60)
    print()
    
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
                        print(f"Loaded: {key}")

    # Load environment variables
    load_env_from_file()

    # Configuration
    config = {
        'jira_url': os.getenv('JIRA_URL', ''),
        'jira_username': os.getenv('JIRA_USERNAME', ''),
        'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
        'confluence_url': os.getenv('CONFLUENCE_URL', ''),
        'confluence_username': os.getenv('CONFLUENCE_USERNAME', ''),
        'confluence_api_token': os.getenv('CONFLUENCE_API_TOKEN', ''),
        'confluence_space': os.getenv('CONFLUENCE_SPACE', ''),
        'sync_interval': 300,  # 5 minutes
        'sync_batch_size': 50,
        'max_retries': 3
    }
    
    # Check environment variables
    missing_vars = []
    if not config['jira_url']:
        missing_vars.append('JIRA_URL')
    if not config['jira_username']:
        missing_vars.append('JIRA_USERNAME')
    if not config['jira_api_token']:
        missing_vars.append('JIRA_API_TOKEN')
    
    if missing_vars:
        print("Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("Please set the following environment variables:")
        print("set JIRA_URL=\"https://your-domain.atlassian.net\"")
        print("set JIRA_USERNAME=\"your-username\"")
        print("set JIRA_API_TOKEN=\"your-api-token\"")
        print()
        return False
    
    try:
        # Create test instances
        kb = KnowledgeBase({'persist_directory': './test_sync_db'})
        embedding_service = EmbeddingService({'text_model': 'test-model'})
        
        # Create sync service
        sync_service = create_data_sync_service(config, kb, embedding_service)
        
        # Test initialization
        print("1. Testing connector initialization...")
        init_result = await sync_service.initialize()
        
        if init_result:
            print("✅ Connectors initialized successfully")
            print()
            print("2. Testing Jira connection...")
            jira_result = await sync_service.jira_connector.test_connection()
            print(f"   Jira: {jira_result['status']} - {jira_result.get('message', '')}")
            
            print("3. Testing Confluence connection...")
            confluence_result = await sync_service.confluence_connector.test_connection()
            print(f"   Confluence: {confluence_result['status']} - {confluence_result.get('message', '')}")
            
            if jira_result['status'] == 'success' or confluence_result['status'] == 'success':
                print()
                print("4. Testing Jira sync (5 issues)...")
                jira_sync = await sync_service.sync_jira_issues(limit=5)
                print(f"   Issues processed: {jira_sync.items_processed}")
                print(f"   Items added: {jira_sync.items_added}")
                print(f"   Errors: {len(jira_sync.errors)}")
                print(f"   Duration: {jira_sync.duration:.2f}s")
                
                print("5. Testing Confluence sync (5 pages)...")
                confluence_sync = await sync_service.sync_confluence_pages(limit=5)
                print(f"   Pages processed: {confluence_sync.items_processed}")
                print(f"   Items added: {confluence_sync.items_added}")
                print(f"   Errors: {len(confluence_sync.errors)}")
                print(f"   Duration: {confluence_sync.duration:.2f}s")
                
                print()
                print("6. Getting sync status...")
                status = await sync_service.get_sync_status()
                print(f"   Jira connected: {status['jira']['connected']}")
                print(f"   Confluence connected: {status['confluence']['connected']}")
                
                print()
                print("All tests completed successfully!")
                return True
            else:
                print("No connectors are properly configured")
                return False
                
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connectors())
