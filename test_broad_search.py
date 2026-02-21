#!/usr/bin/env python3
"""
Test broader Jira search to find the new story.
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

async def test_broad_search():
    try:
        async with aiohttp.ClientSession() as session:
            # Test different JQL queries
            queries = [
                ('', 'All issues (no filter)'),
                ('project is not EMPTY', 'Issues in any project'),
                ('created >= -1h', 'Issues created in last hour'),
                ('updated >= -1h', 'Issues updated in last hour'),
                ('type = Story', 'All stories'),
                ('reporter = currentUser()', 'Issues reported by me'),
                ('assignee = currentUser()', 'Issues assigned to me')
            ]
            
            for jql, description in queries:
                print(f"Testing: {description}")
                print(f"JQL: {jql if jql else '(no filter)'}")
                
                params = {
                    'jql': jql,
                    'maxResults': 10,
                    'fields': 'key,summary,project,reporter,assignee,created,updated,status'
                }
                
                try:
                    url = f'{jira_url}/rest/api/3/search/jql'
                    async with session.get(url, headers=headers, params=params) as response:
                        print(f"  Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            issues = data.get('issues', [])
                            total = data.get('total', 0)
                            
                            print(f"  Total issues: {total}")
                            print(f"  Returned: {len(issues)}")
                            
                            if issues:
                                for issue in issues[:3]:  # Show first 3
                                    key = issue.get('key', 'Unknown')
                                    summary = issue.get('fields', {}).get('summary', 'No summary')
                                    project = issue.get('fields', {}).get('project', {}).get('name', 'No project')
                                    print(f"    - {key}: {summary} (Project: {project})")
                            else:
                                print("  No issues found")
                        else:
                            error_text = await response.text()
                            print(f"  Error: {error_text[:100]}")
                            
                except Exception as e:
                    print(f"  Exception: {e}")
                print()
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(test_broad_search())
