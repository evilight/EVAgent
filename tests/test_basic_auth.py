"""Test Basic Auth login directly"""
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"

# Test with HTTPBasicAuth which properly formats the header
auth = HTTPBasicAuth("admin", "admin123")
resp = requests.post(f"{BASE_URL}/api/v1/auth/login", auth=auth)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

if resp.status_code == 200:
    token = resp.json().get("access_token")
    print(f"\nGot token: {token[:20]}...")
    
    # Test protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    chat_resp = requests.post(f"{BASE_URL}/api/v1/chat/", headers=headers, json={"message": "Hello"})
    print(f"\nChat test: {chat_resp.status_code} - {chat_resp.json()}")
