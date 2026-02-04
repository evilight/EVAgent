#!/usr/bin/env python3
"""
Example usage of the EVAgent RAG System.

This script demonstrates how to use the various components of the RAG system
to fetch data from Jira, process it, and perform semantic search.
"""

import asyncio
import logging
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils import ConfigLoader, setup_logger
from src.connectors import JiraConnector
from src.processors import TextProcessor, AttachmentProcessor, MetadataExtractor
from src.embeddings import EmbeddingService
from src.database import ChromaManager
from src.api import RAGQueryInterface


async def main():
    """Main example function."""
    
    # Setup logging
    logger = setup_logger("example", "INFO")
    logger.info("Starting EVAgent RAG System Example")
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        
        # Initialize components
        logger.info("Initializing RAG system components...")
        
        # 1. Initialize connectors
        jira_config = config_loader.load_config("jira_config")
        jira_connector = JiraConnector(jira_config, logger)
        
        # 2. Initialize processors
        text_processor = TextProcessor(logger)
        attachment_processor = AttachmentProcessor(logger)
        metadata_extractor = MetadataExtractor(logger)
        
        # 3. Initialize embedding service
        embedding_config = config_loader.load_config("embedding_config")
        embedding_service = EmbeddingService(embedding_config, logger)
        
        # 4. Initialize database
        db_config = {
            "persist_directory": "./storage/chroma_db",
            "collection_name": "rag_documents"
        }
        chroma_manager = ChromaManager(db_config, logger)
        
        # 5. Initialize query interface
        query_interface = RAGQueryInterface(
            embedding_service=embedding_service,
            chroma_manager=chroma_manager,
            config=embedding_config,
            logger=logger
        )
        
        logger.info("All components initialized successfully")
        
        # Example 1: Fetch data from Jira
        logger.info("\n=== Example 1: Fetching data from Jira ===")
        
        async with jira_connector:
            # Search for recent bugs
            issues = await jira_connector.search_issues(
                jql="type = Bug AND status in (Open, 'In Progress') ORDER BY updated DESC",
                max_results=5
            )
            
            logger.info(f"Found {len(issues.get('issues', []))} issues")
            
            # Process each issue
            for issue in issues.get('issues', []):
                logger.info(f"\nProcessing issue: {issue['key']}")
                
                # Extract metadata
                metadata = metadata_extractor.extract_jira_metadata(issue)
                logger.info(f"  Title: {metadata['title']}")
                logger.info(f"  Status: {metadata['status']}")
                logger.info(f"  Priority: {metadata['priority']}")
                
                # Process description
                description = metadata.get('description', '')
                if description:
                    cleaned_text = text_processor.clean_html(description)
                    logger.info(f"  Description length: {len(cleaned_text)} chars")
                    
                    # Generate embedding
                    embedding = await embedding_service.embed_text(cleaned_text)
                    if embedding.size > 0:
                        # Store in vector database
                        doc_id = chroma_manager.add_document(
                            content=cleaned_text,
                            embedding=embedding,
                            metadata=metadata
                        )
                        logger.info(f"  Stored document with ID: {doc_id}")
        
        # Example 2: Semantic search
        logger.info("\n=== Example 2: Performing semantic search ===")
        
        search_query = "NullPointerException authentication error"
        logger.info(f"Searching for: '{search_query}'")
        
        search_results = await query_interface.semantic_search(
            query=search_query,
            limit=3,
            similarity_threshold=0.5
        )
        
        logger.info(f"Found {len(search_results.get('results', []))} results:")
        for i, result in enumerate(search_results.get('results', []), 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"  ID: {result['id']}")
            logger.info(f"  Similarity: {result['similarity']:.3f}")
            logger.info(f"  Title: {result['metadata'].get('title', 'N/A')}")
            logger.info(f"  Status: {result['metadata'].get('status', 'N/A')}")
            logger.info(f"  URL: {result['metadata'].get('url', 'N/A')}")
        
        # Example 3: Bug similarity search
        logger.info("\n=== Example 3: Finding similar bugs ===")
        
        error_message = "NullPointerException in AuthenticationService"
        stack_trace = """
        at com.example.AuthenticationService.authenticate(AuthenticationService.java:42)
        at com.example.SecurityFilter.doFilter(SecurityFilter.java:89)
        at javax.servlet.http.HttpServlet.service(HttpServlet.java:623)
        """
        
        logger.info(f"Finding bugs similar to: {error_message}")
        
        bug_results = await query_interface.find_similar_bugs(
            error_message=error_message,
            stack_trace=stack_trace,
            context={"project": "DEMO"},
            limit=3
        )
        
        logger.info(f"Found {len(bug_results.get('results', []))} similar bugs:")
        for i, result in enumerate(bug_results.get('results', []), 1):
            logger.info(f"\nBug {i}:")
            logger.info(f"  ID: {result['id']}")
            logger.info(f"  Bug Score: {result.get('bug_score', 0):.3f}")
            logger.info(f"  Title: {result['metadata'].get('title', 'N/A')}")
            logger.info(f"  Matching Errors: {result.get('matching_errors', [])}")
        
        # Example 4: System statistics
        logger.info("\n=== Example 4: System statistics ===")
        
        stats = await query_interface.get_system_stats()
        logger.info("System Statistics:")
        logger.info(f"  Documents in database: {stats['database'].get('document_count', 0)}")
        logger.info(f"  Files in database: {stats['database'].get('file_count', 0)}")
        logger.info(f"  Text model: {stats['embeddings'].get('text_model', 'N/A')}")
        logger.info(f"  Embedding dimension: {stats['embeddings'].get('embedding_dim', 0)}")
        
        logger.info("\n=== Example completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("./storage/chroma_db", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    
    # Run the example
    asyncio.run(main())
