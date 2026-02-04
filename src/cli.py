"""
Command-line interface for EVAgent RAG System.
"""

import asyncio
import click
import logging
import sys
from pathlib import Path
from typing import Optional

from .utils import ConfigLoader, setup_logger
from .connectors import JiraConnector, ConfluenceConnector
from .processors import TextProcessor, AttachmentProcessor, MetadataExtractor
from .embeddings import EmbeddingService
from .database import ChromaManager
from .api import RAGQueryInterface, SearchAPI


@click.group()
@click.option('--config-dir', default='config', help='Configuration directory')
@click.option('--log-level', default='INFO', help='Log level')
@click.pass_context
def cli(ctx, config_dir: str, log_level: str):
    """EVAgent RAG System CLI."""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    ctx.obj['log_level'] = log_level
    
    # Setup logging
    logger = setup_logger('evagent_cli', level=getattr(logging, log_level.upper()))
    ctx.obj['logger'] = logger


@cli.command()
@click.pass_context
def status(ctx):
    """Check system status and configuration."""
    logger = ctx.obj['logger']
    config_dir = ctx.obj['config_dir']
    
    click.echo("EVAgent RAG System Status")
    click.echo("=" * 30)
    
    try:
        # Check configuration files
        config_loader = ConfigLoader(config_dir)
        
        configs = ['jira_config', 'confluence_config', 'embedding_config']
        for config_name in configs:
            try:
                config = config_loader.load_config(config_name)
                click.echo(f"✅ {config_name}: Loaded")
            except FileNotFoundError:
                click.echo(f"❌ {config_name}: Not found")
            except Exception as e:
                click.echo(f"⚠️  {config_name}: Error - {e}")
        
        # Check database
        try:
            db_config = {
                "persist_directory": "./storage/chroma_db",
                "collection_name": "rag_documents"
            }
            chroma_manager = ChromaManager(db_config, logger)
            stats = chroma_manager.get_collection_stats()
            click.echo(f"✅ Database: {stats.get('document_count', 0)} documents, {stats.get('file_count', 0)} files")
        except Exception as e:
            click.echo(f"❌ Database: Error - {e}")
        
        # Check embedding service
        try:
            embedding_config = config_loader.load_config("embedding_config")
            embedding_service = EmbeddingService(embedding_config, logger)
            info = embedding_service.get_embedding_info()
            click.echo(f"✅ Embeddings: {info.get('text_model', 'Unknown')}")
        except Exception as e:
            click.echo(f"❌ Embeddings: Error - {e}")
        
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")


