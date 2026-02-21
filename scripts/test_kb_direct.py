"""Test knowledge base directly"""
import os
import sys
import asyncio
from pathlib import Path

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge.knowledge_base import KnowledgeBase

async def test_kb_directly():
    print("Testing knowledge base directly...")
    print("=" * 50)
    
    # Setup knowledge base with same config as API
    kb_config = {
        'persist_directory': './storage/rag_sample_db',
        'collection_name': 'evagent_sample',
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'chunk_size': 300,
        'chunk_overlap': 30
    }
    
    kb = KnowledgeBase(kb_config)
    print("Knowledge base initialized")
    
    # Get stats
    stats = kb.get_stats()
    print(f"Document count: {stats.get('document_count', 0)}")
    print(f"Collection: {stats.get('collection_name', 'Unknown')}")
    
    # Test search
    try:
        results = await kb.search("EVAgent architecture", n_results=3)
        print(f"\nSearch results for 'EVAgent architecture': {len(results)}")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Score: {result.get('score', 0):.3f}")
            print(f"  Content: {result.get('content', '')[:100]}...")
            print(f"  Source: {result.get('metadata', {}).get('source', 'Unknown')}")
            print(f"  Title: {result.get('metadata', {}).get('title', 'No title')}")
            
    except Exception as e:
        print(f"Search error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_kb_directly())
