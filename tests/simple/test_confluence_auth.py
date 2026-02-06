#!/usr/bin/env python3
"""Test Confluence authentication and connection."""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def main():
    print("=== Confluence Authentication Test ===")
    
    # Get credentials
    username = os.getenv('CONFLUENCE_USERNAME')
    api_token = os.getenv('CONFLUENCE_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN environment variables")
        return
    
    print(f"Username: {username}")
    print(f"API Token: {'*' * len(api_token)}")
    print()
    
    try:
        from src.utils import ConfigLoader
        from src.connectors import ConfluenceConnector
        
        # Load configuration
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("confluence_config")
        confluence_config = config.get('confluence', {})
        
        print("Loaded configuration:")
        print(f"  URL: {confluence_config.get('url')}")
        print(f"  Username: {confluence_config.get('username')}")
        print(f"  API Token: {'*' * len(confluence_config.get('api_token', ''))}")
        print()
        
        # Test the actual connector
        connector = ConfluenceConnector(confluence_config)
        
        async with connector:
            print("SUCCESS: Connection established!")
            
            # Test getting content to verify API works
            content_url = f"{confluence_config['url']}/rest/api/content"
            content_response = await connector._make_request('GET', content_url, params={'limit': 1})
            
            print(f"API Test successful!")
            print(f"Total content items: {content_response.get('size', 0)}")
            print(f"Results found: {len(content_response.get('results', []))}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
