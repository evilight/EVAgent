#!/usr/bin/env python3
"""Test Vector Database (ChromaDB) functionality."""

import os
import sys
import asyncio
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_chroma_manager():
    """Test ChromaDB manager operations."""
    print("=== Vector Database Test ===\n")
    
    try:
        from src.database import ChromaManager
        
        # Configuration
        config = {
            'persist_directory': './storage/test_chroma_db',
            'collection_name': 'test_documents',
            'file_collection_name': 'test_files'
        }
        
        print("1. Initializing ChromaDB...")
        chroma = ChromaManager(config)
        print("   [OK] ChromaDB initialized")
        
        # Get stats
        stats = chroma.get_collection_stats()
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Initial document count: {stats['document_count']}")
        print()
        
        # Add test documents
        print("2. Adding test documents...")
        
        test_docs = [
            {
                'content': 'This is a test document about Python programming.',
                'embedding': np.random.randn(384).astype(np.float32),
                'metadata': {
                    'source': 'test',
                    'source_id': 'TEST-001',
                    'title': 'Python Programming',
                    'type': 'test_doc',
                    'project': 'TEST'
                }
            },
            {
                'content': 'Another document about machine learning and AI.',
                'embedding': np.random.randn(384).astype(np.float32),
                'metadata': {
                    'source': 'test',
                    'source_id': 'TEST-002',
                    'title': 'Machine Learning',
                    'type': 'test_doc',
                    'project': 'TEST'
                }
            },
            {
                'content': 'Document about web development with JavaScript.',
                'embedding': np.random.randn(384).astype(np.float32),
                'metadata': {
                    'source': 'test',
                    'source_id': 'TEST-003',
                    'title': 'Web Development',
                    'type': 'test_doc',
                    'project': 'WEB'
                }
            }
        ]
        
        doc_ids = chroma.add_documents_batch(test_docs)
        print(f"   [OK] Added {len(doc_ids)} documents")
        for doc_id in doc_ids:
            print(f"     - {doc_id}")
        print()
        
        # Verify documents added
        stats = chroma.get_collection_stats()
        print(f"3. Document count after add: {stats['document_count']}")
        print()
        
        # Test retrieval
        print("4. Testing document retrieval...")
        retrieved = chroma.get_document_by_id(doc_ids[0])
        if retrieved:
            print(f"   [OK] Retrieved document {doc_ids[0][:8]}...")
            print(f"     Title: {retrieved['metadata'].get('title', 'N/A')}")
            print(f"     Content: {retrieved['content'][:50]}...")
        print()
        
        # Test search
        print("5. Testing similarity search...")
        query_embedding = np.random.randn(384).astype(np.float32)
        results = chroma.search(
            query_embedding=query_embedding,
            n_results=2,
            include=['metadatas', 'documents', 'distances']
        )
        print(f"   [OK] Search returned {len(results['ids'])} results")
        for i, doc_id in enumerate(results['ids']):
            similarity = results['similarities'][i] if i < len(results['similarities']) else 0
            title = results['metadatas'][i].get('title', 'N/A') if i < len(results['metadatas']) else 'N/A'
            print(f"     - {title} (similarity: {similarity:.4f})")
        print()
        
        # Test metadata filtering
        print("6. Testing metadata filtering...")
        filtered_results = chroma.search(
            query_embedding=query_embedding,
            n_results=10,
            where={'project': 'TEST'},
            include=['metadatas']
        )
        test_project_count = len(filtered_results['ids'])
        print(f"   [OK] Found {test_project_count} documents with project='TEST'")
        print()
        
        # Test update
        print("7. Testing document update...")
        updated = chroma.update_document(
            doc_ids[0],
            content="Updated content about Python and data science.",
            metadata={
                'source': 'test',
                'source_id': 'TEST-001',
                'title': 'Python Data Science',
                'type': 'test_doc',
                'project': 'TEST',
                'status': 'updated'
            }
        )
        print(f"   [OK] Document updated: {updated}")
        print()
        
        # Test delete
        print("8. Testing document deletion...")
        deleted = chroma.delete_document(doc_ids[2])
        print(f"   [OK] Document deleted: {deleted}")
        
        stats = chroma.get_collection_stats()
        print(f"   Document count after delete: {stats['document_count']}")
        print()
        
        # Cleanup
        print("9. Cleaning up...")
        for doc_id in doc_ids[:2]:  # Delete remaining docs
            chroma.delete_document(doc_id)
        
        final_stats = chroma.get_collection_stats()
        print(f"   [OK] Final document count: {final_stats['document_count']}")
        print()
        
        print("=" * 50)
        print("SUCCESS: All Vector Database tests passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chroma_manager())
    sys.exit(0 if success else 1)
