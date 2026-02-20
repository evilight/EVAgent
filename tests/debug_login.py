"""Debug test for login endpoint"""
import requests
import base64

BASE_URL = "http://localhost:8000"

# Test with detailed error printing
credentials = base64.b64encode(b"admin:admin123").decode()
headers = {"Authorization": f"Basic {credentials}"}

try:
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    print(f"Headers: {resp.headers}")
except Exception as e:
    print(f"Error: {e}")
