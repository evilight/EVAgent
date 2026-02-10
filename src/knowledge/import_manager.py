"""
Import manager for EVAgent RAG system.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timezone
import asyncio
from pathlib import Path
import json

from ..processors.document_processor import DocumentProcessor
from ..processors.content_cleaner import ContentCleaner
from ..knowledge.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class ImportManager:
    """
    Manager for importing documents from various sources.
    
    Handles:
    - Bulk imports from Jira/Confluence
    - Incremental updates
    - Progress tracking
    - Error handling and recovery
    - Import scheduling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize import manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Initialize components
        self.knowledge_base = KnowledgeBase(self.config.get('knowledge_base', {}))
        self.document_processor = DocumentProcessor(self.config.get('document_processor', {}))
        self.content_cleaner = ContentCleaner(self.config.get('content_cleaner', {}))
        
        # Import settings
        self.batch_size = self.config.get('batch_size', 50)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        
        # Progress tracking
        self.import_stats = {
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': []
        }
        
        logger.info("ImportManager initialized")
    
    async def import_jira_issues(
        self,
        issues: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Import Jira issues into knowledge base.
        
        Args:
            issues: List of Jira issue data
            progress_callback: Optional callback for progress updates
            
        Returns:
            Import statistics
        """
        logger.info(f"Starting import of {len(issues)} Jira issues")
        
        # Reset stats
        self.import_stats = {
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Process in batches
        for i in range(0, len(issues), self.batch_size):
            batch = issues[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(issues) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} issues)")
            
            # Process batch
            batch_result = await self._process_jira_batch(batch)
            
            # Update stats
            self.import_stats['total_processed'] += len(batch)
            self.import_stats['successful_imports'] += batch_result['successful']
            self.import_stats['failed_imports'] += batch_result['failed']
            self.import_stats['errors'].extend(batch_result['errors'])
            
            # Progress callback
            if progress_callback:
                progress = (i + len(batch)) / len(issues) * 100
                await self._call_progress_callback(progress_callback, progress, self.import_stats)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Final stats
        self.import_stats['end_time'] = datetime.now(timezone.utc).isoformat()
        self.import_stats['success_rate'] = (
            self.import_stats['successful_imports'] / self.import_stats['total_processed'] * 100
            if self.import_stats['total_processed'] > 0 else 0
        )
        
        logger.info(f"Jira import completed: {self.import_stats['successful_imports']}/{self.import_stats['total_processed']} successful")
        return self.import_stats
    
    async def import_confluence_pages(
        self,
        pages: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Import Confluence pages into knowledge base.
        
        Args:
            pages: List of Confluence page data
            progress_callback: Optional callback for progress updates
            
        Returns:
            Import statistics
        """
        logger.info(f"Starting import of {len(pages)} Confluence pages")
        
        # Reset stats
        self.import_stats = {
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Process in batches
        for i in range(0, len(pages), self.batch_size):
            batch = pages[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(pages) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} pages)")
            
            # Process batch
            batch_result = await self._process_confluence_batch(batch)
            
            # Update stats
            self.import_stats['total_processed'] += len(batch)
            self.import_stats['successful_imports'] += batch_result['successful']
            self.import_stats['failed_imports'] += batch_result['failed']
            self.import_stats['errors'].extend(batch_result['errors'])
            
            # Progress callback
            if progress_callback:
                progress = (i + len(batch)) / len(pages) * 100
                await self._call_progress_callback(progress_callback, progress, self.import_stats)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Final stats
        self.import_stats['end_time'] = datetime.now(timezone.utc).isoformat()
        self.import_stats['success_rate'] = (
            self.import_stats['successful_imports'] / self.import_stats['total_processed'] * 100
            if self.import_stats['total_processed'] > 0 else 0
        )
        
        logger.info(f"Confluence import completed: {self.import_stats['successful_imports']}/{self.import_stats['total_processed']} successful")
        return self.import_stats
    
    async def import_documents(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Import generic documents into knowledge base.
        
        Args:
            documents: List of document dictionaries
            progress_callback: Optional callback for progress updates
            
        Returns:
            Import statistics
        """
        logger.info(f"Starting import of {len(documents)} documents")
        
        # Reset stats
        self.import_stats = {
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Process in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(documents) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Process batch
            batch_result = await self._process_document_batch(batch)
            
            # Update stats
            self.import_stats['total_processed'] += len(batch)
            self.import_stats['successful_imports'] += batch_result['successful']
            self.import_stats['failed_imports'] += batch_result['failed']
            self.import_stats['errors'].extend(batch_result['errors'])
            
            # Progress callback
            if progress_callback:
                progress = (i + len(batch)) / len(documents) * 100
                await self._call_progress_callback(progress_callback, progress, self.import_stats)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Final stats
        self.import_stats['end_time'] = datetime.now(timezone.utc).isoformat()
        self.import_stats['success_rate'] = (
            self.import_stats['successful_imports'] / self.import_stats['total_processed'] * 100
            if self.import_stats['total_processed'] > 0 else 0
        )
        
        logger.info(f"Document import completed: {self.import_stats['successful_imports']}/{self.import_stats['total_processed']} successful")
        return self.import_stats
    
    async def _process_jira_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of Jira issues."""
        result = {'successful': 0, 'failed': 0, 'errors': []}
        
        for issue in batch:
            try:
                # Process issue with retries
                for attempt in range(self.max_retries):
                    try:
                        # Process issue through document processor
                        processed_docs = self.document_processor.process_jira_issue(issue)
                        
                        # Add to knowledge base
                        await self.knowledge_base.add_documents(processed_docs)
                        
                        result['successful'] += 1
                        break
                        
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            error_msg = f"Failed to process issue {issue.get('key', 'unknown')}: {str(e)}"
                            result['errors'].append(error_msg)
                            result['failed'] += 1
                            logger.error(error_msg)
                        else:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            
            except Exception as e:
                error_msg = f"Unexpected error processing issue {issue.get('key', 'unknown')}: {str(e)}"
                result['errors'].append(error_msg)
                result['failed'] += 1
                logger.error(error_msg)
        
        return result
    
    async def _process_confluence_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of Confluence pages."""
        result = {'successful': 0, 'failed': 0, 'errors': []}
        
        for page in batch:
            try:
                # Process page with retries
                for attempt in range(self.max_retries):
                    try:
                        # Clean content
                        content = page.get('content', '')
                        cleaned_content = self.content_cleaner.clean_document(content, 'markdown')
                        
                        # Create document
                        doc = {
                            'content': cleaned_content['cleaned_content'],
                            'metadata': {
                                'source': 'confluence',
                                'source_id': page.get('id', 'unknown'),
                                'title': page.get('title', 'Untitled'),
                                'type': 'page',
                                'space': page.get('space', {}).get('key', 'unknown'),
                                'created_date': page.get('created', ''),
                                'updated_date': page.get('modified', ''),
                                'author': page.get('author', {}).get('displayName', 'unknown'),
                                'content_type': cleaned_content['content_type'],
                                'original_length': cleaned_content['original_length'],
                                'cleaned_length': cleaned_content['cleaned_length']
                            }
                        }
                        
                        # Add to knowledge base
                        await self.knowledge_base.add_documents([doc])
                        
                        result['successful'] += 1
                        break
                        
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            error_msg = f"Failed to process page {page.get('title', 'unknown')}: {str(e)}"
                            result['errors'].append(error_msg)
                            result['failed'] += 1
                            logger.error(error_msg)
                        else:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            
            except Exception as e:
                error_msg = f"Unexpected error processing page {page.get('title', 'unknown')}: {str(e)}"
                result['errors'].append(error_msg)
                result['failed'] += 1
                logger.error(error_msg)
        
        return result
    
    async def _process_document_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of generic documents."""
        result = {'successful': 0, 'failed': 0, 'errors': []}
        
        for doc in batch:
            try:
                # Process document with retries
                for attempt in range(self.max_retries):
                    try:
                        # Clean content if needed
                        content = doc.get('content', '')
                        if doc.get('clean_content', True):
                            cleaned_result = self.content_cleaner.clean_document(content, 'auto')
                            doc['content'] = cleaned_result['cleaned_content']
                            doc['metadata'].update({
                                'content_type': cleaned_result['content_type'],
                                'original_length': cleaned_result['original_length'],
                                'cleaned_length': cleaned_result['cleaned_length']
                            })
                        
                        # Add to knowledge base
                        await self.knowledge_base.add_documents([doc])
                        
                        result['successful'] += 1
                        break
                        
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            error_msg = f"Failed to process document {doc.get('title', 'unknown')}: {str(e)}"
                            result['errors'].append(error_msg)
                            result['failed'] += 1
                            logger.error(error_msg)
                        else:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            
            except Exception as e:
                error_msg = f"Unexpected error processing document {doc.get('title', 'unknown')}: {str(e)}"
                result['errors'].append(error_msg)
                result['failed'] += 1
                logger.error(error_msg)
        
        return result
    
    async def _call_progress_callback(self, callback: Callable, progress: float, stats: Dict[str, Any]):
        """Call progress callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(progress, stats)
            else:
                callback(progress, stats)
        except Exception as e:
            logger.warning(f"Progress callback failed: {e}")
    
    def get_import_history(self) -> List[Dict[str, Any]]:
        """
        Get import history.
        
        Returns:
            List of import records
        """
        # This would typically load from a database or file
        # For now, return current stats
        return [self.import_stats] if self.import_stats.get('start_time') else []
    
    def save_import_report(self, filepath: str) -> bool:
        """
        Save import report to file.
        
        Args:
            filepath: Path to save report
            
        Returns:
            True if successful
        """
        try:
            report = {
                'import_stats': self.import_stats,
                'knowledge_base_stats': self.knowledge_base.get_stats(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Import report saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save import report: {e}")
            return False
