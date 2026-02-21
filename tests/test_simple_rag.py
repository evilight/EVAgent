"""Test simple RAG without LangChain complications"""
import requests
import json

def test_simple_rag():
    print("Testing simple RAG (bypassing LangChain)...")
    print("=" * 50)
    
    # Login first
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post("http://localhost:8000/api/v1/auth/login-json", json=data)
    print(f"Login: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test search to get a document ID
        search_data = {"query": "EVAgent System Architecture"}
        search_resp = requests.post("http://localhost:8000/api/v1/search/", json=search_data, headers=headers)
        print(f"Search status: {search_resp.status_code}")
        
        if search_resp.status_code == 200:
            search_results = search_resp.json()
            print(f"Search results: {len(search_results.get('results', []))}")
            
            if search_results.get('results'):
                first_doc = search_results['results'][0]
                doc_id = first_doc.get('id')
                print(f"First document ID: {doc_id}")
                print(f"First document title: {first_doc.get('metadata', {}).get('title', 'No title')}")
                
                # Now test chat with document context
                chat_data = {"message": f"Tell me about document {doc_id}"}
                chat_resp = requests.post("http://localhost:8000/api/v1/chat/", json=chat_data, headers=headers)
                print(f"Chat status: {chat_resp.status_code}")
                
                if chat_resp.status_code == 200:
                    chat_result = chat_resp.json()
                    print(f"Chat response:")
                    print(json.dumps(chat_result, indent=2))
                else:
                    print(f"Chat error: {chat_resp.text}")
            else:
                print("No search results found")
    else:
        print("Login failed")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_simple_rag()
