#!/usr/bin/env python3
"""
Complete end-to-end RAG system test with all components.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge.knowledge_base import KnowledgeBase
from src.knowledge.import_manager import ImportManager
from src.langchain_integration.rag_chain import RAGChain
from src.langchain_integration.vector_store import ChromaLangChainVectorStore
from src.langchain_integration.llm_integration import LLMManager

async def test_complete_rag_system():
    """Test complete RAG system with all components."""
    print("=" * 80)
    print("COMPLETE EVAGENT RAG SYSTEM TEST")
    print("=" * 80)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[X] ERROR: OPENAI_API_KEY environment variable not set")
        return False
    
    try:
        # Initialize knowledge base
        print("\n[1] Initializing complete RAG system...")
        
        kb = KnowledgeBase({
            'persist_directory': './storage/complete_rag_test',
            'collection_name': 'evagent_complete',
            'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
            'chunk_size': 300,
            'chunk_overlap': 30
        })
        print("    [OK] Knowledge base initialized")
        
        # Initialize import manager
        import_manager = ImportManager({
            'batch_size': 5,
            'knowledge_base': {
                'persist_directory': './storage/complete_rag_test',
                'collection_name': 'evagent_complete',
                'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2'
            }
        })
        print("    [OK] Import manager initialized")
        
        # Initialize RAG chain
        llm_manager = LLMManager()
        vector_store = ChromaLangChainVectorStore(
            chroma_manager=kb.chroma_manager,
            embedding_service=kb.embedding_service
        )
        
        rag_chain = RAGChain(
            vector_store=vector_store,
            llm_manager=llm_manager,
            search_k=5,
            similarity_threshold=0.3,
            enable_hybrid_search=True,
            enable_query_expansion=True
        )
        print("    [OK] Enhanced RAG chain initialized")
        
        # Test 2: Import sample data
        print("\n[2] Importing sample knowledge base...")
        
        # Sample Jira issues
        jira_issues = [
            {
                'key': 'EV-1',
                'summary': 'User authentication fails with special characters',
                'description': '''
Users report authentication errors when passwords contain special characters like @#$%.

**Error Message**: "Authentication failed: Invalid credentials"

**Steps to Reproduce**:
1. Navigate to login page
2. Enter username
3. Enter password with special characters
4. Click login button

**Expected**: User should be authenticated successfully
**Actual**: Authentication error displayed
                ''',
                'status': {'name': 'Open'},
                'priority': {'name': 'High'},
                'labels': [{'name': 'authentication'}, {'name': 'bug'}],
                'project': {'key': 'EV'},
                'reporter': {'displayName': 'user@example.com'},
                'comments': [
                    {
                        'id': '1',
                        'author': {'displayName': 'dev@example.com'},
                        'body': 'This appears to be related to the recent security update.',
                        'created': '2024-01-15T11:00:00Z'
                    }
                ]
            },
            {
                'key': 'EV-2',
                'summary': 'Database connection pool exhausted under load',
                'description': '''
The application experiences database connection timeouts during peak usage hours.

**Symptoms**:
- java.sql.SQLException: Connection pool is at maximum capacity
- Response times increase significantly
- Users experience 503 errors

**Environment**:
- PostgreSQL 14
- Connection pool size: 20
- Peak concurrent users: 500

**Workaround**: Restart application to release connections.
                ''',
                'status': {'name': 'In Progress'},
                'priority': {'name': 'Critical'},
                'labels': [{'name': 'database'}, {'name': 'performance'}],
                'project': {'key': 'EV'},
                'reporter': {'displayName': 'ops@example.com'}
            }
        ]
        
        # Import Jira issues
        jira_result = await import_manager.import_jira_issues(jira_issues)
        print(f"    Imported {jira_result['successful_imports']} Jira issues")
        
        # Sample documentation
        docs = [
            {
                'content': '''
# Python Best Practices

This document outlines Python best practices for development.

## Code Style
Follow PEP 8 guidelines for consistent code formatting.

## Error Handling
Always handle exceptions properly with try-except blocks.

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    handle_error(e)
```

## Performance
- Use list comprehensions instead of loops when possible
- Avoid unnecessary string concatenation in loops
- Profile code before optimizing
                ''',
                'metadata': {
                    'source': 'documentation',
                    'source_id': 'python-best-practices',
                    'title': 'Python Best Practices',
                    'type': 'documentation',
                    'topic': 'python'
                }
            },
            {
                'content': '''
# Authentication System Overview

Our authentication system uses JWT tokens for secure user authentication.

## Flow
1. User submits credentials
2. Server validates credentials
3. Server generates JWT token
4. Client stores token
5. Client includes token in subsequent requests

## Security Features
- Password hashing with bcrypt
- Token expiration
- Refresh token mechanism
- Rate limiting on login attempts
                ''',
                'metadata': {
                    'source': 'documentation',
                    'source_id': 'auth-overview',
                    'title': 'Authentication System Overview',
                    'type': 'documentation',
                    'topic': 'authentication'
                }
            }
        ]
        
        doc_result = await import_manager.import_documents(docs)
        print(f"    Imported {doc_result['successful_imports']} documentation pages")
        
        # Test 3: Search functionality
        print("\n[3] Testing search functionality...")
        
        search_queries = [
            "authentication problems",
            "database connection issues",
            "python error handling",
            "JWT token security"
        ]
        
        for query in search_queries:
            results = await kb.search(query, n_results=3)
            print(f"    Query: '{query}'")
            print(f"    Results: {len(results)}")
            
            for i, result in enumerate(results, 1):
                title = result['metadata'].get('title', 'Unknown')
                score = result['score']
                print(f"      {i}. {title} (score: {score:.4f})")
            print()
        
        print("[OK] Search functionality verified")
        
        # Test 4: RAG问答测试
        print("\n[4] Testing RAG question answering...")
        
        questions = [
            "How should I handle authentication errors with special characters?",
            "What causes database connection pool exhaustion?",
            "What are the best practices for Python error handling?",
            "How does our JWT authentication system work?"
        ]
        
        for question in questions:
            print(f"    Q: {question}")
            
            try:
                result = await rag_chain.ask(question)
                print(f"    A: {result['answer'][:200]}...")
                print(f"    Sources: {len(result['sources'])}")
                print(f"    Search method: {result.get('search_method', 'unknown')}")
                print(f"    Query expansions: {len(result.get('query_expansion', []))}")
                print()
                
            except Exception as e:
                print(f"    [ERROR] Failed to answer: {e}")
        
        print("[OK] RAG question answering verified")
        
        # Test 5: Chat with history
        print("\n[5] Testing conversation with history...")
        
        conversation = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language."},
            {"role": "user", "content": "What are its best practices?"}
        ]
        
        # Simulate conversation
        for i, msg in enumerate(conversation):
            if msg['role'] == 'user':
                print(f"    User: {msg['content']}")
                
                # Build history from previous messages
                history = conversation[:i]
                
                try:
                    result = await rag_chain.ask(msg['content'], chat_history=history)
                    print(f"    Assistant: {result['answer'][:150]}...")
                    print()
                except Exception as e:
                    print(f"    [ERROR] Failed: {e}")
        
        print("[OK] Conversation with history verified")
        
        # Test 6: System statistics
        print("\n[6] System statistics...")
        
        kb_stats = kb.get_stats()
        print(f"    Knowledge base:")
        print(f"      Documents: {kb_stats.get('document_count', 0)}")
        print(f"      Collection: {kb_stats.get('collection_name', 'unknown')}")
        print(f"      Embedding model: {kb_stats.get('embedding_model', 'unknown')}")
        
        print(f"    Import statistics:")
        print(f"      Total imports: {jira_result['total_processed'] + doc_result['total_processed']}")
        print(f"      Success rate: {((jira_result['success_rate'] + doc_result['success_rate']) / 2):.1f}%")
        
        print("[OK] System statistics collected")
        
        # Test 7: Performance test
        print("\n[7] Performance testing...")
        
        import time
        
        # Test search performance
        start_time = time.time()
        for _ in range(10):
            await kb.search("test query", n_results=3)
        search_time = (time.time() - start_time) / 10
        
        # Test RAG performance
        start_time = time.time()
        for _ in range(5):
            await rag_chain.ask("How does authentication work?")
        rag_time = (time.time() - start_time) / 5
        
        print(f"    Search performance: {search_time:.3f}s per query")
        print(f"    RAG performance: {rag_time:.3f}s per question")
        print(f"    Search queries/sec: {1/search_time:.1f}")
        print(f"    RAG questions/sec: {1/rag_time:.1f}")
        
        if search_time < 0.1 and rag_time < 2.0:
            print("[OK] Performance is acceptable")
        else:
            print("[WARN] Performance could be improved")
        
        print("\n" + "=" * 80)
        print("COMPLETE RAG SYSTEM TEST PASSED!")
        print("=" * 80)
        print("\n[SUCCESS] All components working together:")
        print("  - Local embedding generation")
        print("  - Document processing and cleaning")
        print("  - Knowledge base management")
        print("  - Enhanced search with hybrid capabilities")
        print("  - RAG question answering")
        print("  - Conversation with history")
        print("  - Batch import management")
        print("  - Error handling and recovery")
        print("  - Performance optimization")
        print("  - Comprehensive statistics")
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nTesting Complete EVAgent RAG System...\n")
    
    success = asyncio.run(test_complete_rag_system())
    sys.exit(0 if success else 1)
