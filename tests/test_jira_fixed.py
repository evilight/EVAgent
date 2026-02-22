#!/usr/bin/env python3
"""
Fixed Jira API test - addresses the issues found in comprehensive debug
"""

import asyncio
import aiohttp
import base64
import os
import json
from pathlib import Path

# Load environment variables
env_file = Path(__file__).parent.parent / '.env'
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

print("=== FIXED JIRA API TEST ===")
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

async def test_fixed_jira_api():
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
            
            print("\n2. TESTING CORRECTED SEARCH ENDPOINTS")
            print("=" * 50)
            
            # Use the correct search endpoint with JQL
            search_tests = [
                ('/rest/api/3/search/jql?jql=project+is+not+EMPTY&maxResults=5', 'All issues (any project)'),
                ('/rest/api/3/search/jql?jql=project=SCRUM&maxResults=5', 'SCRUM project issues'),
                ('/rest/api/3/search/jql?jql=project=EVAgent&maxResults=5', 'EVAgent project issues'),
                ('/rest/api/3/search/jql?jql=assignee=currentUser()&maxResults=5', 'Issues assigned to me'),
                ('/rest/api/3/search/jql?jql=reporter=currentUser()&maxResults=5', 'Issues reported by me'),
                ('/rest/api/3/search/jql?jql=text+~+test&maxResults=5', 'Issues containing "test"'),
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
                            
                            for i, issue in enumerate(issues[:3]):
                                key = issue.get('key', 'Unknown')
                                fields = issue.get('fields', {})
                                summary = fields.get('summary', 'No summary')
                                project = fields.get('project', {})
                                project_name = project.get('name', 'Unknown')
                                project_key = project.get('key', 'Unknown')
                                print(f"  Issue {i+1}: {key}")
                                print(f"    Project: {project_name} ({project_key})")
                                print(f"    Summary: {summary[:60]}")
                                
                                # Extract project info from first issue
                                if i == 0 and project_key != 'Unknown':
                                    print(f"    [INFO] Found project key: {project_key}")
                        else:
                            error_text = await response.text()
                            print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                            
                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
            
            print("\n3. TESTING USER PERMISSIONS (CORRECTED)")
            print("=" * 50)
            
            try:
                # Test without permissions parameter first
                url = f'{jira_url}/rest/api/3/mypermissions'
                async with session.get(url, headers=headers) as response:
                    print(f"All Permissions Status: {response.status}")
                    
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
                        
                # Test with specific permissions
                url = f'{jira_url}/rest/api/3/mypermissions?permissions=BROWSE_PROJECTS'
                async with session.get(url, headers=headers) as response:
                    print(f"Browse Projects Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        permissions = data.get('permissions', [])
                        for perm in permissions:
                            if perm.get('name') == 'BROWSE_PROJECTS':
                                have = perm.get('have', False)
                                print(f"  BROWSE_PROJECTS: {have}")
                                break
                    else:
                        error_text = await response.text()
                        print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                        
            except Exception as e:
                print(f"[ERROR] Exception: {e}")
            
            print("\n4. TESTING PROJECT ALTERNATIVE ENDPOINTS")
            print("=" * 50)
            
            # Try alternative project endpoints
            project_tests = [
                ('/rest/api/3/project/recent', 'Recent projects'),
                ('/rest/api/3/project/type?excludeSubtasks=true', 'Project types'),
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
                                print(f"[OK] Found {len(data)} items")
                                for i, item in enumerate(data[:2]):
                                    if isinstance(item, dict):
                                        name = item.get('name', 'Unknown')
                                        print(f"  Item {i+1}: {name}")
                            elif isinstance(data, dict):
                                values = data.get('values', [])
                                print(f"[OK] Found {len(values)} items (paginated)")
                                for i, item in enumerate(values[:2]):
                                    name = item.get('name', 'Unknown')
                                    print(f"  Item {i+1}: {name}")
                            else:
                                print(f"[OK] Got response: {type(data)}")
                        else:
                            error_text = await response.text()
                            print(f"[ERROR] Error: {response.status} - {error_text[:200]}")
                            
                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
            
            print("\n5. SUMMARY AND RECOMMENDATIONS")
            print("=" * 50)
            print("Based on the test results:")
            print("1. If you see 0 projects but can access in browser:")
            print("   - Your API token may lack 'BROWSE_PROJECTS' permission")
            print("   - You might not be a member of the project")
            print("   - The project might be using different permissions")
            print()
            print("2. Next steps to fix:")
            print("   - Generate a new API token at: https://id.atlassian.com/manage-profile/security/api-tokens")
            print("   - Ensure token has 'Jira API' permissions")
            print("   - Ask project admin to add you as a member")
            print("   - Try accessing the project directly in browser to verify")
            print()
            print("3. If issues are found but projects aren't:")
            print("   - Use issue search results to extract project info")
            print("   - The project access might be indirect through issues")
            print("   - Consider using issue-based approach instead")
                    
    except Exception as e:
        print(f"Fatal exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_fixed_jira_api())
