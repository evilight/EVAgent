"""Test RAG chain directly"""
import os
import sys
import asyncio
from pathlib import Path

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge.knowledge_base import KnowledgeBase
from langchain_integration.vector_store import ChromaLangChainVectorStore
from langchain_integration.llm_integration import LLMManager
from langchain_integration.rag_chain import RAGChain

async def test_rag_chain():
    print("Testing RAG chain directly...")
    print("=" * 50)
    
    # Setup knowledge base
    kb_config = {
        'persist_directory': 'd:/EVAgent/storage/rag_sample_db',
        'collection_name': 'evagent_sample',
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'chunk_size': 300,
        'chunk_overlap': 30
    }
    
    kb = KnowledgeBase(kb_config)
    print("Knowledge base initialized")
    
    # Setup RAG chain
    llm_manager = LLMManager()
    vector_store = ChromaLangChainVectorStore(
        chroma_manager=kb.chroma_manager,
        embedding_service=kb.embedding_service
    )
    
    rag_chain = RAGChain(
        vector_store=vector_store,
        llm_manager=llm_manager,
        search_k=5,
        similarity_threshold=0.3,  # Lower threshold
        enable_hybrid_search=True,
        enable_query_expansion=True
    )
    
    print(f"RAG chain similarity threshold: {rag_chain.similarity_threshold}")
    
    # Test direct search
    try:
        results = await kb.search("EVAgent architecture", n_results=5)
        print(f"Direct KB search results: {len(results)}")
        for i, result in enumerate(results[:2]):
            print(f"  {i+1}. Score: {result.get('score', 0):.3f}")
    except Exception as e:
        print(f"Direct search error: {e}")
    
    # Test RAG chain
    try:
        # First test vector store directly
        print("\nTesting vector store similarity search...")
        vector_docs = vector_store.similarity_search("EVAgent architecture", k=3)
        print(f"Vector store found {len(vector_docs)} documents:")
        for i, doc in enumerate(vector_docs):
            similarity = doc.metadata.get('similarity', 0.0)
            print(f"  {i+1}. similarity={similarity:.3f}, title={doc.metadata.get('title', 'No title')}")
        
        result = await rag_chain.ask("What are the components of EVAgent system?")
        print(f"\nRAG chain answer: {result.get('answer', '')[:100]}...")
        print(f"RAG chain sources: {len(result.get('sources', []))}")
        
        for i, source in enumerate(result.get('sources', [])[:2]):
            print(f"  Source {i+1}: {source.get('metadata', {}).get('title', 'No title')}")
            
    except Exception as e:
        print(f"RAG chain error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_rag_chain())
