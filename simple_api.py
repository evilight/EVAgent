"""Simple FastAPI server for testing chat functionality"""
import os
import sys
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi import FastAPI, Request, Depends, HTTPException, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install: pip install fastapi uvicorn python-jose")
    sys.exit(1)

# Simple in-memory storage for documents
SAMPLE_DOCUMENTS = [
    {
        "id": "doc1",
        "title": "EVAgent System Architecture",
        "content": "EVAgent RAG System Architecture\n\nThe EVAgent system consists of several key components:\n1. FastAPI Backend - Provides REST API endpoints for chat, search, and system management\n2. React Frontend - Modern web interface for user interaction\n3. Knowledge Base - ChromaDB vector store for document embeddings\n4. RAG Pipeline - Retrieval-Augmented Generation for question answering\n5. Connectors - Integration with Jira and Confluence data sources\n\nThe system uses local embedding models (all-MiniLM-L6-v2) and supports various LLM providers.",
        "score": 0.9
    },
    {
        "id": "doc2", 
        "title": "Getting Started Guide",
        "content": "Getting Started with EVAgent\n\nTo start using EVAgent RAG system:\n\n1. Start the backend server:\n   cd d:\\EVAgent\\src\\api\n   python fresh_api.py\n\n2. Start the frontend:\n   cd d:\\EVAgent\\frontend\n   npm start\n\n3. Access the application:\n   Frontend: http://localhost:3000\n   API Docs: http://localhost:8000/docs\n\n4. Login with default credentials:\n   Username: admin\n   Password: admin123\n\n5. Use the chat interface to ask questions about your documents\n6. Use the search interface to find relevant information\n7. Check system statistics for monitoring",
        "score": 0.8
    },
    {
        "id": "doc3",
        "title": "API Authentication Guide", 
        "content": "API Authentication and Security\n\nThe EVAgent API uses JWT (JSON Web Tokens) for authentication:\n- Login endpoints: /api/v1/auth/login and /api/v1/auth/login-json\n- Default credentials: admin/admin123\n- Token expiration: 24 hours\n- Protected endpoints require Bearer token in Authorization header\n\nSecurity features include:\n- CORS configuration for cross-origin requests\n- Input validation and sanitization\n- Error handling and logging\n- Rate limiting capabilities",
        "score": 0.7
    }
]

