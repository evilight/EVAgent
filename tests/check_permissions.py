#!/usr/bin/env python3
"""
Check Jira permissions and available projects.
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

async def check_permissions():
    try:
        async with aiohttp.ClientSession() as session:
            print("=== JIRA PERMISSIONS AND PROJECTS CHECK ===")
            print(f"User: {jira_username}")
            print(f"URL: {jira_url}")
            print()
            
            # Test 1: Check what we can access
            print("1. Testing accessible endpoints:")
            endpoints = [
                ('/rest/api/2/serverInfo', 'Server info'),
                ('/rest/api/3/project', 'Projects'),
                ('/rest/api/3/issue/createmeta', 'Issue creation metadata'),
                ('/rest/api/3/search/jql?jql=project+is+not+EMPTY&maxResults=1', 'Search access')
            ]
            
            for endpoint, description in endpoints:
                url = f'{jira_url}{endpoint}'
                print(f"  {description}: ", end="")
                
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'serverTitle' in data:
                                print(f"SUCCESS {data.get('serverTitle')}")
                            elif isinstance(data, list):
                                print(f"SUCCESS {len(data)} items")
                            elif 'projects' in data:
                                projects = data.get('projects', [])
                                print(f"SUCCESS {len(projects)} projects")
                                if projects:
                                    print(f"    Projects: {[p.get('name', 'Unknown') for p in projects[:3]]}")
                            else:
                                print(f"SUCCESS Access granted")
                        else:
                            error_text = await response.text()
                            print(f"ERROR {response.status}")
                            
                except Exception as e:
                    print(f"ERROR Exception: {e}")
            
            print()
            
            # Test 2: Try specific project searches
            print("2. Testing common project keys:")
            common_keys = ['PROJ', 'DEV', 'TEST', 'DEMO', 'WEB', 'API', 'APP']
            
            for key in common_keys:
                url = f'{jira_url}/rest/api/3/project/{key}'
                print(f"  Project {key}: ", end="")
                
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"SUCCESS {data.get('name', 'Unknown')}")
                        elif response.status == 404:
                            print("ERROR Not found")
                        else:
                            print(f"ERROR {response.status}")
                            
                except Exception as e:
                    print(f"ERROR Exception: {e}")
            
            print()
            
            # Test 3: Try to find any issues with different approaches
            print("3. Testing issue search approaches:")
            search_tests = [
                ('created >= -24h', 'Last 24 hours'),
                ('updated >= -24h', 'Updated last 24h'),
                ('status != Done', 'Not done issues'),
                ('priority in (High, Medium)', 'High/Medium priority')
            ]
            
            for jql, description in search_tests:
                params = {'jql': jql, 'maxResults': 5}
                url = f'{jira_url}/rest/api/3/search/jql'
                
                print(f"  {description}: ", end="")
                
                try:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            total = data.get('total', 0)
                            print(f"SUCCESS {total} issues")
                            if total > 0:
                                issues = data.get('issues', [])
                                for issue in issues[:1]:
                                    key = issue.get('key', 'Unknown')
                                    summary = issue.get('fields', {}).get('summary', 'No summary')
                                    print(f"    Example: {key} - {summary[:50]}")
                        else:
                            print(f"ERROR {response.status}")
                            
                except Exception as e:
                    print(f"ERROR Exception: {e}")
            
            print()
            print("=== RECOMMENDATIONS ===")
            print("If no issues are found:")
            print("1. Check if the story was created in a project you have access to")
            print("2. Verify your API token has 'Browse projects' permission")
            print("3. Try creating a test issue in an accessible project")
            print("4. Check Jira project permissions for your user")
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(check_permissions())
