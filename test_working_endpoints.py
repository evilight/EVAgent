#!/usr/bin/env python3
"""
Test working Jira endpoints.
"""

import asyncio
import aiohttp
import base64
import os
from pathlib import Path

# Load env
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

# Create auth header
auth_string = f'{jira_username}:{jira_api_token}'
auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

headers = {
    'Authorization': f'Basic {auth_b64}',
    'Accept': 'application/json',
    'User-Agent': 'EVAgent-RAG/1.0'
}

async def test_working_endpoints():
    try:
        async with aiohttp.ClientSession() as session:
            # Test working endpoints
            endpoints = [
                '/rest/api/2/serverInfo',
                '/rest/api/3/project',
                '/rest/api/3/search/jql?jql=project+is+not+EMPTY&maxResults=5'
            ]
            
            for endpoint in endpoints:
                url = f'{jira_url}{endpoint}'
                print(f'Testing: {endpoint}')
                
                try:
                    async with session.get(url, headers=headers) as response:
                        print(f'  Status: {response.status}')
                        if response.status == 200:
                            data = await response.json()
                            if 'serverTitle' in data:
                                print(f'  Server: {data.get("serverTitle")}')
                            elif isinstance(data, list):
                                print(f'  Items: {len(data)}')
                            else:
                                print(f'  Success')
                        else:
                            print(f'  Failed')
                except Exception as e:
                    print(f'  Error: {e}')
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(test_working_endpoints())
