#!/usr/bin/env python3
"""
Check current user permissions and accessible projects.
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
            print("=== CHECKING YOUR JIRA PERMISSIONS ===")
            print(f"User: {jira_username}")
            print(f"URL: {jira_url}")
            print()
            
            # Test 1: Try to get user info (might work even without project access)
            print("1. Testing user access:")
            try:
                url = f'{jira_url}/rest/api/3/user/search'
                params = {'query': jira_username}
                
                async with session.get(url, headers=headers, params=params) as response:
                    print(f"   User search status: {response.status}")
                    if response.status == 200:
                        users = await response.json()
                        if users:
                            user = users[0]
                            print(f"   ✅ Found user: {user.get('displayName', 'Unknown')}")
                            print(f"   ✅ Email: {user.get('emailAddress', 'Unknown')}")
                            print(f"   ✅ Active: {user.get('active', 'Unknown')}")
                        else:
                            print("   ❌ User not found")
                    else:
                        print(f"   ❌ Cannot search users")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            print()
            
            # Test 2: Try different project endpoints
            print("2. Testing project access methods:")
            
            endpoints_to_try = [
                ('/rest/api/3/project', 'All projects'),
                ('/rest/api/3/project/search', 'Search projects'),
                ('/rest/api/3/project/recent', 'Recent projects'),
                ('/rest/api/3/project/type?excludeSubtasks=true', 'Project types')
            ]
            
            for endpoint, description in endpoints_to_try:
                url = f'{jira_url}{endpoint}'
                print(f"   {description}: ", end="")
                
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list):
                                print(f"✅ {len(data)} items")
                                if data and len(data) <= 3:
                                    for item in data[:3]:
                                        name = item.get('name', 'Unknown')
                                        key = item.get('key', 'Unknown')
                                        print(f"      - {key}: {name}")
                            elif 'values' in data:
                                values = data.get('values', [])
                                print(f"✅ {len(values)} items")
                            else:
                                print(f"✅ Access granted")
                        else:
                            print(f"❌ {response.status}")
                            
                except Exception as e:
                    print(f"❌ Exception: {e}")
            
            print()
            
            # Test 3: Try to find issues with broader search
            print("3. Testing issue search with different approaches:")
            
            search_tests = [
                ('', 'All issues (if allowed)'),
                ('creator = currentUser()', 'Issues you created'),
                ('reporter = currentUser()', 'Issues you reported'),
                ('watcher = currentUser()', 'Issues you watch'),
                ('commented by currentUser()', 'Issues you commented on')
            ]
            
            for jql, description in search_tests:
                if jql:
                    params = {'jql': jql, 'maxResults': 5}
                    url = f'{jira_url}/rest/api/3/search/jql'
                else:
                    params = {'maxResults': 5}
                    url = f'{jira_url}/rest/api/3/search'
                
                print(f"   {description}: ", end="")
                
                try:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'issues' in data:
                                issues = data.get('issues', [])
                                total = data.get('total', 0)
                                print(f"✅ {total} issues found")
                                if issues:
                                    for issue in issues[:2]:
                                        key = issue.get('key', 'Unknown')
                                        print(f"      - {key}")
                            else:
                                print(f"✅ Access granted")
                        else:
                            print(f"❌ {response.status}")
                            
                except Exception as e:
                    print(f"❌ Exception: {e}")
            
            print()
            print("=== RECOMMENDATIONS ===")
            print("If you still can't access projects:")
            print("1. Go to Jira and look for 'Administration' or 'Settings'")
            print("2. Check if you're a site admin or need admin help")
            print("3. Try creating a new project you own")
            print("4. Contact your Jira administrator for project access")
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(check_permissions())
