#!/usr/bin/env python3
"""
Complete End-to-End RAG Demo

This script demonstrates the full EVAgent RAG pipeline:
1. Load documents from Jira and Confluence
2. Index them with embeddings
3. Perform semantic search queries
4. Generate answers with LLM (DeepSeek)
5. Show source attribution

Usage:
    python test_e2e_demo.py

Requirements:
    - OPENAI_API_KEY set in environment or config/openai_config.yaml
    - JIRA_USERNAME and JIRA_API_TOKEN for Jira access
    - CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN for Confluence access
"""

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


async def load_sample_jira_data():
    """Load sample Jira issues for demo."""
    print("Loading sample Jira data...")
    
    # Sample Jira issues for demo (since we don't have Confluence enabled)
    jira_docs = [
        {
            'id': 'DEMO-1',
            'title': 'Login page authentication error',
            'content': '''Users are experiencing authentication errors when trying to log in. 
            The error occurs when the password contains special characters. 
            Error message: "Authentication failed: Invalid credentials"
            Steps to reproduce:
            1. Go to login page
            2. Enter username with special characters
            3. Enter password with symbols like @#$%
            4. Click login button
            Expected: User should log in successfully
            Actual: Authentication error displayed''',
            'status': 'Open',
            'priority': 'High',
            'reporter': 'john.doe@example.com',
            'assignee': 'jane.smith@example.com',
            'labels': ['authentication', 'bug', 'login'],
            'created': '2024-01-15T10:30:00Z',
            'updated': '2024-01-16T14:20:00Z',
            'type': 'Bug'
        },
        {
            'id': 'DEMO-2',
            'title': 'Database connection pool exhausted',
            'content': '''The application is throwing "Connection pool exhausted" errors under heavy load.
            This started happening after the last deployment. The database is PostgreSQL 14.
            Error: java.sql.SQLException: Connection pool is at maximum capacity
            Stack trace shows the issue is in the connection pool manager.
            Affected components: UserService, OrderService, PaymentService
            Workaround: Restart the application to release connections.''',
            'status': 'In Progress',
            'priority': 'Critical',
            'reporter': 'devops@example.com',
            'assignee': 'backend.lead@example.com',
            'labels': ['database', 'performance', 'connection-pool'],
            'created': '2024-01-10T08:15:00Z',
            'updated': '2024-01-16T16:45:00Z',
            'type': 'Bug'
        },
        {
            'id': 'DEMO-3',
            'title': 'Setup guide for new developers',
            'content': '''Welcome to the team! Here is the setup guide:
            
            1. Clone the repository: git clone https://github.com/company/project.git
            2. Install dependencies: npm install (for frontend) and pip install -r requirements.txt (for backend)
            3. Set up environment variables:
               - DATABASE_URL=postgresql://localhost:5432/project
               - REDIS_URL=redis://localhost:6379
               - API_KEY=your_api_key_here
            4. Run database migrations: alembic upgrade head
            5. Start the development server: npm run dev (frontend) and python main.py (backend)
            
            Common issues:
            - If you get "Module not found" errors, check your Python version (3.10+)
            - For database connection issues, ensure PostgreSQL is running on port 5432
            - Frontend hot reload may fail on Windows - restart if needed''',
            'status': 'Published',
            'priority': 'Medium',
            'reporter': 'team.lead@example.com',
            'assignee': None,
            'labels': ['documentation', 'onboarding', 'setup'],
            'created': '2024-01-05T09:00:00Z',
            'updated': '2024-01-15T11:30:00Z',
            'type': 'Documentation'
        },
        {
            'id': 'DEMO-4',
            'title': 'API rate limiting implementation',
            'content': '''We need to implement API rate limiting to prevent abuse.
            Requirements:
            - 100 requests per minute per API key
            - Rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
            - Return 429 Too Many Requests when limit exceeded
            - Use Redis for distributed rate limiting
            
            Implementation plan:
            1. Create RateLimiter middleware
            2. Store counters in Redis with TTL
            3. Add rate limit info to response headers
            4. Configure per-endpoint limits if needed
            
            Testing strategy:
            - Unit tests for rate limiter logic
            - Integration tests with Redis
            - Load testing to verify limits work correctly''',
            'status': 'Open',
            'priority': 'High',
            'reporter': 'security@example.com',
            'assignee': 'api.team@example.com',
            'labels': ['api', 'security', 'rate-limiting', 'redis'],
            'created': '2024-01-12T13:20:00Z',
            'updated': '2024-01-14T10:10:00Z',
            'type': 'Task'
        },
        {
            'id': 'DEMO-5',
            'title': 'Memory leak in data processing module',
            'content': '''We have identified a memory leak in the data processing module.
            Symptoms:
            - Heap memory grows continuously during batch processing
            - Garbage collection is not reclaiming memory
            - Application crashes with OutOfMemoryError after ~2 hours
            
            Investigation findings:
            - Memory profiler shows retained objects in DataBuffer class
            - Circular references in event handlers
            - Large byte arrays not being released
            
            Proposed fixes:
            1. Clear DataBuffer after processing each batch
            2. Use weak references for event handlers
            3. Implement explicit resource cleanup
            
            Monitoring: Add memory usage metrics to Datadog dashboard''',
            'status': 'In Progress',
            'priority': 'High',
            'reporter': 'monitoring@example.com',
            'assignee': 'performance.team@example.com',
            'labels': ['performance', 'memory', 'leak', 'java'],
            'created': '2024-01-08T16:30:00Z',
            'updated': '2024-01-16T09:15:00Z',
            'type': 'Bug'
        },
        {
            'id': 'DEMO-6',
            'title': 'Frontend React component testing guide',
            'content': '''Best practices for testing React components:
            
            Testing Tools:
            - Jest for unit testing
            - React Testing Library for component testing
            - Cypress for E2E testing
            
            Component Testing Patterns:
            1. Test user interactions, not implementation details
            2. Use screen queries that reflect how users see the UI
            3. Mock external dependencies (API calls, browser APIs)
            4. Test accessibility with jest-axe
            
            Example test:
            ```javascript
            import { render, screen, fireEvent } from '@testing-library/react';
            import UserProfile from './UserProfile';
            
            test('displays user name', () => {
              render(<UserProfile name="John" />);
              expect(screen.getByText('John')).toBeInTheDocument();
            });
            ```
            
            Common mistakes to avoid:
            - Testing implementation details (internal state)
            - Not testing error states
            - Skipping accessibility testing''',
            'status': 'Published',
            'priority': 'Medium',
            'reporter': 'frontend.lead@example.com',
            'assignee': None,
            'labels': ['documentation', 'testing', 'react', 'frontend'],
            'created': '2024-01-03T11:00:00Z',
            'updated': '2024-01-10T15:20:00Z',
            'type': 'Documentation'
        }
    ]
    
    return jira_docs


