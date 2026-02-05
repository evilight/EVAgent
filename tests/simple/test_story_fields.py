#!/usr/bin/env python3
"""Test script to list all fields of a Jira story/issue."""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def main():
    print("=== Jira Story Fields Explorer ===")
    
    # Get credentials
    username = os.getenv('JIRA_USERNAME')
    api_token = os.getenv('JIRA_API_TOKEN')
    
    if not username or not api_token:
        print("ERROR: Please set JIRA_USERNAME and JIRA_API_TOKEN environment variables")
        return
    
    try:
        from src.utils import ConfigLoader
        from src.connectors import JiraConnector
        
        # Load configuration
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("jira_config")
        jira_config = config.get('jira', {})
        
        connector = JiraConnector(jira_config)
        
        async with connector:
            print("Connection successful!")
            print(f"Jira URL: {jira_config['url']}")
            print()
            
            # Search for issues in the SCRUM project
            print("Searching for issues in project SCRUM...")
            search_result = await connector.search_issues(
                jql="project = SCRUM ORDER BY created DESC",
                max_results=5
            )
            
            issues = search_result.get('issues', [])
            
            if not issues:
                print("No issues found in project SCRUM")
                return
            
            print(f"Found {len(issues)} issues\n")
            
            # The new API returns minimal data (just 'id'), so we need to fetch details
            print("Fetching detailed information for each issue...")
            print()
            
            detailed_issues = []
            for issue in issues:
                issue_id = issue.get('id')
                if issue_id:
                    try:
                        # Fetch full issue details
                        details = await connector.get_issue_details(issue_id)
                        detailed_issues.append(details)
                    except Exception as e:
                        print(f"  Warning: Could not fetch details for issue {issue_id}: {e}")
            
            if not detailed_issues:
                print("ERROR: Could not fetch detailed information for any issues")
                return
            
            # Get the first detailed issue and list all its fields
            first_issue = detailed_issues[0]
            issue_key = first_issue.get('key', 'Unknown')
            
            print(f"=" * 60)
            print(f"Issue: {issue_key}")
            print(f"=" * 60)
            print()
            
            # List all top-level fields
            print("Top-level fields:")
            print("-" * 40)
            for field_name in sorted(first_issue.keys()):
                field_value = first_issue[field_name]
                value_type = type(field_value).__name__
                
                # Show preview of the value
                if isinstance(field_value, dict):
                    preview = f"{{{len(field_value)} sub-fields}}"
                elif isinstance(field_value, list):
                    preview = f"[{len(field_value)} items]"
                elif isinstance(field_value, str):
                    preview = f"\"{field_value[:50]}{'...' if len(str(field_value)) > 50 else ''}\""
                else:
                    preview = str(field_value)[:50]
                
                print(f"  {field_name:<25} ({value_type:<10}) : {preview}")
            
            print()
            
            # If there's a 'fields' key, explore it in detail
            if 'fields' in first_issue:
                fields = first_issue['fields']
                print(f"Detailed 'fields' section ({len(fields)} sub-fields):")
                print("-" * 60)
                
                for field_name in sorted(fields.keys()):
                    field_value = fields[field_name]
                    value_type = type(field_value).__name__
                    
                    # Format the value for display
                    if field_value is None:
                        display_value = "null"
                    elif isinstance(field_value, dict):
                        # For dict, show the keys
                        keys = list(field_value.keys())[:5]
                        display_value = f"dict with keys: {', '.join(keys)}"
                        if len(field_value) > 5:
                            display_value += f" (+{len(field_value)-5} more)"
                    elif isinstance(field_value, list):
                        display_value = f"list[{len(field_value)} items]"
                        if field_value and len(field_value) > 0:
                            first_item = field_value[0]
                            if isinstance(first_item, dict) and 'name' in first_item:
                                names = [item.get('name', 'N/A') for item in field_value[:3]]
                                display_value += f" -> {', '.join(names)}"
                                if len(field_value) > 3:
                                    display_value += f" (+{len(field_value)-3})"
                    elif isinstance(field_value, str):
                        display_value = field_value.replace('\n', ' ')[:80]
                        if len(field_value) > 80:
                            display_value += "..."
                    else:
                        display_value = str(field_value)
                    
                    print(f"  {field_name:<30} ({value_type:<10}): {display_value}")
            
            print()
            print("=" * 60)
            print("Summary:")
            print("=" * 60)
            print(f"Total top-level fields: {len(first_issue.keys())}")
            if 'fields' in first_issue:
                print(f"Total fields in 'fields' section: {len(first_issue['fields'].keys())}")
            print()
            
            # List all other issues briefly
            if len(detailed_issues) > 1:
                print("Other issues found:")
                for issue in detailed_issues[1:]:
                    key = issue.get('key', 'Unknown')
                    fields = issue.get('fields', {})
                    summary = fields.get('summary', 'No summary') if isinstance(fields, dict) else 'No fields'
                    issue_type = fields.get('issuetype', {}).get('name', 'Unknown') if isinstance(fields, dict) else 'Unknown'
                    print(f"  - {key} [{issue_type}]: {summary[:50]}")
            
            # Save full issue details to file for reference
            output_file = Path(__file__).parent / "story_fields_output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(first_issue, f, indent=2, ensure_ascii=False, default=str)
            print(f"\nFull issue details saved to: {output_file}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
