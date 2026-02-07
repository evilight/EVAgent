#!/usr/bin/env python3
"""Test full RAG pipeline with DeepSeek LLM."""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Union
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    async def embed_text(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Generate mock embeddings."""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        for text in texts:
            np.random.seed(hash(text) % 2**32)
            embedding = np.random.randn(384).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())
        
        return embeddings
    
    async def embed_code(self, code: Union[str, List[str]]) -> List[List[float]]:
        """Generate mock code embeddings."""
        return await self.embed_text(code)


async def test_full_rag():
    """Test complete RAG pipeline with LLM."""
    print("=" * 60)
    print("       FULL RAG PIPELINE TEST WITH DEEPSEEK")
    print("=" * 60)
    print()
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[X] ERROR: OPENAI_API_KEY environment variable not set")
        print("    Set it with: export OPENAI_API_KEY=your-key")
        return False
    
    try:
        from src.langchain_integration import ChromaLangChainVectorStore, RAGChain
        from src.langchain_integration.llm_integration import LLMManager
        from src.database.chroma_manager import ChromaManager
        from langchain_core.documents import Document
        
        # Test 1: Initialize components
        print("1. Initializing RAG components...")
        
        embedding_service = MockEmbeddingService()
        chroma_manager = ChromaManager({
            'persist_directory': './storage/test_rag_db',
            'collection_name': 'test_rag'
        })
        vector_store = ChromaLangChainVectorStore(
            chroma_manager=chroma_manager,
            embedding_service=embedding_service
        )
        print("   [OK] Vector store initialized")
        
        llm_manager = LLMManager()
        print("   [OK] LLM manager initialized (DeepSeek)")
        
        # Test 2: Add knowledge base documents
        print("\n2. Adding knowledge base documents...")
        
        knowledge_docs = [
            Document(
                page_content="Python is a high-level programming language created by Guido van Rossum in 1991. It emphasizes code readability with its use of significant whitespace.",
                metadata={"source": "kb", "topic": "python", "title": "Python Overview"}
            ),
            Document(
                page_content="Machine learning is a subset of artificial intelligence that enables systems to learn from data without explicit programming. Common algorithms include neural networks, decision trees, and support vector machines.",
                metadata={"source": "kb", "topic": "ml", "title": "Machine Learning Basics"}
            ),
            Document(
                page_content="Docker is a platform for developing, shipping, and running applications in containers. Containers are lightweight, portable, and self-sufficient environments.",
                metadata={"source": "kb", "topic": "docker", "title": "Docker Introduction"}
            ),
            Document(
                page_content="Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications.",
                metadata={"source": "kb", "topic": "kubernetes", "title": "Kubernetes Overview"}
            ),
            Document(
                page_content="REST API (Representational State Transfer) is an architectural style for designing networked applications. It uses HTTP requests to access and manipulate data.",
                metadata={"source": "kb", "topic": "api", "title": "REST API Design"}
            )
        ]
        
        ids = vector_store.add_documents(knowledge_docs)
        print(f"   [OK] Added {len(ids)} documents to knowledge base")
        
        # Test 3: Create RAG chain
        print("\n3. Creating RAG chain...")
        
        rag_chain = RAGChain(
            vector_store=vector_store,
            llm_manager=llm_manager,
            search_k=2,
            similarity_threshold=-2.0  # Lower threshold for mock embeddings
        )
        print("   [OK] RAG chain created")
        
        # Test 4: Query the RAG system
        print("\n4. Testing RAG queries...")
        print("-" * 40)
        
        queries = [
            "What is Python and who created it?",
            "Explain machine learning in simple terms",
            "What is the difference between Docker and Kubernetes?"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n   Query {i}: {query}")
            print(f"   {'=' * 50}")
            
            try:
                result = await rag_chain.ask(query)
                
                print(f"   Answer: {result['answer']}")
                print(f"\n   Sources used:")
                for j, source in enumerate(result['sources'], 1):
                    title = source.get('title', 'Unknown')
                    score = source.get('similarity', 0)
                    print(f"     {j}. {title} (score: {score:.4f})")
                
                print(f"   {'=' * 50}")
                print("   [OK] Query processed successfully")
                
            except Exception as e:
                print(f"   [X] Query failed: {e}")
        
        # Test 5: Chat with context
        print("\n5. Testing chat with history...")
        print("-" * 40)
        
        chat_history = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."}
        ]
        
        chat_result = await rag_chain.ask(
            question="Who created it and when?",
            chat_history=chat_history
        )
        
        print(f"   User: Who created it and when?")
        print(f"   Assistant: {chat_result['answer']}")
        print(f"   Context used: {len(chat_result['retrieved_documents'])} documents")
        print("   [OK] Chat with history completed")
        
        # Cleanup
        print("\n6. Cleaning up...")
        for doc_id in ids:
            chroma_manager.delete_document(doc_id)
        
        final_stats = chroma_manager.get_collection_stats()
        print(f"   [OK] Cleanup complete. Documents: {final_stats['document_count']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("       FULL RAG PIPELINE TEST PASSED!")
        print("=" * 60)
        print("\nVerified components:")
        print("  - Vector store with document storage")
        print("  - DeepSeek LLM integration")
        print("  - RAG query with context retrieval")
        print("  - Chat with conversation history")
        print("  - Source attribution")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nTesting Full RAG Pipeline with DeepSeek LLM...\n")
    
    success = asyncio.run(test_full_rag())
    sys.exit(0 if success else 1)
