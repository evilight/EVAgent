"""Test RAG with fresh data by forcing reimport"""
import requests
import time

def test_with_new_data():
    print("Testing RAG with fresh data...")
    print("=" * 50)
    
    # Test health
    resp = requests.get("http://localhost:8000/api/v1/system/health")
    print(f"Health: {resp.status_code}")
    
    # Login first
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post("http://localhost:8000/api/v1/auth/login-json", json=data)
    print(f"Login: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test search with a specific query that should match our sample data
        data = {"query": "EVAgent System Architecture"}
        resp = requests.post("http://localhost:8000/api/v1/search/", json=data, headers=headers)
        print(f"Search for 'EVAgent System Architecture': {resp.status_code}")
        
        if resp.status_code == 200:
            results = resp.json()
            print(f"Results found: {len(results.get('results', []))}")
            
            for result in results.get('results', [])[:2]:
                print(f"  - {result.get('metadata', {}).get('title', 'No title')}")
                print(f"    Score: {result.get('score', 0):.3f}")
        
        # Test chat with specific question
        data = {"message": "What are the components of EVAgent system?"}
        resp = requests.post("http://localhost:8000/api/v1/chat/", json=data, headers=headers)
        print(f"Chat response status: {resp.status_code}")
        
        if resp.status_code == 200:
            chat = resp.json()
            answer = chat.get('answer', 'No answer')
            sources = len(chat.get('sources', []))
            print(f"Answer: {answer[:100]}...")
            print(f"Sources: {sources}")
    
    print("\n" + "=" * 50)
    print("If you see 0 results above, the RAG service is still using old collection.")
    print("The fix requires restarting the API server completely.")

if __name__ == "__main__":
    test_with_new_data()
