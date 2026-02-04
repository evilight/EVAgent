#!/usr/bin/env python3
"""Debug script to check configuration loading."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils import ConfigLoader

def main():
    print("=== Configuration Debug ===")
    
    # Check environment variables
    print(f"JIRA_USERNAME: {repr(os.getenv('JIRA_USERNAME', 'NOT_SET'))}")
    print(f"JIRA_API_TOKEN: {repr(os.getenv('JIRA_API_TOKEN', 'NOT_SET'))}")
    print()
    
    # Read raw YAML content
    config_path = Path("config/jira_config.yaml")
    if config_path.exists():
        print("=== Raw YAML Content ===")
        with open(config_path, 'r') as f:
            raw_content = f.read()
        print(repr(raw_content))
        print()
        
        print("=== YAML Content (visible) ===")
        print(raw_content)
        print()
        
        # Test environment variable substitution
        config_loader = ConfigLoader("config")
        
        print("=== After Environment Substitution ===")
        substituted_content = config_loader._substitute_env_vars(raw_content)
        print(repr(substituted_content))
        print()
        
        print("=== Substituted Content (visible) ===")
        print(substituted_content)
        print()
        
        # Try to load the config
        try:
            config = config_loader.load_config("jira_config")
            print("✅ Config loaded successfully!")
            print(f"URL: {config.get('jira', {}).get('url', 'NOT_FOUND')}")
            print(f"Username: {config.get('jira', {}).get('username', 'NOT_FOUND')}")
        except Exception as e:
            print(f"❌ Error loading config: {e}")
    else:
        print(f"❌ Config file not found: {config_path}")

if __name__ == "__main__":
    main()
