#!/usr/bin/env python3
"""Test Jira authentication."""

import os
import sys
import base64
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    print("=== Jira Authentication Test ===")
    
    # Get credentials
    username = os.getenv('JIRA_USERNAME')
    api_token = os.getenv('JIRA_API_TOKEN')
    
    print(f"Username: {username}")
    print(f"API Token: {'*' * len(api_token) if api_token else 'None'}")
    print()
    
    if not username or not api_token:
        print("ERROR: Please set JIRA_USERNAME and JIRA_API_TOKEN environment variables")
        return
    
    # Test Basic Auth encoding
    auth_string = f"{username}:{api_token}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    print(f"Auth string length: {len(auth_string)}")
    print(f"Auth header: Basic {auth_header[:20]}...")
    print()
    
    # Test with ConfigLoader
    try:
        from src.utils import ConfigLoader
        # Use absolute path to config directory
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("jira_config")
        jira_config = config.get('jira', {})
        
        print("Loaded configuration:")
        print(f"  URL: {jira_config.get('url')}")
        print(f"  Username: {jira_config.get('username')}")
        print(f"  API Token: {'*' * len(jira_config.get('api_token', ''))}")
        print()
        
        # Test the actual connector
        import asyncio
        from src.connectors import JiraConnector
        
        async def test_connection():
            connector = JiraConnector(jira_config)
            try:
                await connector.connect()
                print("SUCCESS: Connection established!")
                
                # Test a simple API call
                result = await connector._make_request(
                    'GET', 
                    f"{jira_config['url']}/rest/api/3/myself"
                )
                print(f"User info: {result.get('displayName', 'Unknown')}")
                print(f"Email: {result.get('emailAddress', 'Unknown')}")
                
            except Exception as e:
                print(f"ERROR: {e}")
            finally:
                await connector.disconnect()
        
        asyncio.run(test_connection())
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
