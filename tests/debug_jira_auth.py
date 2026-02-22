#!/usr/bin/env python3
"""
Debug Jira authentication issue.
"""

import asyncio
import aiohttp
import base64
import os
from pathlib import Path

# Load environment variables
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

jira_url = os.getenv('JIRA_URL', '')
jira_username = os.getenv('JIRA_USERNAME', '')
jira_api_token = os.getenv('JIRA_API_TOKEN', '')

print("=== JIRA AUTHENTICATION DEBUG ===")
print(f"JIRA URL: {jira_url}")
print(f"JIRA Username: {jira_username}")
print(f"JIRA Token Length: {len(jira_api_token)}")
print(f"JIRA Token Last 4: {jira_api_token[-4:]}")
print()

# Create auth header
auth_string = f'{jira_username}:{jira_api_token}'
auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

headers = {
    'Authorization': f'Basic {auth_b64}',
    'Accept': 'application/json',
    'User-Agent': 'EVAgent-RAG/1.0'
}

print(f"Auth String Length: {len(auth_string)}")
print(f"Auth B64 Length: {len(auth_b64)}")
print(f"Auth B64 Prefix: {auth_b64[:20]}...")
print()

async def test_auth():
    try:
        async with aiohttp.ClientSession() as session:
            # Test both endpoints
            endpoints = [
                ('/rest/api/2/serverInfo', 'Public endpoint'),
                ('/rest/api/3/myself', 'User-specific endpoint')
            ]
            
            for endpoint, description in endpoints:
                url = f'{jira_url}{endpoint}'
                print(f"Testing: {url} ({description})")
                
                async with session.get(url, headers=headers) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        if 'serverTitle' in data:
                            print(f"  Server: {data.get('serverTitle', 'Unknown')}")
                        elif 'displayName' in data:
                            print(f"  User: {data.get('displayName', 'Unknown')}")
                    else:
                        error_text = await response.text()
                        print(f"  Error: {error_text[:200]}")
                    print()
                    
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
