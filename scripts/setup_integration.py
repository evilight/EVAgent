#!/usr/bin/env python3
"""
EVAgent Setup Script
Guides through configuring Jira/Confluence integration for production use.
"""

import os
import sys
from pathlib import Path

def main():
    print("EVAgent Jira/Confluence Integration Setup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print(" .env file already exists")
        print("Current configuration:")
        with open(".env", "r", encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    print(f"   {line}")
        
        # Check if Jira credentials are configured
        jira_configured = False
        confluence_configured = False
        
        with open(".env", "r", encoding='utf-8') as f:
            for line in f:
                if "JIRA_URL=" in line:
                    jira_configured = True
                elif "CONFLUENCE_URL=" in line:
                    confluence_configured = True
        
        if jira_configured:
            print(" Jira credentials found in .env")
        else:
            print("  Jira credentials not found in .env")
        
        if confluence_configured:
            print(" Confluence credentials found in .env")
        else:
            print("  Confluence credentials not found in .env")
        
        if jira_configured or confluence_configured:
            print()
            print("NEXT STEPS:")
            print("1. Test the integration:")
            print("   python scripts/test_connectors.py")
            print()
            print("SECURITY NOTES:")
            print("   - Never commit API tokens to version control")
            print("   - Use secure credential management")
            print("   - Regularly rotate API tokens")
            print("   - Monitor API usage for unusual activity")
        else:
            print("SETUP REQUIRED:")
            print("1. Add your Jira credentials to .env:")
            print("   JIRA_URL=\"https://your-domain.atlassian.net\"")
            print("   JIRA_USERNAME=\"your-username\"")
            print("   JIRA_API_TOKEN=\"your-api-token\"")
            print()
            print("2. Add your Confluence credentials to .env:")
            print("   CONFLUENCE_URL=\"https://your-domain.atlassian.net/wiki\"")
            print("   CONFLUENCE_USERNAME=\"your-username\"")
            print("   CONFLUENCE_API_TOKEN=\"your-api-token\"")
            print()
            print("3. Set environment variables:")
            print("   - Windows: set JIRA_URL=\"https://your-domain.atlassian.net\"")
            print("   - Mac/Linux: export JIRA_URL=\"https://your-domain.atlassian.net\"")
            print("   - Or add to your system's environment variables")
            print()
            print("4. Test the integration:")
            print("   python scripts/test_connectors.py")
            print()
            print("SECURITY NOTES:")
            print("   - Never commit API tokens to version control")
            print("   - Use secure credential management")
            print("   - Regularly rotate API tokens")
            print("   - Monitor API usage for unusual activity")
    else:
        print(" Creating .env file from template...")
        print("📝 Creating .env file from template...")
        
        # Copy template to .env
        template_file = Path(".env.template")
        if template_file.exists():
            with open(template_file, "r") as f:
                template_content = f.read()
            
            with open(".env", "w") as f:
                f.write(template_content)
            
            print("✅ .env file created from template")
        else:
            print("❌ .env.template file not found")
            print("Please ensure .env.template exists in the current directory")

if __name__ == "__main__":
    main()
