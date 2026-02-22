#!/usr/bin/env python3
"""
Comprehensive Jira API debugging script
"""

import asyncio
import aiohttp
import base64
import os
import json
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

print("=== COMPREHENSIVE JIRA API DEBUG ===")
print(f"JIRA URL: {jira_url}")
print(f"JIRA Username: {jira_username}")
print(f"JIRA Token Length: {len(jira_api_token)}")
print()

# Create auth header
auth_string = f'{jira_username}:{jira_api_token}'
auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

headers = {
    'Authorization': f'Basic {auth_b64}',
    'Accept': 'application/json',
    'User-Agent': 'EVAgent-RAG/1.0'
}

async def debug_jira_api():
    try:
        async with aiohttp.ClientSession() as session:
            print("1. TESTING BASIC AUTHENTICATION")
            print("=" * 50)
            
            # Test basic auth with serverInfo
            try:
                async with session.get(f'{jira_url}/rest/api/2/serverInfo', headers=headers) as response:
                    print(f"Server Info Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"[OK] Server: {data.get('serverTitle')}")
                        print(f"[OK] Version: {data.get('version')}")
                    else:
                        print(f"[ERROR] Auth failed: {response.status}")
                        return
            except Exception as e:
                print(f"[ERROR] Exception: {e}")
                return
            
            print("\n2. TESTING PROJECT ACCESS")
            print("=" * 50)
            
            # Test different project endpoints
            project_tests = [
                ('/rest/api/3/project', 'All projects (API v3)'),
                ('/rest/api/2/project', 'All projects (API v2)'),
                ('/rest/api/3/project/search', 'Project search'),
                ('/rest/api/3/project/accessible', 'Accessible projects'),
            ]
            
            for endpoint, desc in project_tests:
                try:
                    url = f'{jira_url}{endpoint}'
                    print(f"\nTesting: {desc}")
                    print(f"URL: {url}")
                    
                    async with session.get(url, headers=headers) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list):
                                print(f"[OK] Found {len(data)} projects")
                                for i, project in enumerate(data[:3]):
                                    key = project.get('key', 'Unknown')
                                    name = project.get('name', 'Unknown')
                                    print(f"  Project {i+1}: {name} (key: {key})")
                            elif isinstance(data, dict):
                                if 'values' in data:
                                    values = data.get('values', [])
                                    print(f"[OK] Found {len(values)} projects (paginated)")
                                    for i, project in enumerate(values[:3]):
                                        key = project.get('key', 'Unknown')
                                        name = project.get('name', 'Unknown')
                                        print(f"  Project {i+1}: {name} (key: {key})")
                                else:
                                    print(f"[OK] Got response: {list(data.keys())}")
                            else:
                                print(f"[OK] Unexpected format: {type(data)}")
                        else:
                            error_text = await response.text()
                            print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                            
                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
            
            print("\n3. TESTING SPECIFIC PROJECT ACCESS")
            print("=" * 50)
            
            # Test the specific project we know exists
            specific_tests = [
                ('/rest/api/3/project/10000', 'Project by ID 10000'),
                ('/rest/api/3/project/SCRUM', 'Project by key SCRUM'),
                ('/rest/api/3/project/EVAgent', 'Project by name EVAgent'),
            ]
            
            for endpoint, desc in specific_tests:
                try:
                    url = f'{jira_url}{endpoint}'
                    print(f"\nTesting: {desc}")
                    print(f"URL: {url}")
                    
                    async with session.get(url, headers=headers) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            key = data.get('key', 'Unknown')
                            name = data.get('name', 'Unknown')
                            print(f"[OK] Project: {name} (key: {key})")
                        else:
                            error_text = await response.text()
                            print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                            
                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
            
            print("\n4. TESTING ISSUE SEARCH")
            print("=" * 50)
            
            # Test issue search with different JQL queries
            search_tests = [
                ('/rest/api/3/search?jql=project=SCRUM&maxResults=3', 'Issues in SCRUM project'),
                ('/rest/api/3/search?jql=project=10000&maxResults=3', 'Issues in project 10000'),
                ('/rest/api/3/search?jql=project=EVAgent&maxResults=3', 'Issues in EVAgent project'),
                ('/rest/api/3/search?jql=assignee=currentUser()&maxResults=3', 'Issues assigned to me'),
                ('/rest/api/3/search?jql=reporter=currentUser()&maxResults=3', 'Issues reported by me'),
            ]
            
            for endpoint, desc in search_tests:
                try:
                    url = f'{jira_url}{endpoint}'
                    print(f"\nTesting: {desc}")
                    print(f"URL: {url}")
                    
                    async with session.get(url, headers=headers) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            issues = data.get('issues', [])
                            total = data.get('total', 0)
                            print(f"[OK] Found {total} issues, showing {len(issues)}")
                            
                            for i, issue in enumerate(issues[:2]):
                                key = issue.get('key', 'Unknown')
                                summary = issue.get('fields', {}).get('summary', 'No summary')
                                print(f"  Issue {i+1}: {key} - {summary[:50]}")
                        else:
                            error_text = await response.text()
                            print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                            
                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
            
            print("\n5. TESTING USER PERMISSIONS")
            print("=" * 50)
            
            try:
                url = f'{jira_url}/rest/api/3/mypermissions'
                async with session.get(url, headers=headers) as response:
                    print(f"Permissions Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        permissions = data.get('permissions', [])
                        print(f"[OK] Found {len(permissions)} permissions")
                        
                        # Check specific permissions
                        key_permissions = ['BROWSE_PROJECTS', 'VIEW_ISSUES', 'CREATE_ISSUES']
                        for perm in permissions:
                            perm_name = perm.get('name', '')
                            if perm_name in key_permissions:
                                have = perm.get('have', False)
                                print(f"  {perm_name}: {have}")
                    else:
                        error_text = await response.text()
                        print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                        
            except Exception as e:
                print(f"[ERROR] Exception: {e}")
            
            print("\n6. RECOMMENDATIONS")
            print("=" * 50)
            print("If you're seeing 0 projects but can access projects in browser:")
            print("1. Check if your API token has the right scopes")
            print("2. Verify you're using the correct email/username")
            print("3. Try generating a new API token with full permissions")
            print("4. Check if you need to be added as a project member")
            print("5. Verify the project is not archived or hidden")
                    
    except Exception as e:
        print(f"Fatal exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_jira_api())
