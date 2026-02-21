#!/usr/bin/env python3
"""
Test Jira permissions and endpoints.
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

print("=== JIRA PERMISSIONS TEST ===")
print(f"JIRA URL: {jira_url}")
print(f"JIRA Username: {jira_username}")
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

async def test_permissions():
    try:
        async with aiohttp.ClientSession() as session:
            # Test various endpoints to identify permission requirements
            endpoints = [
                ('/rest/api/2/serverInfo', 'Public server info'),
                ('/rest/api/3/project', 'Project list'),
                ('/rest/api/3/search/jql?jql=project+is+not+EMPTY&maxResults=5', 'Public issues'),
                ('/rest/api/3/mypermissions?permissions=BROWSE_PROJECTS', 'User permissions'),
                ('/rest/api/3/myself', 'User profile')
            ]
            
            for endpoint, description in endpoints:
                url = f'{jira_url}{endpoint}'
                print(f"Testing: {description}")
                print(f"URL: {url}")
                
                try:
                    async with session.get(url, headers=headers) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            if 'serverTitle' in data:
                                print(f"  SUCCESS Server: {data.get('serverTitle')}")
                            elif isinstance(data, list):
                                print(f"  SUCCESS Found {len(data)} items")
                            elif 'permissions' in data:
                                print(f"  SUCCESS Permissions loaded")
                            elif 'displayName' in data:
                                print(f"  SUCCESS User: {data.get('displayName')}")
                            else:
                                print(f"  SUCCESS Success")
                        else:
                            error_text = await response.text()
                            print(f"  ERROR Status: {response.status} - {error_text[:100]}")
                            
                except Exception as e:
                    print(f"  ERROR Exception: {e}")
                print()
                    
    except Exception as e:
        print(f"Fatal exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_permissions())
