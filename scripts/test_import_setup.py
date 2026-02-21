"""Test data import setup"""
import os
import sys
from pathlib import Path

# Add EVAgent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_import_setup():
    """Test if import script can be loaded and configured"""
    print("Testing data import setup...")
    print("=" * 50)
    
    # Check if config files exist
    jira_config = Path("d:/EVAgent/config/jira_config.yaml")
    confluence_config = Path("d:/EVAgent/config/confluence_config.yaml")
    
    print(f"Jira config exists: {jira_config.exists()}")
    print(f"Confluence config exists: {confluence_config.exists()}")
    
    # Check environment variables
    print(f"\nEnvironment variables:")
    print(f"JIRA_USERNAME: {'Set' if os.getenv('JIRA_USERNAME') else 'Not set'}")
    print(f"JIRA_API_TOKEN: {'Set' if os.getenv('JIRA_API_TOKEN') else 'Not set'}")
    print(f"CONFLUENCE_USERNAME: {'Set' if os.getenv('CONFLUENCE_USERNAME') else 'Not set'}")
    print(f"CONFLUENCE_API_TOKEN: {'Set' if os.getenv('CONFLUENCE_API_TOKEN') else 'Not set'}")
    print(f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    
    # Try to import components
    try:
        from connectors.jira_connector import JiraConnector
        print("[OK] JiraConnector import successful")
    except Exception as e:
        print(f"[FAIL] JiraConnector import failed: {e}")
    
    try:
        from connectors.confluence_connector import ConfluenceConnector
        print("[OK] ConfluenceConnector import successful")
    except Exception as e:
        print(f"[FAIL] ConfluenceConnector import failed: {e}")
    
    try:
        from knowledge.knowledge_base import KnowledgeBase
        print("[OK] KnowledgeBase import successful")
    except Exception as e:
        print(f"[FAIL] KnowledgeBase import failed: {e}")
    
    print("\n" + "=" * 50)
    print("Setup test complete!")
    print("\nNext steps:")
    print("1. Copy config/.env.example to .env")
    print("2. Update .env with your actual credentials")
    print("3. Run: python scripts/import_data.py")

if __name__ == "__main__":
    test_import_setup()
