#!/usr/bin/env python3
"""
Automated background synchronization service for EVAgent.
Continuously synchronizes Jira and Confluence data with the knowledge base.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
import signal
import json

# Add EVAgent src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import services
try:
    from src.services.data_sync_service import create_data_sync_service
    from src.knowledge.knowledge_base import KnowledgeBase
    from src.embeddings.embedding_service import EmbeddingService
except ImportError as e:
    print(f"Failed to import services: {e}")
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

class BackgroundSyncService:
    """Background synchronization service."""
    
    def __init__(self):
        self.running = False
        self.sync_service = None
        self.config = None
        
    async def initialize(self):
        """Initialize the sync service."""
        logger.info("Initializing background sync service...")
        
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
        
        # Create sync configuration
        sync_config = {
            'jira_url': os.getenv('JIRA_URL', ''),
            'jira_username': os.getenv('JIRA_USERNAME', ''),
            'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
            'confluence_url': os.getenv('CONFLUENCE_URL', ''),
            'confluence_username': os.getenv('CONFLUENCE_USERNAME', ''),
            'confluence_api_token': os.getenv('CONFLUENCE_API_TOKEN', ''),
            'confluence_space': os.getenv('CONFLUENCE_SPACE', ''),
            'sync_interval': self.config.get('sync_interval', 300),
            'sync_batch_size': self.config.get('sync_batch_size', 50),
            'max_retries': self.config.get('max_retries', 3)
        }
        
        # Create knowledge base and embedding service
        kb_config = {
            'persist_directory': self.config.get('knowledge_base', {}).get('persist_directory', './storage/chroma_db'),
            'collection_name': self.config.get('knowledge_base', {}).get('collection_name', 'evagent_documents')
        }
        
        embedding_config = {
            'text_model': self.config.get('knowledge_base', {}).get('text_model', './models/all-MiniLM-L6-v2'),
            'model_path': self.config.get('knowledge_base', {}).get('model_path', './models/all-MiniLM-L6-v2')
        }
        
        try:
            kb = KnowledgeBase(kb_config)
            embedding_service = EmbeddingService(embedding_config)
            self.sync_service = create_data_sync_service(sync_config, kb, embedding_service)
            
            # Initialize connectors
            await self.sync_service.initialize()
            logger.info("Background sync service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sync service: {e}")
            return False
    
    async def run_sync_cycle(self):
        """Run a single synchronization cycle."""
        logger.info("Starting synchronization cycle...")
        
        try:
            # Get sync status
            status = await self.sync_service.get_sync_status()
            logger.info(f"Current sync status: {json.dumps(status, indent=2)}")
            
            # Perform full synchronization
            result = await self.sync_service.sync_all()
            
            logger.info(f"Sync cycle completed:")
            logger.info(f"  Jira: {result.jira.items_processed} processed, {result.jira.items_added} added, {len(result.jira.errors)} errors")
            logger.info(f"  Confluence: {result.confluence.items_processed} processed, {result.confluence.items_added} added, {len(result.confluence.errors)} errors")
            logger.info(f"  Duration: {result.duration:.2f} seconds")
            
            # Log errors if any
            if result.jira.errors:
                logger.warning("Jira sync errors:")
                for error in result.jira.errors[:5]:  # Limit to first 5 errors
                    logger.warning(f"  - {error}")
            
            if result.confluence.errors:
                logger.warning("Confluence sync errors:")
                for error in result.confluence.errors[:5]:  # Limit to first 5 errors
                    logger.warning(f"  - {error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            return False
    
    async def run_background_sync(self):
        """Run continuous background synchronization."""
        logger.info("Starting background synchronization service...")
        self.running = True
        
        # Run initial sync
        await self.run_sync_cycle()
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main sync loop
        sync_interval = self.config.get('sync_interval', 300)  # 5 minutes default
        
        while self.running:
            try:
                logger.info(f"Next sync in {sync_interval} seconds...")
                await asyncio.sleep(sync_interval)
                
                if self.running:
                    await self.run_sync_cycle()
                    
            except asyncio.CancelledError:
                logger.info("Background sync cancelled")
                break
            except Exception as e:
                logger.error(f"Background sync error: {e}")
                # Continue running even if one cycle fails
                await asyncio.sleep(60)  # Wait 1 minute before retry
        
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
    print("EVAgent Background Synchronization Service")
    print("=" * 60)
    print()
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Create and start sync service
    sync_service = BackgroundSyncService()
    
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
