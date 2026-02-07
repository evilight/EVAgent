#!/usr/bin/env python3
"""Test end-to-end Vector Search workflow with mock embeddings."""

import os
import sys
import asyncio
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def generate_mock_embedding(text, dim=384):
    """Generate a deterministic mock embedding based on text content."""
    # Use hash of text to seed random for deterministic results
    np.random.seed(hash(text) % 2**32)
    embedding = np.random.randn(dim).astype(np.float32)
    # Normalize
    embedding = embedding / np.linalg.norm(embedding)
    return embedding


async def test_vector_search_workflow():
    """Test complete vector search workflow with mock embeddings."""
    print("=== Vector Search Workflow Test ===\n")
    
    try:
        from src.database import ChromaManager
        
        # Configuration
        db_config = {
            'persist_directory': './storage/test_search_db',
            'collection_name': 'search_test_docs',
            'file_collection_name': 'search_test_files'
        }
        
        # Initialize ChromaDB
        print("1. Initializing ChromaDB...")
        chroma = ChromaManager(db_config)
        print("   [OK] ChromaManager ready")
        print()
        
        # Test documents about various topics
        test_documents = [
            {
                'id': 'doc_001',
                'content': '''Python is a high-level programming language known for its simplicity.
                It is widely used in data science, machine learning, and web development.
                Python has a large ecosystem of libraries like NumPy, Pandas, and TensorFlow.''',
                'metadata': {
                    'source': 'test',
                    'source_id': 'DOC-001',
                    'title': 'Python Programming Guide',
                    'type': 'documentation',
                    'category': 'programming',
                    'tags': ['python', 'programming', 'tutorial']
                }
            },
            {
                'id': 'doc_002',
                'content': '''JavaScript is the language of the web. It runs in browsers and servers
                through Node.js. Modern JavaScript frameworks include React, Vue, and Angular.
                It is essential for front-end development and full-stack applications.''',
                'metadata': {
                    'source': 'test',
                    'source_id': 'DOC-002',
                    'title': 'JavaScript Basics',
                    'type': 'documentation',
                    'category': 'programming',
                    'tags': ['javascript', 'web', 'frontend']
                }
            },
            {
                'id': 'doc_003',
                'content': '''Machine learning is a subset of artificial intelligence that enables
                computers to learn from data without explicit programming. Common algorithms
                include neural networks, decision trees, and support vector machines.''',
                'metadata': {
                    'source': 'test',
                    'source_id': 'DOC-003',
                    'title': 'Machine Learning Introduction',
                    'type': 'documentation',
                    'category': 'ai',
                    'tags': ['machine learning', 'ai', 'data science']
                }
            },
            {
                'id': 'doc_004',
                'content': '''Docker is a platform for containerizing applications. It ensures consistency
                across development and production environments. Containers are lightweight
                and efficient compared to virtual machines.''',
                'metadata': {
                    'source': 'test',
                    'source_id': 'DOC-004',
                    'title': 'Docker Containerization',
                    'type': 'documentation',
                    'category': 'devops',
                    'tags': ['docker', 'containers', 'devops']
                }
            },
            {
                'id': 'doc_005',
                'content': '''Cloud computing provides on-demand computing resources over the internet.
                Major providers include AWS, Azure, and Google Cloud Platform. It offers
                scalability, reliability, and cost-efficiency for modern applications.''',
                'metadata': {
                    'source': 'test',
                    'source_id': 'DOC-005',
                    'title': 'Cloud Computing Overview',
                    'type': 'documentation',
                    'category': 'cloud',
                    'tags': ['cloud', 'aws', 'infrastructure']
                }
            }
        ]
        
        # Generate embeddings and add to database
        print("2. Generating embeddings and adding documents...")
        docs_with_embeddings = []
        
        for doc in test_documents:
            # Generate deterministic mock embedding
            embedding = generate_mock_embedding(doc['content'])
            
            docs_with_embeddings.append({
                'id': doc['id'],
                'content': doc['content'],
                'embedding': embedding,
                'metadata': doc['metadata']
            })
            print(f"   [OK] Generated embedding for: {doc['metadata']['title']}")
        
        # Add to database
        doc_ids = chroma.add_documents_batch(docs_with_embeddings)
        print(f"   [OK] Added {len(doc_ids)} documents to vector database")
        print()
        
        # Perform semantic searches
        print("3. Testing semantic searches...")
        print()
        
        # Search 1: Python-related query
        print("   Search 1: 'Python programming language'")
        query1 = "Tell me about Python programming language"
        query_embedding1 = generate_mock_embedding(query1)
        results1 = chroma.search(
            query_embedding=query_embedding1,
            n_results=3,
            include=['metadatas', 'documents', 'distances']
        )
        print("   Top results:")
        for i, doc_id in enumerate(results1['ids']):
            title = results1['metadatas'][i].get('title', 'N/A') if i < len(results1['metadatas']) else 'N/A'
            sim = results1['similarities'][i] if i < len(results1['similarities']) else 0
            print(f"     {i+1}. {title} (score: {sim:.4f})")
        print()
        
        # Search 2: AI/Machine Learning query
        print("   Search 2: 'artificial intelligence and ML'")
        query2 = "What is artificial intelligence and machine learning?"
        query_embedding2 = generate_mock_embedding(query2)
        results2 = chroma.search(
            query_embedding=query_embedding2,
            n_results=3,
            include=['metadatas', 'documents', 'distances']
        )
        print("   Top results:")
        for i, doc_id in enumerate(results2['ids']):
            title = results2['metadatas'][i].get('title', 'N/A') if i < len(results2['metadatas']) else 'N/A'
            sim = results2['similarities'][i] if i < len(results2['similarities']) else 0
            print(f"     {i+1}. {title} (score: {sim:.4f})")
        print()
        
        # Search 3: With metadata filter
        print("   Search 3: 'programming languages' (filtered by category='programming')")
        query3 = "programming languages"
        query_embedding3 = generate_mock_embedding(query3)
        results3 = chroma.search(
            query_embedding=query_embedding3,
            n_results=10,
            where={'category': 'programming'},
            include=['metadatas', 'documents', 'distances']
        )
        print(f"   Found {len(results3['ids'])} documents in 'programming' category:")
        for i, doc_id in enumerate(results3['ids']):
            title = results3['metadatas'][i].get('title', 'N/A') if i < len(results3['metadatas']) else 'N/A'
            cat = results3['metadatas'][i].get('category', 'N/A') if i < len(results3['metadatas']) else 'N/A'
            sim = results3['similarities'][i] if i < len(results3['similarities']) else 0
            print(f"     {i+1}. {title} (category: {cat}, score: {sim:.4f})")
        print()
        
        # Get database stats
        print("4. Final database statistics...")
        stats = chroma.get_collection_stats()
        print(f"   Document count: {stats['document_count']}")
        print(f"   File count: {stats['file_count']}")
        print(f"   Collection: {stats['collection_name']}")
        print()
        
        # Cleanup
        print("5. Cleaning up...")
        for doc_id in doc_ids:
            chroma.delete_document(doc_id)
        
        final_stats = chroma.get_collection_stats()
        print(f"   [OK] Cleaned up. Final count: {final_stats['document_count']}")
        print()
        
        print("=" * 50)
        print("SUCCESS: All Vector Search Workflow tests passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_vector_search_workflow())
    sys.exit(0 if success else 1)
