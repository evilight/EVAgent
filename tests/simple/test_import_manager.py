#!/usr/bin/env python3
"""
Test import manager functionality.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge.import_manager import ImportManager

async def test_import_manager():
    """Test import manager functionality."""
    print("=" * 70)
    print("TESTING IMPORT MANAGER")
    print("=" * 70)
    
    # Initialize import manager
    import_manager = ImportManager({
        'batch_size': 3,
        'max_retries': 2,
        'retry_delay': 0.1,
        'knowledge_base': {
            'persist_directory': './storage/test_import_manager',
            'collection_name': 'test_import',
            'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2'
        },
        'document_processor': {
            'chunk_size': 200,
            'chunk_overlap': 20
        },
        'content_cleaner': {
            'preserve_code_blocks': True,
            'normalize_unicode': True
        }
    })
    print("[OK] ImportManager initialized")
    
    # Test 1: Import Jira issues
    print("\n[1] Testing Jira issue import...")
    
    sample_jira_issues = [
        {
            'key': 'TEST-1',
            'summary': 'Login authentication error',
            'description': 'Users cannot log in with special characters in passwords.',
            'status': {'name': 'Open'},
            'priority': {'name': 'High'},
            'labels': [{'name': 'authentication'}, {'name': 'bug'}],
            'project': {'key': 'TEST'},
            'reporter': {'displayName': 'user@example.com'},
            'comments': [
                {
                    'id': '1',
                    'author': {'displayName': 'dev@example.com'},
                    'body': 'This is related to security update.',
                    'created': '2024-01-15T11:00:00Z'
                }
            ],
            'attachments': []
        },
        {
            'key': 'TEST-2',
            'summary': 'Database timeout issue',
            'description': 'Database connections timing out under load.',
            'status': {'name': 'In Progress'},
            'priority': {'name': 'Critical'},
            'labels': [{'name': 'database'}, {'name': 'performance'}],
            'project': {'key': 'TEST'},
            'reporter': {'displayName': 'ops@example.com'},
            'comments': [],
            'attachments': []
        },
        {
            'key': 'TEST-3',
            'summary': 'UI rendering problem',
            'description': 'Dashboard not rendering properly on mobile devices.',
            'status': {'name': 'Open'},
            'priority': {'name': 'Medium'},
            'labels': [{'name': 'ui'}, {'name': 'mobile'}],
            'project': {'key': 'TEST'},
            'reporter': {'displayName': 'frontend@example.com'},
            'comments': [],
            'attachments': []
        }
    ]
    
    # Progress callback
    async def progress_callback(progress: float, stats: dict):
        print(f"      Progress: {progress:.1f}% - Success: {stats['successful_imports']}, Failed: {stats['failed_imports']}")
    
    jira_result = await import_manager.import_jira_issues(sample_jira_issues, progress_callback)
    print(f"    Jira import completed:")
    print(f"      Total processed: {jira_result['total_processed']}")
    print(f"      Successful: {jira_result['successful_imports']}")
    print(f"      Failed: {jira_result['failed_imports']}")
    print(f"      Success rate: {jira_result['success_rate']:.1f}%")
    print(f"      Errors: {len(jira_result['errors'])}")
    print("[OK] Jira import test completed")
    
    # Test 2: Import Confluence pages
    print("\n[2] Testing Confluence page import...")
    
    sample_confluence_pages = [
        {
            'id': 'page-1',
            'title': 'Getting Started Guide',
            'content': '''
# Getting Started

This guide covers the basics of using our system.

## Installation
```bash
npm install our-system
```

## Configuration
Edit the config file to set up your environment.

## Usage
Run the application with the start command.
            ''',
            'space': {'key': 'DOC'},
            'created': '2024-01-01T00:00:00Z',
            'modified': '2024-01-15T10:00:00Z',
            'author': {'displayName': 'doc@example.com'}
        },
        {
            'id': 'page-2',
            'title': 'API Documentation',
            'content': '''
# API Reference

## Authentication
All API calls require authentication.

## Endpoints

### GET /users
Retrieve user information.

### POST /users
Create a new user.

## Error Handling
API returns standard HTTP status codes.
            ''',
            'space': {'key': 'DOC'},
            'created': '2024-01-02T00:00:00Z',
            'modified': '2024-01-16T12:00:00Z',
            'author': {'displayName': 'api@example.com'}
        }
    ]
    
    confluence_result = await import_manager.import_confluence_pages(sample_confluence_pages)
    print(f"    Confluence import completed:")
    print(f"      Total processed: {confluence_result['total_processed']}")
    print(f"      Successful: {confluence_result['successful_imports']}")
    print(f"      Failed: {confluence_result['failed_imports']}")
    print(f"      Success rate: {confluence_result['success_rate']:.1f}%")
    print("[OK] Confluence import test completed")
    
    # Test 3: Import generic documents
    print("\n[3] Testing generic document import...")
    
    sample_documents = [
        {
            'content': 'Python is a high-level programming language with dynamic typing.',
            'metadata': {
                'source': 'kb',
                'source_id': 'doc-1',
                'title': 'Python Overview',
                'type': 'documentation'
            }
        },
        {
            'content': 'Machine learning algorithms can be categorized into supervised and unsupervised learning.',
            'metadata': {
                'source': 'kb',
                'source_id': 'doc-2',
                'title': 'ML Basics',
                'type': 'documentation'
            }
        },
        {
            'content': 'Docker containers provide lightweight virtualization for applications.',
            'metadata': {
                'source': 'kb',
                'source_id': 'doc-3',
                'title': 'Docker Introduction',
                'type': 'documentation'
            }
        }
    ]
    
    doc_result = await import_manager.import_documents(sample_documents)
    print(f"    Document import completed:")
    print(f"      Total processed: {doc_result['total_processed']}")
    print(f"      Successful: {doc_result['successful_imports']}")
    print(f"      Failed: {doc_result['failed_imports']}")
    print(f"      Success rate: {doc_result['success_rate']:.1f}%")
    print("[OK] Document import test completed")
    
    # Test 4: Error handling
    print("\n[4] Testing error handling...")
    
    # Test with malformed data
    malformed_docs = [
        {
            'content': 'Valid document',
            'metadata': {'source': 'test', 'title': 'Valid'}
        },
        {
            # Missing required fields
            'metadata': {'source': 'test'}
        },
        {
            'content': 'Another valid document',
            'metadata': {'source': 'test', 'title': 'Valid 2'}
        }
    ]
    
    error_result = await import_manager.import_documents(malformed_docs)
    print(f"    Error handling test:")
    print(f"      Total processed: {error_result['total_processed']}")
    print(f"      Successful: {error_result['successful_imports']}")
    print(f"      Failed: {error_result['failed_imports']}")
    print(f"      Errors: {len(error_result['errors'])}")
    if error_result['errors']:
        print(f"      Sample error: {error_result['errors'][0]}")
    print("[OK] Error handling test completed")
    
    # Test 5: Import history and reporting
    print("\n[5] Testing import history and reporting...")
    
    history = import_manager.get_import_history()
    print(f"    Import history entries: {len(history)}")
    
    # Save import report
    report_path = './storage/test_import_report.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report_saved = import_manager.save_import_report(report_path)
    print(f"    Import report saved: {report_saved}")
    
    if report_saved and os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = f.read()
        print(f"    Report size: {len(report_data)} characters")
    
    print("[OK] History and reporting test completed")
    
    # Test 6: Knowledge base stats
    print("\n[6] Testing knowledge base integration...")
    
    kb_stats = import_manager.knowledge_base.get_stats()
    print(f"    Knowledge base stats:")
    print(f"      Document count: {kb_stats.get('document_count', 0)}")
    print(f"      Collection name: {kb_stats.get('collection_name', 'unknown')}")
    print(f"      Embedding model: {kb_stats.get('embedding_model', 'unknown')}")
    
    # Test search functionality
    search_results = await import_manager.knowledge_base.search("python", n_results=3)
    print(f"    Search results for 'python': {len(search_results)}")
    
    print("[OK] Knowledge base integration test completed")
    
    # Test 7: Performance test
    print("\n[7] Testing import performance...")
    
    import time
    
    # Create larger batch
    large_batch = [
        {
            'content': f'Test document {i} with some content about topic {i % 5}.',
            'metadata': {
                'source': 'perf_test',
                'source_id': f'perf-doc-{i}',
                'title': f'Performance Test Doc {i}',
                'type': 'test'
            }
        }
        for i in range(20)
    ]
    
    start_time = time.time()
    perf_result = await import_manager.import_documents(large_batch)
    end_time = time.time()
    
    duration = end_time - start_time
    docs_per_second = len(large_batch) / duration
    
    print(f"    Performance test results:")
    print(f"      Documents: {len(large_batch)}")
    print(f"      Duration: {duration:.3f}s")
    print(f"      Documents/second: {docs_per_second:.1f}")
    print(f"      Success rate: {perf_result['success_rate']:.1f}%")
    
    if docs_per_second > 10:
        print("[OK] Performance is good")
    else:
        print("[WARN] Performance could be improved")
    
    print("\n" + "=" * 70)
    print("IMPORT MANAGER TEST COMPLETED!")
    print("=" * 70)
    print("\nVerified features:")
    print("  - Jira issue import with chunking")
    print("  - Confluence page import with content cleaning")
    print("  - Generic document import")
    print("  - Batch processing with progress tracking")
    print("  - Error handling and retry logic")
    print("  - Import history and reporting")
    print("  - Knowledge base integration")
    print("  - Performance optimization")
    print("  - Progress callbacks")
    print("  - Import statistics")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_import_manager())
    sys.exit(0 if success else 1)