@cli.command()
@click.option('--source', type=click.Choice(['jira', 'confluence', 'all']), default='all', help='Data source to sync')
@click.option('--projects', help='Comma-separated list of projects/spaces')
@click.option('--limit', type=int, default=100, help='Maximum number of items to sync')
@click.pass_context
def sync(ctx, source: str, projects: Optional[str], limit: int):
    """Sync data from Jira and/or Confluence."""
    logger = ctx.obj['logger']
    config_dir = ctx.obj['config_dir']
    
    click.echo(f"Syncing data from {source}...")
    
    async def run_sync():
        try:
            config_loader = ConfigLoader(config_dir)
            
            # Initialize processors
            text_processor = TextProcessor(logger)
            attachment_processor = AttachmentProcessor(logger)
            metadata_extractor = MetadataExtractor(logger)
            
            # Initialize embedding service
            embedding_config = config_loader.load_config("embedding_config")
            embedding_service = EmbeddingService(embedding_config, logger)
            
            # Initialize database
            db_config = {
                "persist_directory": "./storage/chroma_db",
                "collection_name": "rag_documents"
            }
            chroma_manager = ChromaManager(db_config, logger)
            
            total_processed = 0
            
            # Sync Jira
            if source in ['jira', 'all']:
                click.echo("Syncing Jira data...")
                
                jira_config = config_loader.load_config("jira_config")
                jira_connector = JiraConnector(jira_config, logger)
                
                async with jira_connector:
                    # Parse projects if specified
                    project_list = projects.split(',') if projects else jira_config.get('projects', [])
                    
                    # Fetch data
                    issues = await jira_connector.fetch_data(projects=project_list)
                    
                    for issue in issues[:limit]:
                        try:
                            # Extract metadata
                            metadata = metadata_extractor.extract_jira_metadata(issue)
                            
                            # Process content
                            description = metadata.get('description', '')
                            if description:
                                cleaned_text = text_processor.clean_html(description)
                                
                                # Generate embedding
                                embedding = await embedding_service.embed_text(cleaned_text)
                                if embedding.size > 0:
                                    # Store in database
                                    doc_id = chroma_manager.add_document(
                                        content=cleaned_text,
                                        embedding=embedding,
                                        metadata=metadata
                                    )
                                    total_processed += 1
                                    
                                    if total_processed % 10 == 0:
                                        click.echo(f"Processed {total_processed} items...")
                        
                        except Exception as e:
                            logger.warning(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
            
            # Sync Confluence
            if source in ['confluence', 'all']:
                click.echo("Syncing Confluence data...")
                
                confluence_config = config_loader.load_config("confluence_config")
                confluence_connector = ConfluenceConnector(confluence_config, logger)
                
                async with confluence_connector:
                    # Parse spaces if specified
                    space_list = projects.split(',') if projects else confluence_config.get('spaces', [])
                    
                    # Fetch data
                    pages = await confluence_connector.fetch_data(spaces=space_list)
                    
                    for page in pages[:limit]:
                        try:
                            # Extract metadata
                            metadata = confluence_connector.extract_page_metadata(page)
                            
                            # Process content
                            content = metadata.get('content', '')
                            if content:
                                cleaned_text = text_processor.clean_html(content)
                                
                                # Generate embedding
                                embedding = await embedding_service.embed_text(cleaned_text)
                                if embedding.size > 0:
                                    # Store in database
                                    doc_id = chroma_manager.add_document(
                                        content=cleaned_text,
                                        embedding=embedding,
                                        metadata=metadata
                                    )
                                    total_processed += 1
                                    
                                    if total_processed % 10 == 0:
                                        click.echo(f"Processed {total_processed} items...")
                        
                        except Exception as e:
                            logger.warning(f"Failed to process page {page.get('id', 'unknown')}: {e}")
            
            click.echo(f"✅ Sync completed! Processed {total_processed} items.")
            
        except Exception as e:
            click.echo(f"❌ Sync failed: {e}")
            logger.error(f"Sync failed: {e}")
    
    asyncio.run(run_sync())


@cli.command()
@click.argument('query')
@click.option('--limit', type=int, default=10, help='Maximum number of results')
@click.option('--threshold', type=float, default=0.7, help='Similarity threshold')
@click.option('--include-attachments', is_flag=True, help='Include attachment results')
@click.pass_context
def search(ctx, query: str, limit: int, threshold: float, include_attachments: bool):
    """Search for documents using semantic search."""
    logger = ctx.obj['logger']
    config_dir = ctx.obj['config_dir']
    
    async def run_search():
        try:
            config_loader = ConfigLoader(config_dir)
            
            # Initialize components
            embedding_config = config_loader.load_config("embedding_config")
            embedding_service = EmbeddingService(embedding_config, logger)
            
            db_config = {
                "persist_directory": "./storage/chroma_db",
                "collection_name": "rag_documents"
            }
            chroma_manager = ChromaManager(db_config, logger)
            
            query_interface = RAGQueryInterface(
                embedding_service=embedding_service,
                chroma_manager=chroma_manager,
                config=embedding_config,
                logger=logger
            )
            
            # Perform search
            results = await query_interface.semantic_search(
                query=query,
                limit=limit,
                similarity_threshold=threshold,
                include_attachments=include_attachments
            )
            
            # Display results
            click.echo(f"Search Results for: '{query}'")
            click.echo("=" * 50)
            
            if not results.get('results'):
                click.echo("No results found.")
                return
            
            for i, result in enumerate(results.get('results', []), 1):
                click.echo(f"\n{i}. {result['metadata'].get('title', 'N/A')}")
                click.echo(f"   Similarity: {result['similarity']:.3f}")
                click.echo(f"   Source: {result['metadata'].get('source', 'N/A')}")
                click.echo(f"   Type: {result['metadata'].get('type', 'N/A')}")
                click.echo(f"   Status: {result['metadata'].get('status', 'N/A')}")
                click.echo(f"   URL: {result['metadata'].get('url', 'N/A')}")
                
                # Show preview of content
                content = result.get('content', '')
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    click.echo(f"   Preview: {preview}")
        
        except Exception as e:
            click.echo(f"❌ Search failed: {e}")
            logger.error(f"Search failed: {e}")
    
    asyncio.run(run_search())


@cli.command()
@click.argument('error_message')
@click.option('--stack-trace', help='Stack trace for better matching')
@click.option('--project', help='Project to limit search to')
@click.option('--limit', type=int, default=10, help='Maximum number of results')
@click.pass_context
def find_bugs(ctx, error_message: str, stack_trace: Optional[str], project: Optional[str], limit: int):
    """Find similar bugs based on error message."""
    logger = ctx.obj['logger']
    config_dir = ctx.obj['config_dir']
    
    async def run_bug_search():
        try:
            config_loader = ConfigLoader(config_dir)
            
            # Initialize components
            embedding_config = config_loader.load_config("embedding_config")
            embedding_service = EmbeddingService(embedding_config, logger)
            
            db_config = {
                "persist_directory": "./storage/chroma_db",
                "collection_name": "rag_documents"
            }
            chroma_manager = ChromaManager(db_config, logger)
            
            query_interface = RAGQueryInterface(
                embedding_service=embedding_service,
                chroma_manager=chroma_manager,
                config=embedding_config,
                logger=logger
            )
            
            # Build context
            context = {}
            if project:
                context['project'] = project
            
            # Perform bug search
            results = await query_interface.find_similar_bugs(
                error_message=error_message,
                stack_trace=stack_trace,
                context=context,
                limit=limit
            )
            
            # Display results
            click.echo(f"Similar Bugs for: '{error_message}'")
            click.echo("=" * 50)
            
            if not results.get('results'):
                click.echo("No similar bugs found.")
                return
            
            for i, result in enumerate(results.get('results', []), 1):
                click.echo(f"\n{i}. {result['metadata'].get('title', 'N/A')}")
                click.echo(f"   Bug Score: {result.get('bug_score', 0):.3f}")
                click.echo(f"   Similarity: {result['similarity']:.3f}")
                click.echo(f"   Status: {result['metadata'].get('status', 'N/A')}")
                click.echo(f"   Priority: {result['metadata'].get('priority', 'N/A')}")
                click.echo(f"   URL: {result['metadata'].get('url', 'N/A')}")
                
                matching_errors = result.get('matching_errors', [])
                if matching_errors:
                    click.echo(f"   Matching Errors: {', '.join(matching_errors)}")
        
        except Exception as e:
            click.echo(f"❌ Bug search failed: {e}")
            logger.error(f"Bug search failed: {e}")
    
    asyncio.run(run_bug_search())


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', type=int, default=8000, help='Port to bind to')
@click.pass_context
def serve(ctx, host: str, port: int):
    """Start the search API server."""
    logger = ctx.obj['logger']
    config_dir = ctx.obj['config_dir']
    
    try:
        config_loader = ConfigLoader(config_dir)
        
        # Initialize components
        embedding_config = config_loader.load_config("embedding_config")
        embedding_service = EmbeddingService(embedding_config, logger)
        
        db_config = {
            "persist_directory": "./storage/chroma_db",
            "collection_name": "rag_documents"
        }
        chroma_manager = ChromaManager(db_config, logger)
        
        # Create and run API server
        search_api = SearchAPI(
            embedding_service=embedding_service,
            chroma_manager=chroma_manager,
            config=embedding_config,
            logger=logger
        )
        
        click.echo(f"Starting EVAgent Search API server on {host}:{port}")
        click.echo(f"API docs will be available at http://{host}:{port}/docs")
        
        search_api.run(host=host, port=port)
        
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}")
        logger.error(f"Failed to start server: {e}")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()
