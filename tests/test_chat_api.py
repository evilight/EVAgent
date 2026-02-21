"""Test chat API specifically"""
import requests
import json

def test_chat_api():
    print("Testing Chat API...")
    print("=" * 50)
    
    # Login first
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post("http://localhost:8000/api/v1/auth/login-json", json=data)
    print(f"Login: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test chat with specific question
        data = {"message": "What are the components of EVAgent system?"}
        resp = requests.post("http://localhost:8000/api/v1/chat/", json=data, headers=headers)
        print(f"Chat status: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"Full chat response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"Error response: {resp.text}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_chat_api()
