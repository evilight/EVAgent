"""Simple chat endpoint that bypasses RAG chain issues"""
import requests
import json
from typing import Dict, List, Any

def create_simple_chat_response(query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a simple chat response from search results"""
    
    if not search_results:
        return {
            "answer": "I couldn't find any relevant information to answer your question. Please try different keywords or check your search terms.",
            "sources": [],
            "conversation_id": str(uuid.uuid4())
        }
    
    # Extract key information from search results
    relevant_docs = []
    for result in search_results[:3]:  # Use top 3 results
        title = result.get('metadata', {}).get('title', 'Untitled')
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
        answer += f"The document has a relevance score of {relevant_docs[0]['score']:.2f}. "
        answer += "You can find more details in the search results below."
    elif len(relevant_docs) == 2:
        answer = f"I found 2 relevant documents: '{relevant_docs[0]['title']}' and '{relevant_docs[1]['title']}'. "
        answer += f"The first document has a relevance score of {relevant_docs[0]['score']:.2f} and the second has {relevant_docs[1]['score']:.2f}. "
        answer += "Please review both documents for complete information."
    else:
        answer = f"I found {len(relevant_docs)} relevant documents related to your question. "
        answer += f"The most relevant is '{relevant_docs[0]['title']}' with a score of {relevant_docs[0]['score']:.2f}. "
        answer += "Please review all the search results below for comprehensive information."
    
    return {
        "answer": answer,
        "sources": relevant_docs,
        "conversation_id": str(uuid.uuid4())
    }

def test_simple_chat():
    print("Testing Simple Chat Endpoint...")
    print("=" * 50)
    
    # Login first
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post("http://localhost:8000/api/v1/auth/login", json=data)
    print(f"Login: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test simple chat
        chat_data = {"message": "EVAgent system architecture"}
        chat_resp = requests.post("http://localhost:8000/api/v1/chat/", json=chat_data, headers=headers)
        print(f"Simple chat status: {chat_resp.status_code}")
        
        if chat_resp.status_code == 200:
            chat_result = chat_resp.json()
            print(f"Simple chat response:")
            print(json.dumps(chat_result, indent=2))
        else:
            print(f"Simple chat error: {chat_resp.text}")
    else:
        print("Login failed")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    import uuid
    test_simple_chat()