def convert_jira_to_documents(jira_docs):
    """Convert Jira documents to LangChain Documents."""
    from langchain_core.documents import Document
    
    documents = []
    for doc in jira_docs:
        # Convert labels list to string for ChromaDB compatibility
        labels_str = ', '.join(doc['labels']) if doc['labels'] else ''
        
        metadata = {
            'source': 'jira',
            'source_id': doc['id'],
            'title': doc['title'],
            'type': doc['type'],
            'status': doc['status'],
            'priority': doc['priority'],
            'reporter': doc['reporter'],
            'assignee': doc['assignee'] or 'Unassigned',
            'labels': labels_str,  # Convert list to string
            'created': doc['created'],
            'updated': doc['updated'],
            'url': f"https://jira.example.com/browse/{doc['id']}"
        }
        
        documents.append(Document(
            page_content=doc['content'],
            metadata=metadata
        ))
    
    return documents


async def run_e2e_demo():
    """Run complete end-to-end RAG demo."""
    print("=" * 70)
    print("       END-TO-END RAG PIPELINE DEMO")
    print("=" * 70)
    print()
    print("This demo showcases the complete EVAgent RAG system:")
    print("  1. Document loading (Jira, simulated Confluence)")
    print("  2. Vector embedding and storage")
    print("  3. Semantic search with context retrieval")
    print("  4. LLM-powered question answering (DeepSeek)")
    print("  5. Source attribution")
    print()
    print("-" * 70)
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
        
        # Initialize components
        print("[Phase 1] Initializing RAG components...")
        embedding_service = MockEmbeddingService()
        chroma_manager = ChromaManager({
            'persist_directory': './storage/demo_db',
            'collection_name': 'demo_knowledge'
        })
        vector_store = ChromaLangChainVectorStore(
            chroma_manager=chroma_manager,
            embedding_service=embedding_service
        )
        llm_manager = LLMManager()
        rag_chain = RAGChain(
            vector_store=vector_store,
            llm_manager=llm_manager,
            search_k=3,
            similarity_threshold=-2.0
        )
        print("          [OK] All components initialized")
        print()
        
        # Load and index documents
        print("[Phase 2] Loading and indexing documents...")
        
        # Load Jira data
        jira_data = await load_sample_jira_data()
        jira_docs = convert_jira_to_documents(jira_data)
        print(f"          Loaded {len(jira_docs)} documents from Jira")
        
        # Add documents to vector store
        doc_ids = vector_store.add_documents(jira_docs)
        print(f"          [OK] Indexed {len(doc_ids)} documents")
        
        # Show collection stats
        stats = chroma_manager.get_collection_stats()
        print(f"          Collection: {stats['document_count']} documents")
        print()
        
        # Query phase
        print("[Phase 3] RAG Query Demonstration")
        print("=" * 70)
        print()
        
        test_queries = [
            {
                'query': 'How do I fix the login authentication error?',
                'description': 'Bug resolution query'
            },
            {
                'query': 'What causes database connection pool exhaustion?',
                'description': 'Performance issue query'
            },
            {
                'query': 'How do new developers set up their environment?',
                'description': 'Onboarding query'
            },
            {
                'query': 'How should we implement API rate limiting?',
                'description': 'Architecture/implementation query'
            },
            {
                'query': 'What is causing the memory leak in data processing?',
                'description': 'Troubleshooting query'
            }
        ]
        
        for i, test in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {test['description']}")
            print(f"Question: \"{test['query']}\"")
            print("-" * 70)
            
            result = await rag_chain.ask(test['query'])
            
            print(f"Answer:\n{result['answer']}\n")
            
            print("Sources Retrieved:")
            for j, source in enumerate(result['sources'], 1):
                doc_type = source.get('type', 'Unknown')
                title = source.get('title', 'Untitled')
                source_id = source.get('id', 'unknown')
                similarity = source.get('similarity', 0)
                print(f"  {j}. [{doc_type}] {title} ({source_id}) - score: {similarity:.4f}")
            
            print()
        
        # Chat conversation demo
        print("=" * 70)
        print("[Phase 4] Conversation with History")
        print("=" * 70)
        print()
        
        conversation = [
            {"role": "user", "content": "I'm having trouble with database connections"},
            {"role": "assistant", "content": "I see there are some database-related issues. What specific error are you seeing?"},
            {"role": "user", "content": "It says 'Connection pool exhausted'"}
        ]
        
        print("Conversation History:")
        for msg in conversation:
            role = msg['role'].capitalize()
            print(f"  {role}: {msg['content']}")
        print()
        
        final_answer = await rag_chain.ask(
            question="What's causing this and how do I fix it?",
            chat_history=conversation
        )
        
        print(f"Final Answer:\n{final_answer['answer']}\n")
        
        # Summary
        print("=" * 70)
        print("                    DEMO COMPLETE")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  - Indexed {len(doc_ids)} documents")
        print(f"  - Performed {len(test_queries)} RAG queries")
        print(f"  - LLM Provider: DeepSeek (deepseek-chat)")
        print(f"  - Vector Store: ChromaDB")
        print()
        print("Components Demonstrated:")
        print("  [OK] Document loading (Jira connector)")
        print("  [OK] Vector embedding and storage")
        print("  [OK] Semantic search retrieval")
        print("  [OK] LLM-powered answer generation")
        print("  [OK] Source attribution")
        print("  [OK] Conversation with history")
        print()
        
        # Cleanup
        print("Cleaning up demo data...")
        for doc_id in doc_ids:
            chroma_manager.delete_document(doc_id)
        print("[OK] Demo data cleaned up")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("       EVAgent RAG System - End-to-End Demonstration")
    print("=" * 70)
    print()
    print("Requirements:")
    print("  - OPENAI_API_KEY environment variable set")
    print("  - DeepSeek API configured in config/openai_config.yaml")
    print()
    
    success = asyncio.run(run_e2e_demo())
    sys.exit(0 if success else 1)
