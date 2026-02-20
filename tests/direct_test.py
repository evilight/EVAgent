"""Direct test for login-json endpoint"""
import requests

BASE_URL = "http://localhost:8000"

# Test if the endpoint exists
data = {"username": "admin", "password": "admin123"}
resp = requests.post(f"{BASE_URL}/api/v1/auth/login-json", json=data)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

# Also check the docs to see registered routes
docs = requests.get(f"{BASE_URL}/openapi.json")
if docs.status_code == 200:
    spec = docs.json()
    paths = list(spec.get('paths', {}).keys())
    print(f"\nRegistered paths: {paths}")
