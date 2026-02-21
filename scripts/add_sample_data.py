"""Add sample data to knowledge base for testing"""
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge.knowledge_base import KnowledgeBase

async def add_sample_data():
    """Add sample documents to knowledge base"""
    print("Adding sample data to knowledge base...")
    print("=" * 50)
    
    # Setup knowledge base
    kb_config = {
        'persist_directory': './storage/rag_sample_db',
        'collection_name': 'evagent_sample',
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'chunk_size': 300,
        'chunk_overlap': 30
    }
    
    kb = KnowledgeBase(kb_config)
    print("Knowledge base initialized")
    
    # Sample documents
    sample_docs = [
        {
            'content': '''EVAgent RAG System Architecture
            
The EVAgent system consists of several key components:
1. FastAPI Backend - Provides REST API endpoints for chat, search, and system management
2. React Frontend - Modern web interface for user interaction
3. Knowledge Base - ChromaDB vector store for document embeddings
4. RAG Pipeline - Retrieval-Augmented Generation for question answering
5. Connectors - Integration with Jira and Confluence data sources

The system uses local embedding models (all-MiniLM-L6-v2) and supports various LLM providers.''',
            'metadata': {
                'source': 'documentation',
                'type': 'architecture',
                'title': 'EVAgent System Architecture',
                'created_at': datetime.now().isoformat()
            },
            'id': 'doc-architecture'
        },
        {
            'content': '''API Authentication and Security

The EVAgent API uses JWT (JSON Web Tokens) for authentication:
- Login endpoints: /api/v1/auth/login and /api/v1/auth/login-json
- Default credentials: admin/admin123
- Token expiration: 24 hours
- Protected endpoints require Bearer token in Authorization header

Security features include:
- CORS configuration for cross-origin requests
- Input validation and sanitization
- Error handling and logging
- Rate limiting capabilities''',
            'metadata': {
                'source': 'documentation',
                'type': 'security',
                'title': 'API Authentication Guide',
                'created_at': datetime.now().isoformat()
            },
            'id': 'doc-security'
        },
        {
            'content': '''Getting Started with EVAgent

To start using EVAgent RAG system:

1. Start the backend server:
   cd d:\EVAgent\src\api
   python fresh_api.py

2. Start the frontend:
   cd d:\EVAgent\frontend
   npm start

3. Access the application:
   Frontend: http://localhost:3000
   API Docs: http://localhost:8000/docs

4. Login with default credentials:
   Username: admin
   Password: admin123

5. Use the chat interface to ask questions about your documents
6. Use the search interface to find relevant information
7. Check system statistics for monitoring''',
            'metadata': {
                'source': 'documentation',
                'type': 'tutorial',
                'title': 'Getting Started Guide',
                'created_at': datetime.now().isoformat()
            },
            'id': 'doc-tutorial'
        },
        {
            'content': '''Troubleshooting Common Issues

Backend Issues:
- Port 8000 in use: Kill existing processes with taskkill
- Import errors: Check Python path and dependencies
- RAG not working: Verify embedding model path

Frontend Issues:
- Port 3000 in use: Kill existing Node.js processes
- Build errors: Check npm dependencies and TypeScript config
- API connection: Verify proxy configuration

Data Import Issues:
- Jira/Confluence connection: Check API tokens and permissions
- Environment variables: Ensure .env file is properly configured
- Document parsing: Verify file formats and permissions

Performance Issues:
- Slow responses: Check embedding model loading
- Memory usage: Monitor ChromaDB size and cleanup
- Network timeouts: Adjust timeout settings in config''',
            'metadata': {
                'source': 'documentation',
                'type': 'troubleshooting',
                'title': 'Troubleshooting Guide',
                'created_at': datetime.now().isoformat()
            },
            'id': 'doc-troubleshooting'
        }
    ]
    
    # Add documents to knowledge base
    documents = []
    for doc in sample_docs:
        documents.append({
            'content': doc['content'],
            'metadata': doc['metadata'],
            'id': doc['id']
        })
    
    try:
        doc_ids = await kb.add_documents(documents)
        added_count = len(doc_ids)
        print(f"\nSuccessfully added {added_count} documents to knowledge base")
        
        for i, doc in enumerate(sample_docs):
            print(f"Added: {doc['metadata']['title']}")
            
    except Exception as e:
        print(f"Error adding documents: {e}")
        added_count = 0
    
    # Get statistics
    stats = kb.get_stats()
    print(f"\nKnowledge Base Statistics:")
    print(f"Total documents: {stats.get('document_count', 0)}")
    print(f"Embedding model: {stats.get('embedding_model', 'Unknown')}")
    print(f"Collection: {stats.get('collection_name', 'Unknown')}")
    
    print("\n" + "=" * 50)
    print("Sample data added successfully!")
    print("You can now test the chat and search functionality.")

if __name__ == "__main__":
    asyncio.run(add_sample_data())
