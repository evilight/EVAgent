#!/usr/bin/env python3
"""Test Confluence pages - fetch first 3 pages."""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def main():
    print("=== Confluence Pages Test ===")
    
    # Get credentials
    username = os.getenv('CONFLUENCE_USERNAME')
    api_token = os.getenv('CONFLUENCE_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN environment variables")
        return
    
    try:
        from src.utils import ConfigLoader
        from src.connectors import ConfluenceConnector
        
        # Load configuration
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("confluence_config")
        confluence_config = config.get('confluence', {})
        
        connector = ConfluenceConnector(confluence_config)
        
        async with connector:
            print("Connection successful!")
            print(f"Confluence URL: {confluence_config['url']}")
            print()
            
            # Fetch content directly (without spaces endpoint)
            print("Fetching content from Confluence...")
            print("-" * 60)
            
            content_url = f"{confluence_config['url']}/rest/api/content"
            content_response = await connector._make_request('GET', content_url, params={'limit': 3, 'expand': 'history'})
            
            pages = content_response.get('results', [])
            
            if not pages:
                print("No pages found!")
                return
            
            print(f"Found {len(pages)} pages:\n")
            
            # Display first 3 pages
            for i, page in enumerate(pages[:3], 1):
                page_id = page.get('id', 'N/A')
                page_title = page.get('title', 'No title')
                page_status = page.get('status', 'unknown')
                page_type = page.get('type', 'unknown')
                
                print(f"{i}. {page_title}")
                print(f"   ID: {page_id}")
                print(f"   Status: {page_status}")
                print(f"   Type: {page_type}")
                
                # Get history info if available
                history = page.get('history', {})
                if history:
                    created_by = history.get('createdBy', {}).get('displayName', 'Unknown')
                    created_date = history.get('createdDate', 'Unknown')
                    print(f"   Created by: {created_by} on {created_date}")
                
                print()
            
            # Save full details to file
            output_file = Path(__file__).parent / "confluence_pages_output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(pages[:3], f, indent=2, ensure_ascii=False, default=str)
            print(f"Full page details saved to: {output_file}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
