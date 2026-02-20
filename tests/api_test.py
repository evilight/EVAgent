"""Test script for EVAgent RAG API"""
import requests
import base64

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Health: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200

def test_login():
    """Test login endpoint"""
    credentials = base64.b64encode(b"admin:admin123").decode()
    headers = {"Authorization": f"Basic {credentials}"}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", headers=headers)
    print(f"Login: {resp.status_code} - {resp.json()}")
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

def test_chat(token):
    """Test chat endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": "What is RAG?"}
    resp = requests.post(f"{BASE_URL}/api/v1/chat/", headers=headers, json=data)
    print(f"Chat: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200

def test_search(token):
    """Test search endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {"query": "test query"}
    resp = requests.post(f"{BASE_URL}/api/v1/search/", headers=headers, json=data)
    print(f"Search: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200

def test_stats(token):
    """Test stats endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/system/stats", headers=headers)
    print(f"Stats: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200

if __name__ == "__main__":
    print("Testing EVAgent RAG API...")
    print("=" * 50)
    
    # Test health
    if not test_health():
        print("Health check failed!")
        exit(1)
    
    # Test login
    token = test_login()
    if not token:
        print("Login failed!")
        exit(1)
    
    # Test protected endpoints
    test_chat(token)
    test_search(token)
    test_stats(token)
    
    print("=" * 50)
    print("All tests completed!")
