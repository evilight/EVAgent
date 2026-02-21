"""Setup environment variables for Jira and Confluence connections"""
import os
from pathlib import Path

def setup_env_file():
    """Create .env file with required environment variables"""
    
    env_file = Path("d:/EVAgent/.env")
    
    # Check if .env already exists
    if env_file.exists():
        print("⚠️  .env file already exists. Please update it manually.")
        return False
    
    env_content = """# Jira Configuration
JIRA_USERNAME=your_jira_username
JIRA_API_TOKEN=your_jira_api_token

# Confluence Configuration  
CONFLUENCE_USERNAME=your_confluence_username
CONFLUENCE_API_TOKEN=your_confluence_api_token

# OpenAI Configuration (for LLM)
OPENAI_API_KEY=your_openai_api_key
"""
    
    try:
        env_file.write_text(env_content)
        print("✅ Created .env file at d:/EVAgent/.env")
        print("\n📝 Please update the .env file with your actual credentials:")
        print("   1. JIRA_USERNAME and JIRA_API_TOKEN")
        print("   2. CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN") 
        print("   3. OPENAI_API_KEY (for LLM functionality)")
        print("\n🔗 How to get API tokens:")
        print("   Jira: https://id.atlassian.com/manage-profile/security/api-tokens")
        print("   Confluence: https://id.atlassian.com/manage-profile/security/api-tokens")
        print("   OpenAI: https://platform.openai.com/api-keys")
        return True
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

if __name__ == "__main__":
    setup_env_file()
