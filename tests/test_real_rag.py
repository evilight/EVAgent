"""Test the updated API with real RAG integration"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing EVAgent RAG API with Real Integration...")
    print("=" * 60)
    
    # Test health
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Health: {resp.status_code} - {resp.json()}")
    
    # Login
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login-json", json=data)
    print(f"\nLogin: {resp.status_code}")
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"✅ Got token: {token[:30]}...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test stats
        print("\n--- System Stats ---")
        resp = requests.get(f"{BASE_URL}/api/v1/system/stats", headers=headers)
        if resp.status_code == 200:
            stats = resp.json()
            print(f"✅ Documents: {stats.get('total_documents', 0)}")
            print(f"✅ Embedding model: {stats.get('model_info', {}).get('embedding_model', 'unknown')}")
        else:
            print(f"❌ Stats failed: {resp.status_code}")
        
        # Test search
        print("\n--- Search Test ---")
        resp = requests.post(f"{BASE_URL}/api/v1/search/", headers=headers, json={"query": "test"})
        if resp.status_code == 200:
            results = resp.json()
            print(f"✅ Search returned {results.get('total', 0)} results")
            for i, result in enumerate(results.get('results', [])[:2]:
                print(f"   Result {i+1}: {result.get('title', 'No title')[:50]}...")
        else:
            print(f"❌ Search failed: {resp.status_code} - {resp.text}")
        
        # Test chat
        print("\n--- Chat Test ---")
        resp = requests.post(f"{BASE_URL}/api/v1/chat/", headers=headers, json={"message": "What can you tell me about this system?"})
        if resp.status_code == 200:
            chat = resp.json()
            print(f"✅ Chat response: {chat.get('answer', 'No answer')[:100]}...")
            print(f"   Sources: {len(chat.get('sources', []))}")
        else:
            print(f"❌ Chat failed: {resp.status_code} - {resp.text}")
            
    else:
        print(f"❌ Login failed: {resp.status_code} - {resp.text}")
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    test_api()
