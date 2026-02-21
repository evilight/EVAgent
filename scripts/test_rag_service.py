"""Test RAG service directly"""
import os
import sys
import asyncio
from pathlib import Path

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.services.rag_service import RAGService

async def test_rag_service():
    print("Testing RAG service directly...")
    print("=" * 50)
    
    # Initialize RAG service
    rag_service = RAGService()
    print("RAG service initialized")
    
    # Test search
    try:
        results = await rag_service.search("EVAgent architecture", limit=3)
        print(f"Search results: {len(results)}")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Score: {result.get('score', 0):.3f}")
            print(f"  Content: {result.get('content', '')[:100]}...")
            
    except Exception as e:
        print(f"Search error: {e}")
    
    # Test chat
    try:
        response = await rag_service.ask("What is EVAgent architecture?")
        print(f"\nChat response: {response.get('answer', '')[:200]}...")
        print(f"Sources: {len(response.get('sources', []))}")
        
    except Exception as e:
        print(f"Chat error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_rag_service())
