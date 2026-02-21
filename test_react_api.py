"""Test React frontend connection to simple API"""
import requests
import json

def test_react_connection():
    print("Testing React Frontend Connection...")
    print("=" * 50)
    
    # Test login through React-style endpoint
    data = {"username": "admin", "password": "admin123"}
    
    # Use Basic Auth like React frontend does
    import base64
    credentials = base64.b64encode(f"{data['username']}:{data['password']}".encode()).decode()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {credentials}'
    }
    
    resp = requests.post("http://localhost:8000/api/v1/auth/login", json=data, headers=headers)
    print(f"React-style login status: {resp.status_code}")
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        headers['Authorization'] = f"Bearer {token}"
        
        # Test chat through React-style endpoint
        chat_data = {"message": "EVAgent system architecture"}
        chat_resp = requests.post("http://localhost:8000/api/v1/chat/", json=chat_data, headers=headers)
        print(f"React-style chat status: {chat_resp.status_code}")
        
        if chat_resp.status_code == 200:
            chat_result = chat_resp.json()
            print(f"Chat response:")
            print(json.dumps(chat_result, indent=2))
        else:
            print(f"Chat error: {chat_resp.text}")
    else:
        print(f"Login error: {resp.text}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_react_connection()
