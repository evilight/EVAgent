#!/usr/bin/env python3
"""Test different API formats for Jira search."""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def main():
    print("=== Jira API Format Test ===")
    
    # Get credentials
    username = os.getenv('JIRA_USERNAME')
    api_token = os.getenv('JIRA_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set JIRA_USERNAME and JIRA_API_TOKEN environment variables")
        return
    
    try:
        from src.utils import ConfigLoader
        from src.connectors import JiraConnector
        import aiohttp
        
        # Load configuration
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("jira_config")
        jira_config = config.get('jira', {})
        
        connector = JiraConnector(jira_config)
        
        async with connector:
            print("Connection successful!")
            
            # Test different approaches
            base_url = jira_config['url']
            
            # 1. Try the old search endpoint with GET
            try:
                print("\n1. Testing old GET search...")
                url = f"{base_url}/rest/api/3/search"
                params = {
                    'jql': 'project = EVAgent',
                    'maxResults': 3
                }
                headers = connector._get_default_headers()
                
                async with connector.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"SUCCESS: Old GET works! Found {len(result.get('issues', []))} issues")
                        for issue in result.get('issues', []):
                            print(f"  - {issue.get('key')}: {issue.get('fields', {}).get('summary', 'No summary')}")
                    else:
                        print(f"FAILED: {response.status} - {await response.text()}")
                        
            except Exception as e:
                print(f"ERROR: {e}")
            
            # 2. Try the new search endpoint with different payload formats
            new_url = f"{base_url}/rest/api/3/search/jql"
            headers = connector._get_default_headers()
            headers['Content-Type'] = 'application/json'
            
            payloads = [
                # Format 1: Simple JQL
                {'jql': 'project = EVAgent'},
                
                # Format 2: JQL with maxResults
                {'jql': 'project = EVAgent', 'maxResults': 3},
                
                # Format 3: Full payload
                {
                    'jql': 'project = EVAgent',
                    'startAt': 0,
                    'maxResults': 3,
                    'fields': ['summary', 'status', 'created']
                },
                
                # Format 4: Minimal payload
                {"jql": "project = EVAgent", "maxResults": 3}
            ]
            
            for i, payload in enumerate(payloads, 1):
                try:
                    print(f"\n{i+1}. Testing new POST search with format {i}:")
                    print(f"   Payload: {json.dumps(payload, indent=2)}")
                    
                    async with connector.session.post(new_url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            print(f"SUCCESS: Format {i} works! Found {len(result.get('issues', []))} issues")
                            break
                        else:
                            error_text = await response.text()
                            print(f"FAILED: {response.status} - {error_text}")
                            
                except Exception as e:
                    print(f"ERROR: {e}")
                    
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
