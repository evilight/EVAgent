#!/usr/bin/env python3
"""
Detailed debug test for Jira authentication.
"""

import os
import sys
from pathlib import Path
import asyncio
import base64
import aiohttp

# Add EVAgent src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

async def debug_jira_auth():
    """Debug Jira authentication in detail."""
    print("=" * 60)
    print("EVAgent Jira Authentication Debug")
    print("=" * 60)
    print()
    
    # Load environment variables from .env file
    def load_env_from_file():
        """Load environment variables from .env file."""
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value

    # Load environment variables
    load_env_from_file()

    jira_url = os.getenv('JIRA_URL', '')
    jira_username = os.getenv('JIRA_USERNAME', '')
    jira_api_token = os.getenv('JIRA_API_TOKEN', '')
    
    print("1. Configuration Check:")
    print(f"   Jira URL: {jira_url}")
    print(f"   Jira Username: {jira_username}")
    print(f"   Jira Token Length: {len(jira_api_token)}")
    print(f"   Jira Token Last 4: {jira_api_token[-4:] if jira_api_token else 'None'}")
    
    # Create auth header
    auth_string = f"{jira_username}:{jira_api_token}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    print(f"   Auth String Length: {len(auth_string)}")
    print(f"   Auth B64 Length: {len(auth_b64)}")
    print(f"   Auth B64 Prefix: {auth_b64[:20]}...")
    
    # Test different endpoints
    endpoints_to_test = [
        "/rest/api/3/myself",
        "/rest/api/2/serverInfo",
        "/rest/api/3/project"
    ]
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Accept': 'application/json',
        'User-Agent': 'EVAgent-RAG/1.0'
    }
    
    print()
    print("2. Testing Different Endpoints:")
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_test:
            url = f"{jira_url}{endpoint}"
            print(f"   Testing: {url}")
            
            try:
                async with session.get(url, headers=headers) as response:
                    print(f"     Status: {response.status}")
                    print(f"     Headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"     Response: {str(data)[:100]}...")
                        except:
                            text = await response.text()
                            print(f"     Response: {text[:100]}...")
                    else:
                        error_text = await response.text()
                        print(f"     Error: {error_text[:200]}...")
                        
            except Exception as e:
                print(f"     Exception: {e}")
            
            print()
    
    print("3. Testing with curl-like request:")
    try:
        # Test with different approach
        import urllib.request
        import json
        
        req = urllib.request.Request(f"{jira_url}/rest/api/3/myself")
        req.add_header('Authorization', f'Basic {auth_b64}')
        req.add_header('Accept', 'application/json')
        req.add_header('User-Agent', 'EVAgent-RAG/1.0')
        
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            print(f"   urllib Status: {status}")
            if status == 200:
                data = json.loads(response.read().decode())
                print(f"   urllib Response: {str(data)[:100]}...")
                
    except Exception as e:
        print(f"   urllib Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_jira_auth())
