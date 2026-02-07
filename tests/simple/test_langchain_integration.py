#!/usr/bin/env python3
"""Test LangChain integration for EVAgent RAG system."""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_langchain_integration():
    """Test LangChain integration components."""
    print("=== LangChain Integration Test ===\n")
    
    try:
        from src.langchain_integration import (
            ChromaLangChainVectorStore,
            RAGChain,
            LLMManager,
            JiraDocumentLoader,
            ConfluenceDocumentLoader
        )
        from src.database import ChromaManager
        from src.embeddings import EmbeddingService
        
        print("[OK] All LangChain imports successful")
        print()
        
        # Test 1: Vector Store initialization
        print("1. Testing Vector Store initialization...")
        
        db_config = {
            'persist_directory': './storage/test_langchain_db',
            'collection_name': 'test_langchain_docs'
        }
        
        chroma_manager = ChromaManager(db_config)
        
        # Create a mock embedding service for testing
        class MockEmbeddingService:
            async def embed_text(self, texts):
                import numpy as np
                if isinstance(texts, str):
                    texts = [texts]
                # Generate deterministic mock embeddings
                embeddings = []
                for text in texts:
                    np.random.seed(hash(text) % 2**32)
                    emb = np.random.randn(384).astype(np.float32)
                    emb = emb / np.linalg.norm(emb)
                    embeddings.append(emb)
                return np.array(embeddings)
        
        embedding_service = MockEmbeddingService()
        
        vector_store = ChromaLangChainVectorStore(
            chroma_manager=chroma_manager,
            embedding_service=embedding_service
        )
        
        print("   [OK] ChromaLangChainVectorStore initialized")
        print()
        
        # Test 2: Add documents
        print("2. Testing document addition...")
        
        from langchain_core.documents import Document
        
        test_docs = [
            Document(
                page_content="Python is a programming language used for data science.",
                metadata={"source": "test", "title": "Python Guide"}
            ),
            Document(
                page_content="Machine learning enables computers to learn from data.",
                metadata={"source": "test", "title": "ML Basics"}
            ),
            Document(
                page_content="Cloud computing provides scalable infrastructure on demand.",
                metadata={"source": "test", "title": "Cloud Overview"}
            )
        ]
        
        ids = vector_store.add_documents(test_docs)
        print(f"   [OK] Added {len(ids)} documents")
        print()
        
        # Test 3: Similarity search
        print("3. Testing similarity search...")
        
        results = vector_store.similarity_search(
            query="What is Python programming?",
            k=2
        )
        
        print(f"   [OK] Found {len(results)} results")
        for i, doc in enumerate(results, 1):
            title = doc.metadata.get('title', 'N/A')
            sim = doc.metadata.get('similarity', 0)
            print(f"     {i}. {title} (score: {sim:.4f})")
        print()
        
        # Test 4: Search with scores
        print("4. Testing search with scores...")
        
        scored_results = vector_store.similarity_search_with_score(
            query="machine learning and AI",
            k=2
        )
        
        print(f"   [OK] Found {len(scored_results)} scored results")
        for i, (doc, score) in enumerate(scored_results, 1):
            print(f"     {i}. {doc.metadata.get('title', 'N/A')} (score: {score:.4f})")
        print()
        
        # Test 5: Collection stats
        print("5. Testing collection statistics...")
        
        stats = vector_store.get_collection_stats()
        print(f"   [OK] Document count: {stats['document_count']}")
        print()
        
        # Test 6: RAG Chain initialization (without LLM)
        print("6. Testing RAG Chain initialization...")
        
        llm_config = {'provider': 'openai', 'model': 'gpt-3.5-turbo'}
        llm_manager = LLMManager(llm_config)
        
        print("   [OK] LLMManager initialized")
        
        # Note: We can't test actual RAG without API key
        print("   [NOTE] Skipping RAG test (requires OPENAI_API_KEY)")
        print()
        
        # Cleanup
        print("7. Cleaning up...")
        for doc_id in ids:
            chroma_manager.delete_document(doc_id)
        
        final_stats = chroma_manager.get_collection_stats()
        print(f"   [OK] Cleanup complete. Documents: {final_stats['document_count']}")
        print()
        
        print("=" * 50)
        print("SUCCESS: LangChain integration tests passed!")
        print("=" * 50)
        print()
        print("Components verified:")
        print("  - ChromaLangChainVectorStore")
        print("  - Document loading and storage")
        print("  - Similarity search")
        print("  - LLMManager initialization")
        print()
        print("Next steps:")
        print("  1. Set OPENAI_API_KEY environment variable")
        print("  2. Run full RAG test with actual LLM")
        print("  3. Test Jira/Confluence document loaders")
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing LangChain Integration...\n")
    print("Note: This test uses mock embeddings to avoid model download.")
    print("Full functionality requires OPENAI_API_KEY for LLM.\n")
    print("=" * 50)
    print()
    
    success = asyncio.run(test_langchain_integration())
    sys.exit(0 if success else 1)
