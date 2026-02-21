#!/usr/bin/env python3
"""
Very simple test script for Jira and Confluence connectors.
Tests basic connectivity with minimal requirements.
"""

import os
import sys
from pathlib import Path
import asyncio
import logging

# Add EVAgent src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import services
try:
    from src.connectors.jira_connector import JiraConnector
    from src.connectors.confluence_connector import ConfluenceConnector
except ImportError as e:
    print(f"Failed to import connectors: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

async def test_basic_connectors():
    """Test basic connectivity with real configuration."""
    print("=" * 60)
    print("EVAgent Basic Connector Test")
    print("=" * 60)
    print()
    
    # Load environment variables from .env file
    def load_env_from_file():
        """Load environment variables from .env file."""
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value
                        print(f"Loaded: {key}")

    # Load environment variables
    load_env_from_file()

    # Configuration
    jira_url = os.getenv('JIRA_URL', '')
    jira_username = os.getenv('JIRA_USERNAME', '')
    jira_api_token = os.getenv('JIRA_API_TOKEN', '')
    
    confluence_url = os.getenv('CONFLUENCE_URL', '')
    confluence_username = os.getenv('CONFLUENCE_USERNAME', '')
    confluence_api_token = os.getenv('CONFLUENCE_API_TOKEN', '')
    
    print("1. Checking configuration...")
    if jira_url:
        print(f"   Jira URL: {jira_url}")
        print(f"   Jira Username: {jira_username}")
        print(f"   Jira Token: {'*' * (len(jira_api_token) - 4) + jira_api_token[-4:] if jira_api_token else 'None'}")
    else:
        print("   Jira URL: Not configured")
    
    if confluence_url:
        print(f"   Confluence URL: {confluence_url}")
        print(f"   Confluence Username: {confluence_username}")
        print(f"   Confluence Token: {'*' * (len(confluence_api_token) - 4) + confluence_api_token[-4:] if confluence_api_token else 'None'}")
    else:
        print("   Confluence URL: Not configured")
    
    if not jira_url and not confluence_url:
        print("ERROR: No Jira or Confluence URLs configured")
        return False
    
    print()
    print("2. Testing basic HTTP connectivity...")
    
    # Test Jira basic connectivity
    if jira_url:
        try:
            import aiohttp
            headers = {
                'Authorization': f'Basic {__import__("base64").b64encode(f"{jira_username}:{jira_api_token}".encode()).decode()}',
                'Accept': 'application/json',
                'User-Agent': 'EVAgent-RAG/1.0'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{jira_url}/rest/api/3/myself", headers=headers) as response:
                    if response.status == 200:
                        print("   Jira: HTTP connection successful")
                    else:
                        print(f"   Jira: HTTP connection failed with status {response.status}")
        except Exception as e:
            print(f"   Jira: HTTP connection error: {e}")
    
    # Test Confluence basic connectivity
    if confluence_url:
        try:
            headers = {
                'Authorization': f'Basic {__import__("base64").b64encode(f"{confluence_username}:{confluence_api_token}".encode()).decode()}',
                'Accept': 'application/json',
                'User-Agent': 'EVAgent-RAG/1.0'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{confluence_url}/rest/api/content", headers=headers) as response:
                    if response.status == 200:
                        print("   Confluence: HTTP connection successful")
                    else:
                        print(f"   Confluence: HTTP connection failed with status {response.status}")
        except Exception as e:
            print(f"   Confluence: HTTP connection error: {e}")
    
    print()
    print("3. Summary:")
    print("   Basic HTTP connectivity test completed")
    print("   If HTTP connections work but API tests fail, check authentication tokens")
    print("   If HTTP connections fail, check network connectivity and URLs")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_basic_connectors())
