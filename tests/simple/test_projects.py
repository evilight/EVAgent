#!/usr/bin/env python3
"""Test to check available projects in Jira."""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def main():
    print("=== Jira Projects Test ===")
    
    # Get credentials
    username = os.getenv('JIRA_USERNAME')
    api_token = os.getenv('JIRA_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set JIRA_USERNAME and JIRA_API_TOKEN environment variables")
        return
    
    try:
        from src.utils import ConfigLoader
        from src.connectors import JiraConnector
        
        # Load configuration
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("jira_config")
        jira_config = config.get('jira', {})
        
        print(f"Connecting to: {jira_config.get('url')}")
        print(f"Username: {jira_config.get('username')}")
        print()
        
        connector = JiraConnector(jira_config)
        
        async with connector:
            print("SUCCESS: Connection successful!")
            
            # Test 1: Get projects
            try:
                projects_url = f"{jira_config['url']}/rest/api/3/project"
                projects_result = await connector._make_request('GET', projects_url)
                
                print(f"\nFound {len(projects_result)} projects:")
                for project in projects_result:
                    print(f"  - {project.get('key')}: {project.get('name')}")
                
            except Exception as e:
                print(f"Failed to get projects: {e}")
            
            # Test 2: Try old search API
            try:
                print(f"\nTesting old search API...")
                old_search_url = f"{jira_config['url']}/rest/api/3/search"
                search_params = {
                    'jql': 'order by created DESC',
                    'maxResults': 5
                }
                old_result = await connector._make_request('GET', old_search_url, params=search_params)
                print(f"SUCCESS: Old API works! Found {len(old_result.get('issues', []))} issues")
                
            except Exception as e:
                print(f"Old API failed: {e}")
            
            # Test 3: Try new search API with different payload
            try:
                print(f"\nTesting new search API...")
                new_search_url = f"{jira_config['url']}/rest/api/3/search/jql"
                
                # Try different payload formats
                payloads = [
                    {'jql': 'order by created DESC', 'maxResults': 5},
                    {"jql": "order by created DESC", "maxResults": 5},
                    {'jql': 'order by created DESC'}
                ]
                
                for i, payload in enumerate(payloads):
                    try:
                        print(f"  Trying payload format {i+1}: {payload}")
                        new_result = await connector._make_request('POST', new_search_url, data=payload)
                        print(f"SUCCESS: New API works with format {i+1}! Found {len(new_result.get('issues', []))} issues")
                        break
                    except Exception as e:
                        print(f"  Format {i+1} failed: {e}")
                
            except Exception as e:
                print(f"New API failed: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
