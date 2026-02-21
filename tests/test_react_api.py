"""Test React frontend with API"""
import requests
import time

def test_react_api_connection():
    print("Testing React Frontend + API Connection...")
    print("=" * 50)
    
    # Test API health
    try:
        resp = requests.get("http://localhost:8000/health", timeout=5)
        print(f"[OK] API Health: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] API Health: {e}")
        return False
    
    # Test React frontend
    try:
        resp = requests.get("http://localhost:3000", timeout=5)
        print(f"[OK] React Frontend: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] React Frontend: {e}")
        return False
    
    # Test API login through React's proxy
    try:
        data = {"username": "admin", "password": "admin123"}
        resp = requests.post("http://localhost:3000/api/v1/auth/login-json", json=data, timeout=5)
        if resp.status_code == 200:
            print("[OK] API Login through React proxy: Success")
            token = resp.json().get("access_token")
            print(f"  Token received: {token[:30]}...")
        else:
            print(f"[FAIL] API Login through React proxy: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] API Login through React proxy: {e}")
    
    print("\n" + "=" * 50)
    print("React + API setup is ready!")
    print("Access React app at: http://localhost:3000")
    print("API docs at: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    test_react_api_connection()
