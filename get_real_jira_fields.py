#!/usr/bin/env python3
"""
Get the actual field list from your specific Jira instance.
"""

import asyncio
import aiohttp
import base64
import os
from pathlib import Path

# Load env
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

jira_url = os.getenv('JIRA_URL', '')
jira_username = os.getenv('JIRA_USERNAME', '')
jira_api_token = os.getenv('JIRA_API_TOKEN', '')

# Create auth header
auth_string = f'{jira_username}:{jira_api_token}'
auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

headers = {
    'Authorization': f'Basic {auth_b64}',
    'Accept': 'application/json',
    'User-Agent': 'EVAgent-RAG/1.0'
}

async def get_real_fields():
    try:
        async with aiohttp.ClientSession() as session:
            print("=== GETTING REAL FIELDS FROM YOUR JIRA INSTANCE ===")
            print(f"Jira URL: {jira_url}")
            print()
            
            # Get all fields from your Jira instance
            print("Fetching field metadata...")
            url = f'{jira_url}/rest/api/3/field'
            
            try:
                async with session.get(url, headers=headers, timeout=30) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        fields = await response.json()
                        print(f"Total fields available: {len(fields)}")
                        print()
                        
                        # Categorize fields
                        system_fields = []
                        custom_fields = []
                        
                        for field in fields:
                            field_id = field.get('id', 'Unknown')
                            field_name = field.get('name', 'Unknown')
                            field_type = field.get('schema', {}).get('type', 'Unknown')
                            custom = field.get('custom', False)
                            searchable = field.get('searchable', False)
                            
                            field_info = {
                                'id': field_id,
                                'name': field_name,
                                'type': field_type,
                                'searchable': searchable
                            }
                            
                            if custom:
                                custom_fields.append(field_info)
                            else:
                                system_fields.append(field_info)
                        
                        # Sort by name
                        system_fields.sort(key=lambda x: x['name'])
                        custom_fields.sort(key=lambda x: x['name'])
                        
                        print(f"SYSTEM FIELDS ({len(system_fields)}):")
                        print("=" * 80)
                        
                        for field in system_fields:
                            searchable_mark = "SEARCHABLE" if field['searchable'] else "NOT SEARCHABLE"
                            print(f"{searchable_mark:12} | {field['id']:25} | {field['name']:30} | {field['type']}")
                        
                        print()
                        print(f"CUSTOM FIELDS ({len(custom_fields)}):")
                        print("=" * 80)
                        
                        for field in custom_fields[:20]:  # Show first 20 custom fields
                            searchable_mark = "SEARCHABLE" if field['searchable'] else "NOT SEARCHABLE"
                            print(f"{searchable_mark:12} | {field['id']:25} | {field['name']:30} | {field['type']}")
                        
                        if len(custom_fields) > 20:
                            print(f"... and {len(custom_fields) - 20} more custom fields")
                        
                        print()
                        print("=== RECOMMENDED FIELDS FOR SYNC ===")
                        
                        # Recommend fields based on what's actually available
                        recommended = []
                        
                        # Core system fields to always include
                        core_system_ids = ['summary', 'description', 'status', 'priority', 'assignee', 'reporter', 'created', 'updated', 'project', 'issuetype']
                        
                        print("CORE FIELDS (always include):")
                        for field_id in core_system_ids:
                            matching = [f for f in system_fields if f['id'] == field_id]
                            if matching:
                                field = matching[0]
                                recommended.append(field_id)
                                print(f"  AVAILABLE {field_id} - {field['name']} ({field['type']})")
                            else:
                                print(f"  MISSING   {field_id} - NOT AVAILABLE")
                        
                        print()
                        print("ADDITIONAL USEFUL FIELDS:")
                        additional_fields = ['components', 'labels', 'fixVersions', 'versions', 'resolution', 'resolutiondate', 'duedate', 'environment', 'attachment', 'comment']
                        
                        for field_id in additional_fields:
                            matching = [f for f in system_fields if f['id'] == field_id]
                            if matching:
                                field = matching[0]
                                recommended.append(field_id)
                                print(f"  AVAILABLE {field_id} - {field['name']} ({field['type']})")
                        
                        print()
                        print("RELEVANT CUSTOM FIELDS:")
                        # Look for useful custom fields
                        useful_custom = []
                        for field in custom_fields:
                            field_name_lower = field['name'].lower()
                            if any(keyword in field_name_lower for keyword in ['sprint', 'story', 'epic', 'team', 'release', 'build', 'test', 'review']):
                                useful_custom.append(field)
                                recommended.append(field['id'])
                                print(f"  AVAILABLE {field['id']} - {field['name']} ({field['type']})")
                        
                        print()
                        print("=== FINAL RECOMMENDED FIELD LIST ===")
                        print(f"Total recommended fields: {len(recommended)}")
                        print("Field string for API:")
                        field_string = ','.join(recommended)
                        print(field_string)
                        
                        print()
                        print("=== UPDATE RECOMMENDATION ===")
                        print("Update your sync service with this field string:")
                        print(f"'fields': '{field_string}'")
                        
                    else:
                        error_text = await response.text()
                        print(f"Error: {response.status}")
                        print(f"Details: {error_text}")
                        
            except asyncio.TimeoutError:
                print("Timeout: Request took too long")
            except Exception as e:
                print(f"Exception: {e}")
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(get_real_fields())
