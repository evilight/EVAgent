#!/usr/bin/env python3
"""
EVAgent RAG Chat UI

A simple web-based chat interface for querying the RAG system.
Uses Flask for the web server and integrates with the existing RAG pipeline.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session

# Import RAG components
from langchain_integration import ChromaLangChainVectorStore, RAGChain
from langchain_integration.llm_integration import LLMManager
from database.chroma_manager import ChromaManager
from langchain_core.documents import Document


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    async def embed_text(self, texts):
        """Generate mock embeddings."""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        for text in texts:
            # Generate deterministic embeddings based on text hash
            import numpy as np
            np.random.seed(hash(text) % 2**32)
            embedding = np.random.randn(384).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())
        
        return embeddings
    
    async def embed_code(self, code):
        """Generate mock code embeddings."""
        return await self.embed_text(code)


class RAGChatUI:
    """RAG Chat UI application."""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Configure session
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.app.config['SESSION_PERMANENT'] = False
        self.app.config['SESSION_USE_SIGNER'] = True
        self.app.config['SESSION_KEY_PREFIX'] = 'rag_chat'
        
        # Initialize RAG components (will be done in init_rag)
        self.rag_chain = None
        self.chroma_manager = None
        self.vector_store = None
        self.llm_manager = None
        self.embedding_service = None
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main chat interface."""
            return render_template('chat.html')
        
        @self.app.route('/api/init', methods=['POST'])
        def init_rag():
            """Initialize RAG components."""
            try:
                # Check for API key
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return jsonify({
                        'success': False,
                        'error': 'OPENAI_API_KEY environment variable not set'
                    })
                
                # Initialize components
                self.embedding_service = MockEmbeddingService()
                self.chroma_manager = ChromaManager({
                    'persist_directory': './storage/chat_db',
                    'collection_name': 'chat_collection'
                })
                
                self.vector_store = ChromaLangChainVectorStore(
                    chroma_manager=self.chroma_manager,
                    embedding_service=self.embedding_service
                )
                
                self.llm_manager = LLMManager()
                
                self.rag_chain = RAGChain(
                    vector_store=self.vector_store,
                    llm_manager=self.llm_manager,
                    search_k=3,
                    similarity_threshold=-2.0
                )
                
                # Debug RAGChain
                import inspect
                print(f"RAGChain initialized: {type(self.rag_chain)}")
                print(f"RAGChain.ask signature: {inspect.signature(self.rag_chain.ask)}")
                
                # Load sample data if collection is empty
                stats = self.chroma_manager.get_collection_stats()
                if stats['document_count'] == 0:
                    self._load_sample_data()
                
                return jsonify({
                    'success': True,
                    'message': 'RAG system initialized successfully',
                    'document_count': stats['document_count']
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        
        @self.app.route('/api/test-rag', methods=['POST'])
        def test_rag():
            """Test RAG directly."""
            try:
                data = request.get_json()
                message = data.get('message', '').strip()
                
                if not self.rag_chain:
                    return jsonify({
                        'success': False,
                        'error': 'RAG system not initialized'
                    })
                
                # Run RAG query using asyncio.run for proper event loop handling
                def run_async(coro):
                    """Run async coroutine in sync context."""
                    try:
                        return asyncio.run(coro)
                    except RuntimeError:
                        # If already in async context, use the existing loop
                        return asyncio.get_event_loop().run_until_complete(coro)

                try:
                    result = run_async(self.rag_chain.ask(message))
                    return jsonify({
                        'success': True,
                        'answer': result['answer'],
                        'sources': result.get('sources', [])
                    })
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    })
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        
        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            """Handle chat messages."""
            try:
                data = request.get_json()
                message = data.get('message', '').strip()
                
                print(f"Request data: {data}")
                print(f"Session data: {dict(session)}")
                
                if not message:
                    return jsonify({
                        'success': False,
                        'error': 'Message cannot be empty'
                    })
                
                if not self.rag_chain:
                    return jsonify({
                        'success': False,
                        'error': 'RAG system not initialized'
                    })
                
                # Run RAG query using asyncio.run for proper event loop handling
                def run_async(coro):
                    """Run async coroutine in sync context."""
                    try:
                        return asyncio.run(coro)
                    except RuntimeError:
                        # If already in async context, use the existing loop
                        return asyncio.get_event_loop().run_until_complete(coro)
                
                try:
                    result = run_async(self.rag_chain.ask(message))
                except Exception as e:
                    print(f"Error calling RAGChain.ask: {e}")
                    print(f"RAGChain type: {type(self.rag_chain)}")
                    import inspect
                    print(f"RAGChain.ask signature: {inspect.signature(self.rag_chain.ask)}")
                    raise
                
                # Update history
                history = session.get('history', [])
                history.append({
                    'role': 'user',
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                history.append({
                    'role': 'assistant',
                    'message': result['answer'],
                    'timestamp': datetime.now().isoformat(),
                    'sources': result.get('sources', [])
                })
                
                # Keep only last 10 messages
                session['history'] = history[-10:]
                
                return jsonify({
                    'success': True,
                    'answer': result['answer'],
                    'sources': result.get('sources', []),
                    'history': history
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        
        @self.app.route('/api/clear', methods=['POST'])
        def clear_history():
            """Clear conversation history."""
            session.pop('history', None)
            return jsonify({'success': True})
        
        @self.app.route('/api/status')
        def status():
            """Get system status."""
            try:
                if self.chroma_manager:
                    stats = self.chroma_manager.get_collection_stats()
                    return jsonify({
                        'initialized': self.rag_chain is not None,
                        'document_count': stats['document_count'],
                        'collection_name': stats['collection_name']
                    })
                else:
                    return jsonify({
                        'initialized': False,
                        'document_count': 0,
                        'collection_name': None
                    })
            except Exception as e:
                return jsonify({
                    'initialized': False,
                    'error': str(e)
                })
    
    def _load_sample_data(self):
        """Load sample Jira data for demonstration."""
        # Sample Jira documents
        sample_docs = [
            {
                'content': 'Login page shows authentication error after recent deployment. Users report "Invalid credentials" message even with correct password. Stack trace shows JWT token validation failing in auth service.',
                'metadata': {
                    'source': 'jira',
                    'source_id': 'DEMO-1',
                    'title': 'Login page authentication error',
                    'type': 'Bug',
                    'priority': 'High',
                    'status': 'Open',
                    'labels': ['authentication', 'bug', 'login']
                }
            },
            {
                'content': 'Database connection pool exhaustion under heavy load. Error: "Connection pool is at maximum capacity". Affects UserService, OrderService, and PaymentService. Workaround: restart application.',
                'metadata': {
                    'source': 'jira',
                    'source_id': 'DEMO-2',
                    'title': 'Database connection pool exhausted',
                    'type': 'Bug',
                    'priority': 'Critical',
                    'status': 'In Progress',
                    'labels': ['database', 'performance', 'connection-pool']
                }
            },
            {
                'content': 'Memory leak detected in data processing module. Heap memory grows continuously during batch processing. GC not reclaiming memory. Large byte arrays not being released. Application crashes after ~2 hours.',
                'metadata': {
                    'source': 'jira',
                    'source_id': 'DEMO-5',
                    'title': 'Memory leak in data processing module',
                    'type': 'Bug',
                    'priority': 'High',
                    'status': 'Open',
                    'labels': ['memory', 'performance', 'leak']
                }
            },
            {
                'content': 'Setup guide for new developers: 1. Clone repository 2. Install Python 3.9+ 3. Create virtual environment 4. Install requirements.txt 5. Set environment variables 6. Run database migrations 7. Start development server.',
                'metadata': {
                    'source': 'jira',
                    'source_id': 'DEMO-6',
                    'title': 'Frontend React component testing guide',
                    'type': 'Documentation',
                    'priority': 'Medium',
                    'status': 'Done',
                    'labels': ['documentation', 'setup', 'onboarding']
                }
            },
            {
                'content': 'API rate limiting implementation: Use Redis for rate limiting. Key: user_id. Limit: 100 requests per minute. Expiration: 60 seconds. Return 429 status when limit exceeded.',
                'metadata': {
                    'source': 'jira',
                    'source_id': 'DEMO-4',
                    'title': 'API rate limiting implementation',
                    'type': 'Task',
                    'priority': 'Medium',
                    'status': 'In Review',
                    'labels': ['api', 'rate-limiting', 'redis']
                }
            }
        ]
        
        # Convert to LangChain documents and add to vector store
        documents = []
        for doc_data in sample_docs:
            doc = Document(
                page_content=doc_data['content'],
                metadata=doc_data['metadata']
            )
            documents.append(doc)
        
        self.vector_store.add_documents(documents)
    
    def run(self, host='localhost', port=5000, debug=True):
        """Run the Flask application."""
        print(f"Starting RAG Chat UI at http://{host}:{port}")
        print("Make sure OPENAI_API_KEY environment variable is set!")
        self.app.run(host=host, port=port, debug=debug)


# Create HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVAgent RAG Chat</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: #2563eb;
            color: white;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        
        .status {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            padding: 1rem;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem 0;
            margin-bottom: 1rem;
        }
        
        .message {
            margin-bottom: 1rem;
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            max-width: 80%;
        }
        
        .message.user {
            background: #2563eb;
            color: white;
            margin-left: auto;
        }
        
        .message.assistant {
            background: white;
            border: 1px solid #e5e7eb;
            margin-right: auto;
        }
        
        .message-content {
            margin-bottom: 0.5rem;
        }
        
        .message-time {
            font-size: 0.75rem;
            opacity: 0.7;
        }
        
        .sources {
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid #e5e7eb;
            font-size: 0.85rem;
        }
        
        .sources-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        
        .source-item {
            background: #f9fafb;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            margin-bottom: 0.25rem;
        }
        
        .input-container {
            display: flex;
            gap: 0.5rem;
            padding: 1rem;
            background: white;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .input-field {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #d1d5db;
            border-radius: 0.375rem;
            font-size: 1rem;
            outline: none;
        }
        
        .input-field:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .send-button {
            padding: 0.75rem 1.5rem;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 0.375rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .send-button:hover:not(:disabled) {
            background: #1d4ed8;
        }
        
        .send-button:disabled {
            background: #9ca3af;
            cursor: not-allowed;
        }
        
        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 1rem;
            background: white;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .clear-button {
            padding: 0.5rem 1rem;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            cursor: pointer;
        }
        
        .clear-button:hover {
            background: #dc2626;
        }
        
        .error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin-bottom: 1rem;
            border: 1px solid #fecaca;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #2563eb;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>EVAgent RAG Chat</h1>
        <div class="status" id="status">Initializing...</div>
    </div>
    
    <div class="chat-container">
        <div class="controls">
            <div>
                <span id="doc-count">Documents: 0</span>
            </div>
            <button class="clear-button" onclick="clearHistory()">Clear History</button>
        </div>
        
        <div id="error-container"></div>
        
        <div class="messages" id="messages"></div>
        
        <div class="input-container">
            <input 
                type="text" 
                id="message-input" 
                class="input-field" 
                placeholder="Ask about bugs, setup, or any project issues..."
                onkeypress="handleKeyPress(event)"
            >
            <button id="send-button" class="send-button" onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script>
        let isInitialized = false;
        
        // Initialize on page load
        window.onload = function() {
            initializeRAG();
            loadHistory();
        };
        
        // Initialize RAG system
        async function initializeRAG() {
            try {
                const response = await fetch('/api/init', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                
                const result = await response.json();
                
                if (result.success) {
                    isInitialized = true;
                    document.getElementById('status').textContent = 'Ready';
                    document.getElementById('doc-count').textContent = `Documents: ${result.document_count}`;
                } else {
                    showError(result.error);
                    document.getElementById('status').textContent = 'Error';
                }
            } catch (error) {
                showError('Failed to initialize RAG system: ' + error.message);
                document.getElementById('status').textContent = 'Error';
            }
        }
        
        // Send message
        async function sendMessage() {
            if (!isInitialized) {
                showError('RAG system not initialized');
                return;
            }
            
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Clear input
            input.value = '';
            
            // Disable send button
            const sendButton = document.getElementById('send-button');
            sendButton.disabled = true;
            sendButton.innerHTML = '<div class="loading"></div>';
            
            // Add user message
            addMessage('user', message);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    addMessage('assistant', result.answer, result.sources);
                } else {
                    addMessage('assistant', 'Error: ' + result.error);
                }
            } catch (error) {
                addMessage('assistant', 'Error: ' + error.message);
            } finally {
                // Re-enable send button
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
            }
        }
        
        // Add message to chat
        function addMessage(role, content, sources = null) {
            const messagesContainer = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = new Date().toLocaleTimeString();
            
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(timeDiv);
            
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                
                const sourcesTitle = document.createElement('div');
                sourcesTitle.className = 'sources-title';
                sourcesTitle.textContent = 'Sources:';
                sourcesDiv.appendChild(sourcesTitle);
                
                sources.forEach(source => {
                    const sourceItem = document.createElement('div');
                    sourceItem.className = 'source-item';
                    sourceItem.textContent = source;
                    sourcesDiv.appendChild(sourceItem);
                });
                
                messageDiv.appendChild(sourcesDiv);
            }
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Clear history
        async function clearHistory() {
            try {
                await fetch('/api/clear', {method: 'POST'});
                document.getElementById('messages').innerHTML = '';
            } catch (error) {
                showError('Failed to clear history: ' + error.message);
            }
        }
        
        // Load history from session
        function loadHistory() {
            // History is loaded from session on the server side
            // This is just a placeholder for any client-side history loading
        }
        
        // Handle Enter key
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        // Show error message
        function showError(message) {
            const errorContainer = document.getElementById('error-container');
            errorContainer.innerHTML = `<div class="error">${message}</div>`;
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorContainer.innerHTML = '';
            }, 5000);
        }
    </script>
</body>
</html>
"""


def create_templates():
    """Create templates directory and HTML file."""
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    with open(templates_dir / 'chat.html', 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE)


def main():
    """Main entry point."""
    # Create templates
    create_templates()
    
    # Create and run app
    app = RAGChatUI()
    app.run(debug=False)


if __name__ == '__main__':
    main()
