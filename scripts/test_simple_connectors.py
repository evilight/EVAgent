#!/usr/bin/env python3
"""
Simple test script for Jira and Confluence connectors.
Tests basic connectivity without requiring ChromaDB.
"""

import os
import sys
from pathlib import Path
import asyncio
import logging
from datetime import datetime

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
    print("Please ensure all required packages are installed:")
    print("   - pip install aiohttp requests")
    print("   - Check that src/connectors/ directory exists")
    print("   - Verify that connector files are in place")
    sys.exit(1)

logger = logging.getLogger(__name__)

async def test_simple_connectors():
    """Test Jira and Confluence connectors with real configuration."""
    print("=" * 60)
    print("EVAgent Simple Connector Test")
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
    config = {
        'jira_url': os.getenv('JIRA_URL', ''),
        'jira_username': os.getenv('JIRA_USERNAME', ''),
        'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
        'confluence_url': os.getenv('CONFLUENCE_URL', ''),
        'confluence_username': os.getenv('CONFLUENCE_USERNAME', ''),
        'confluence_api_token': os.getenv('CONFLUENCE_API_TOKEN', ''),
        'confluence_space': os.getenv('CONFLUENCE_SPACE', ''),
    }
    
    # Check environment variables
    missing_vars = []
    if not config['jira_url']:
        missing_vars.append('JIRA_URL')
    if not config['jira_username']:
        missing_vars.append('JIRA_USERNAME')
    if not config['jira_api_token']:
        missing_vars.append('JIRA_API_TOKEN')
    
    if missing_vars:
        print("Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("Please set the following environment variables:")
        print("set JIRA_URL=\"https://your-domain.atlassian.net\"")
        print("set JIRA_USERNAME=\"your-username\"")
        print("set JIRA_API_TOKEN=\"your-api-token\"")
        print()
        return False
    
    try:
        # Create connectors
        jira_connector = JiraConnector({
            'url': config['jira_url'],
            'username': config['jira_username'],
            'api_token': config['jira_api_token'],
            'api': {'version': '3'}
        })
        
        confluence_connector = ConfluenceConnector({
            'url': config['confluence_url'],
            'username': config['confluence_username'],
            'api_token': config['confluence_api_token'],
            'api': {'version': '2'}
        })
        
        print("1. Testing Jira connection...")
        try:
            jira_result = await jira_connector._test_connection()
            print(f"   Jira result type: {type(jira_result)}")
            print(f"   Jira result: {jira_result}")
            print(f"   Jira result.get('status'): {jira_result.get('status')}")
        except Exception as e:
            print(f"   Jira test exception: {e}")
            jira_result = {"status": "error", "message": str(e)}
        
        print("2. Testing Confluence connection...")
        try:
            confluence_result = await confluence_connector._test_connection()
            print(f"   Confluence result type: {type(confluence_result)}")
            print(f"   Confluence result: {confluence_result}")
            print(f"   Confluence result.get('status'): {confluence_result.get('status')}")
        except Exception as e:
            print(f"   Confluence test exception: {e}")
            confluence_result = {"status": "error", "message": str(e)}
        
        if jira_result['status'] == 'success' or confluence_result['status'] == 'success':
            print()
            print("3. Testing Jira data retrieval...")
            try:
                jira_projects = await jira_connector.get_projects()
                print(f"   Projects found: {len(jira_projects)}")
                if jira_projects:
                    print(f"   First project: {jira_projects[0].get('name', 'Unknown')}")
            except Exception as e:
                print(f"   Error retrieving projects: {e}")
            
            print("4. Testing Confluence data retrieval...")
            try:
                confluence_spaces = await confluence_connector.get_spaces()
                print(f"   Spaces found: {len(confluence_spaces)}")
                if confluence_spaces:
                    print(f"   First space: {confluence_spaces[0].get('name', 'Unknown')}")
            except Exception as e:
                print(f"   Error retrieving spaces: {e}")
            
            print()
            print("SUCCESS: All connectors are working!")
            return True
        else:
            print("ERROR: No connectors are properly configured")
            return False
                
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_simple_connectors())