app = FastAPI(title="EVAgent Simple API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.options("/api/v1/{path:path}")
async def preflight_handler(path: str):
    """Handle CORS preflight requests"""
    return {
        "status": "ok",
        "message": f"CORS preflight for {path}"
    }

import base64
import json
import uuid
from datetime import datetime, timedelta

# Generate a simple JWT-like token
def generate_simple_token(username: str) -> str:
    """Generate a simple JWT-like token for testing"""
    # Create header
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    
    # Create payload
    payload = {
        "sub": username,
        "exp": int((datetime.now() + timedelta(hours=24)).timestamp()),
        "iat": int(datetime.now().timestamp())
    }
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Create signature (simple for demo)
    signature = base64.urlsafe_b64encode(b"test-signature").decode().rstrip('=')
    
    # Combine parts
    return f"{header_encoded}.{payload_encoded}.{signature}"

# Simple JWT token storage (in production, use proper database)
TOKENS = {"admin": generate_simple_token("admin")}

# Pydantic models
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = None
    filters: Dict[str, Any] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    conversation_id: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Dict[str, Any] = None

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    username: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Simple search function
def search_documents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Simple keyword-based search"""
    query_lower = query.lower()
    results = []
    
    for doc in SAMPLE_DOCUMENTS:
        # Check if query matches title or content
        title_match = query_lower in doc["title"].lower()
        content_match = query_lower in doc["content"].lower()
        
        # Also check for partial matches in common words
        query_words = query_lower.split()
        title_words = doc["title"].lower().split()
        content_words = doc["content"].lower().split()
        
        partial_match = any(word in title_words or word in content_words for word in query_words if len(word) > 2)
        
        if title_match or content_match or partial_match:
            results.append(doc)
    
    return results[:limit]

# Simple chat function
def generate_chat_response(query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate simple chat response from search results"""
    
    if not search_results:
        return {
            "answer": "I couldn't find any relevant information to answer your question. Please try different keywords or check your search terms.",
            "sources": [],
            "conversation_id": str(uuid.uuid4())
        }
    
    # Extract key information from search results
    relevant_docs = []
    for result in search_results[:3]:  # Use top 3 results
        title = result.get('title', 'Untitled')
        content = result.get('content', '')
        score = result.get('score', 0.0)
        
        # Create a brief summary of each document
        if len(content) > 200:
            content_preview = content[:200] + "..."
        else:
            content_preview = content
            
        relevant_docs.append({
            "title": title,
            "content": content_preview,
            "score": score,
            "id": result.get('id', 'unknown')
        })
    
    # Generate a simple answer based on the documents found
    if len(relevant_docs) == 1:
        answer = f"Based on the document '{relevant_docs[0]['title']}', I found relevant information. "
        answer += f"The document has a relevance score of {relevant_docs[0]['score']:.1f}. "
        answer += "You can find more details in the search results below."
    elif len(relevant_docs) == 2:
        answer = f"I found 2 relevant documents: '{relevant_docs[0]['title']}' and '{relevant_docs[1]['title']}'. "
        answer += f"The first document has a relevance score of {relevant_docs[0]['score']:.1f} and the second has {relevant_docs[1]['score']:.1f}. "
        answer += "Please review both documents for complete information."
    else:
        answer = f"I found {len(relevant_docs)} relevant documents related to your question. "
        answer += f"The most relevant is '{relevant_docs[0]['title']}' with a score of {relevant_docs[0]['score']:.1f}. "
        answer += "Please review all the search results below for comprehensive information."
    
    return {
        "answer": answer,
        "sources": relevant_docs,
        "conversation_id": str(uuid.uuid4())
    }

# Authentication
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Simple token verification"""
    if credentials.credentials in TOKENS.values():
        return credentials.credentials
    return None

# API Routes
# Simple usage tracking (in production, use database)
USAGE_STATS = {
    "total_conversations": 0,
    "total_searches": 0
}

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Simple login endpoint"""
    print(f"Login request received: {request}")
    print(f"Username: {request.username}")
    print(f"Password: {request.password}")
    
    if request.username in TOKENS and request.password == "admin123":
        # Track conversation usage
        USAGE_STATS["total_conversations"] += 1
        return TokenResponse(access_token=TOKENS[request.username])
    else:
        print(f"Invalid credentials: username={request.username}, password={request.password}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/v1/chat/")
async def chat_endpoint(request: ChatRequest, current_user: str = Depends(verify_token)):
    """Simple chat endpoint"""
    try:
        # Track search usage
        USAGE_STATS["total_searches"] += 1
        
        # Use working search functionality
        search_results = search_documents(request.message, limit=5)
        
        # Create simple response from search results
        response = generate_chat_response(request.message, search_results)
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")

@app.post("/api/v1/search/")
async def search_endpoint(request: SearchRequest, current_user: str = Depends(verify_token)):
    """Simple search endpoint"""
    try:
        results = search_documents(request.query, limit=request.limit)
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            username=current_user
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")

@app.get("/api/v1/system/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/system/stats")
async def system_stats():
    """System statistics endpoint"""
    return {
        "status": "healthy",
        "total_documents": len(SAMPLE_DOCUMENTS),
        "total_conversations": USAGE_STATS["total_conversations"],
        "total_searches": USAGE_STATS["total_searches"],
        "model_info": {
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": "deepseek"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Simple test endpoint for debugging"""
    return {
        "status": "ok",
        "message": "API is working",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/test-json")
async def test_json_endpoint():
    """Simple test endpoint that returns JSON"""
    return {
        "status": "ok",
        "message": "API is working",
        "data": {"test": "value", "number": 123},
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("Starting EVAgent Simple API Server...")
    print("Available endpoints:")
    print("  POST /api/v1/auth/login - Login")
    print("  POST /api/v1/chat/ - Chat")
    print("  POST /api/v1/search/ - Search")
    print("  GET  /api/v1/test - Simple test")
    print("  GET  /api/v1/test-json - JSON test")
    print("  GET  /api/v1/system/health - Health check")
    print()
    print("Default credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
