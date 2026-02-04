#!/usr/bin/env python3
"""Simple configuration test."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    print("=== Simple Config Test ===")
    
    # Check environment variables
    print("Environment Variables:")
    print(f"  JIRA_USERNAME: {repr(os.getenv('JIRA_USERNAME', 'NOT_SET'))}")
    print(f"  JIRA_API_TOKEN: {repr(os.getenv('JIRA_API_TOKEN', 'NOT_SET'))}")
    print()
    
    # Test manual substitution
    print("=== Manual Substitution Test ===")
    yaml_content = '''jira:
  url: "https://evilight.atlassian.net/jira"
  username: "${JIRA_USERNAME}"
  api_token: "${JIRA_API_TOKEN}"'''
    
    print("Original YAML:")
    print(yaml_content)
    print()
    
    # Simple manual substitution
    username = os.getenv('JIRA_USERNAME', '').strip().strip('"\'')
    api_token = os.getenv('JIRA_API_TOKEN', '').strip().strip('"\'')
    
    substituted = yaml_content.replace('${JIRA_USERNAME}', username).replace('${JIRA_API_TOKEN}', api_token)
    
    print("After substitution:")
    print(substituted)
    print()
    
    # Try to parse with YAML
    try:
        import yaml
        config = yaml.safe_load(substituted)
        print("SUCCESS: YAML parsing successful!")
        print(f"  URL: {config['jira']['url']}")
        print(f"  Username: {config['jira']['username']}")
        print(f"  API Token: {'*' * len(config['jira']['api_token']) if config['jira']['api_token'] else 'EMPTY'}")
    except Exception as e:
        print(f"ERROR: YAML parsing failed: {e}")
    
    print()
    
    # Test with ConfigLoader
    print("=== ConfigLoader Test ===")
    try:
        from src.utils import ConfigLoader
        # Use absolute path to config directory
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("jira_config")
        print("SUCCESS: ConfigLoader successful!")
        print(f"  Config keys: {list(config.keys())}")
        jira_config = config.get('jira', {})
        print(f"  URL: {jira_config.get('url', 'NOT_FOUND')}")
        print(f"  Username: {jira_config.get('username', 'NOT_FOUND')}")
        print(f"  Projects: {jira_config.get('projects', [])}")
    except Exception as e:
        print(f"ERROR: ConfigLoader failed: {e}")

if __name__ == "__main__":
    main()
