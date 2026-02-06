#!/usr/bin/env python3
"""Test Confluence API discovery - find working endpoints."""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
import base64

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_endpoint(session, base_url, endpoint, headers):
    """Test a single endpoint."""
    url = f"{base_url}{endpoint}"
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                return True, data
            else:
                text = await response.text()
                return False, f"Status {response.status}: {text[:100]}"
    except Exception as e:
        return False, str(e)


async def main():
    print("=== Confluence API Discovery ===")
    
    username = os.getenv('CONFLUENCE_USERNAME')
    api_token = os.getenv('CONFLUENCE_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN")
        return
    
    # Test both URL formats
    base_urls = [
        "https://evilight.atlassian.net/wiki",
        "https://evilight.atlassian.net",
    ]
    
    # Common Confluence API endpoints
    endpoints = [
        "/rest/api/2/myself",
        "/rest/api/2/user/current",
        "/rest/api/2/spaces",
        "/rest/api/2/content",
        "/rest/api/2/search",
        "/rest/api/v2/myself",
        "/rest/api/v2/spaces",
        "/rest/api/v2/content",
        "/rest/api/latest/myself",
        "/rest/api/latest/spaces",
        "/rest/api/3/myself",
        "/rest/api/3/spaces",
        "/rest/atlassian-connect/1/addons",
    ]
    
    auth_string = f"{username}:{api_token}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Accept': 'application/json',
        'User-Agent': 'EVAgent-RAG/1.0'
    }
    
    async with aiohttp.ClientSession() as session:
        for base_url in base_urls:
            print(f"\nTesting base URL: {base_url}")
            print("=" * 60)
            
            found_working = False
            for endpoint in endpoints:
                success, result = await test_endpoint(session, base_url, endpoint, headers)
                status = "[OK] WORKING" if success else "[X] Failed"
                print(f"  {endpoint:<45} {status}")
                
                if success:
                    found_working = True
                    print(f"    Response: {str(result)[:100]}...")
            
            if found_working:
                print(f"\n[OK] Found working endpoints for {base_url}")
            else:
                print(f"\n[X] No working endpoints found for {base_url}")
    
    print("\n" + "=" * 60)
    print("Discovery complete!")


if __name__ == "__main__":
    asyncio.run(main())
