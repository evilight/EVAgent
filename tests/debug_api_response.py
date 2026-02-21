"""Debug API response format"""
import requests
import json

def debug_api_response():
    print("Debugging API response format...")
    print("=" * 50)
    
    # Login first
    data = {"username": "admin", "password": "admin123"}
    resp = requests.post("http://localhost:8000/api/v1/auth/login-json", json=data)
    print(f"Login: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test search with a specific query
        data = {"query": "EVAgent System Architecture"}
        resp = requests.post("http://localhost:8000/api/v1/search/", json=data, headers=headers)
        print(f"Search status: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"Full response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"Error response: {resp.text}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    debug_api_response()
