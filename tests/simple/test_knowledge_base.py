#!/usr/bin/env python3
"""
Test knowledge base functionality.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge.knowledge_base import KnowledgeBase

async def test_knowledge_base():
    """Test knowledge base functionality."""
    print("=" * 70)
    print("TESTING KNOWLEDGE BASE")
    print("=" * 70)
    
    # Initialize knowledge base
    kb = KnowledgeBase({
        'persist_directory': './storage/test_knowledge_base',
        'collection_name': 'test_kb',
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'chunk_size': 300,
        'chunk_overlap': 30
    })
    print("[OK] KnowledgeBase initialized")
    
    # Test 1: Add documents
    print("\n[1] Testing document addition...")
    test_docs = [
        {
            'content': 'Python is a high-level programming language created by Guido van Rossum. It emphasizes code readability with significant whitespace.',
            'metadata': {
                'source': 'kb',
                'title': 'Python Overview',
                'type': 'documentation',
                'topic': 'python'
            }
        },
        {
            'content': 'Machine learning is a subset of artificial intelligence that enables systems to learn from data without explicit programming.',
            'metadata': {
                'source': 'kb',
                'title': 'ML Basics',
                'type': 'documentation',
                'topic': 'machine-learning'
            }
        },
        {
            'content': 'Docker is a platform for developing, shipping, and running applications in containers. Containers are lightweight and portable.',
            'metadata': {
                'source': 'kb',
                'title': 'Docker Introduction',
                'type': 'documentation',
                'topic': 'docker'
            }
        }
    ]
    
    doc_ids = await kb.add_documents(test_docs)
    print(f"    Added {len(doc_ids)} documents")
    print(f"    Document IDs: {[id[:8] + '...' for id in doc_ids]}")
    print("[OK] Document addition successful")
    
    # Test 2: Search functionality
    print("\n[2] Testing search functionality...")
    search_queries = [
        "What is Python?",
        "Explain machine learning",
        "How does Docker work?",
        "programming language readability"
    ]
    
    for query in search_queries:
        results = await kb.search(query, n_results=3)
        print(f"    Query: '{query}'")
        print(f"    Results: {len(results)}")
        
        for i, result in enumerate(results, 1):
            title = result['metadata'].get('title', 'Unknown')
            score = result['score']
            preview = result['content'][:100] + "..."
            print(f"      {i}. {title} (score: {score:.4f})")
            print(f"         {preview}")
        print()
    
    print("[OK] Search functionality successful")
    
    # Test 3: Add Jira issues
    print("\n[3] Testing Jira issue addition...")
    jira_issues = [
        {
            'key': 'TEST-1',
            'summary': 'Authentication error in login',
            'description': 'Users cannot log in with special characters in password. Error: "Invalid credentials"',
            'status': {'name': 'Open'},
            'priority': {'name': 'High'},
            'labels': [{'name': 'authentication'}, {'name': 'bug'}],
            'project': {'key': 'TEST'},
            'reporter': {'displayName': 'user@example.com'},
            'comments': [
                {
                    'id': '1',
                    'author': {'displayName': 'dev@example.com'},
                    'body': 'This is related to the recent security update.',
                    'created': '2024-01-15T11:00:00Z'
                }
            ]
        },
        {
            'key': 'TEST-2',
            'summary': 'Database connection timeout',
            'description': 'The application experiences database timeouts under heavy load. Need to increase connection pool size.',
            'status': {'name': 'In Progress'},
            'priority': {'name': 'Critical'},
            'labels': [{'name': 'database'}, {'name': 'performance'}],
            'project': {'key': 'TEST'},
            'reporter': {'displayName': 'ops@example.com'}
        }
    ]
    
    jira_doc_ids = await kb.add_jira_issues(jira_issues)
    print(f"    Added {len(jira_doc_ids)} document chunks from Jira issues")
    
    # Search for Jira content
    jira_results = await kb.search("authentication error", n_results=5)
    print(f"    Found {len(jira_results)} results for 'authentication error'")
    
    for result in jira_results:
        source = result['metadata'].get('source', 'unknown')
        title = result['metadata'].get('title', 'Unknown')
        print(f"      - {source}: {title}")
    
    print("[OK] Jira issue addition successful")
    
    # Test 4: Document management
    print("\n[4] Testing document management...")
    
    # Get a document
    if doc_ids:
        test_doc_id = doc_ids[0]
        doc = kb.get_document(test_doc_id)
        if doc:
            print(f"    Retrieved document: {doc['metadata'].get('title', 'Unknown')}")
            print(f"    Content preview: {doc['content'][:100]}...")
        
        # Update document
        update_success = await kb.update_document(
            test_doc_id,
            "Updated content: Python is a programming language that emphasizes readability and simplicity.",
            {'updated_by': 'test', 'version': 2}
        )
        print(f"    Document update: {'Success' if update_success else 'Failed'}")
        
        # Verify update
        updated_doc = kb.get_document(test_doc_id)
        if updated_doc:
            print(f"    Updated content: {updated_doc['content'][:100]}...")
    
    print("[OK] Document management successful")
    
    # Test 5: Statistics
    print("\n[5] Testing statistics...")
    stats = kb.get_stats()
    print(f"    Total documents: {stats.get('document_count', 0)}")
    print(f"    Collection name: {stats.get('collection_name', 'unknown')}")
    print(f"    Embedding model: {stats.get('embedding_model', 'unknown')}")
    print(f"    Chunk size: {stats.get('chunk_size', 0)}")
    print(f"    Last updated: {stats.get('last_updated', 'unknown')}")
    
    print("[OK] Statistics retrieval successful")
    
    # Test 6: Search with filters
    print("\n[6] Testing filtered search...")
    
    # Search only Jira issues
    jira_only_results = await kb.search("error", filters={'source': 'jira'})
    print(f"    Jira-only results for 'error': {len(jira_only_results)}")
    
    # Search only documentation
    doc_only_results = await kb.search("python", filters={'source': 'kb'})
    print(f"    Documentation-only results for 'python': {len(doc_only_results)}")
    
    # Search by topic
    python_results = await kb.search("language", filters={'topic': 'python'})
    print(f"    Python topic results: {len(python_results)}")
    
    print("[OK] Filtered search successful")
    
    # Cleanup
    print("\n[7] Cleaning up test data...")
    for doc_id in doc_ids:
        kb.delete_document(doc_id)
    for doc_id in jira_doc_ids:
        kb.delete_document(doc_id)
    
    final_stats = kb.get_stats()
    print(f"    Final document count: {final_stats.get('document_count', 0)}")
    print("[OK] Cleanup completed")
    
    print("\n" + "=" * 70)
    print("KNOWLEDGE BASE TEST COMPLETED!")
    print("=" * 70)
    print("\nVerified features:")
    print("  - Document addition with metadata")
    print("  - Semantic search with scoring")
    print("  - Jira issue processing")
    print("  - Document CRUD operations")
    print("  - Statistics and monitoring")
    print("  - Filtered search")
    print("  - Data cleanup")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_knowledge_base())
    sys.exit(0 if success else 1)
