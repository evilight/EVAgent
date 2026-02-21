#!/usr/bin/env python3
"""
Check what Jira fields are available.
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

async def check_fields():
    try:
        async with aiohttp.ClientSession() as session:
            print("=== JIRA FIELDS ANALYSIS ===")
            print()
            
            # Current fields being retrieved
            print("1. CURRENT FIELDS IN SYNC SERVICE:")
            current_fields = ['key', 'summary', 'updated', 'status']
            print(f"   Fields: {current_fields}")
            print(f"   Count: {len(current_fields)}")
            print()
            
            # Test 1: Get all available field metadata
            print("2. AVAILABLE JIRA FIELDS:")
            try:
                url = f'{jira_url}/rest/api/3/field'
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        fields = await response.json()
                        print(f"   Total available fields: {len(fields)}")
                        print()
                        
                        # Group fields by type
                        system_fields = []
                        custom_fields = []
                        
                        for field in fields:
                            field_name = field.get('name', 'Unknown')
                            field_id = field.get('id', 'Unknown')
                            custom = field.get('custom', False)
                            
                            if custom:
                                custom_fields.append((field_id, field_name))
                            else:
                                system_fields.append((field_id, field_name))
                        
                        print("   SYSTEM FIELDS (important ones):")
                        important_system = [
                            ('id', 'ID'),
                            ('key', 'Key'),
                            ('summary', 'Summary'),
                            ('description', 'Description'),
                            ('status', 'Status'),
                            ('priority', 'Priority'),
                            ('assignee', 'Assignee'),
                            ('reporter', 'Reporter'),
                            ('created', 'Created'),
                            ('updated', 'Updated'),
                            ('resolution', 'Resolution'),
                            ('resolutiondate', 'Resolution Date'),
                            ('project', 'Project'),
                            ('issuetype', 'Issue Type'),
                            ('components', 'Components'),
                            ('labels', 'Labels'),
                            ('environment', 'Environment'),
                            ('duedate', 'Due Date'),
                            ('votes', 'Votes'),
                            ('watches', 'Watches'),
                            ('attachment', 'Attachments'),
                            ('comment', 'Comments'),
                            ('worklog', 'Work Logs'),
                            ('timeoriginalestimate', 'Original Estimate'),
                            ('timeestimate', 'Remaining Estimate'),
                            ('timespent', 'Time Spent'),
                            ('fixVersions', 'Fix Versions'),
                            ('versions', 'Affects Versions'),
                            ('sprint', 'Sprint')
                        ]
                        
                        for field_id, field_name in important_system:
                            matching = [f for f in system_fields if f[0] == field_id]
                            if matching:
                                print(f"     ✅ {field_id} - {field_name}")
                            else:
                                print(f"     ❌ {field_id} - {field_name} (not available)")
                        
                        print()
                        print(f"   CUSTOM FIELDS: {len(custom_fields)} available")
                        if custom_fields[:5]:  # Show first 5
                            for field_id, field_name in custom_fields[:5]:
                                print(f"     📝 {field_id} - {field_name}")
                        if len(custom_fields) > 5:
                            print(f"     ... and {len(custom_fields) - 5} more")
                        
                    else:
                        print(f"   Error getting fields: {response.status}")
                        
            except Exception as e:
                print(f"   Exception: {e}")
            
            print()
            
            # Test 2: Recommended fields for comprehensive sync
            print("3. RECOMMENDED FIELDS FOR COMPREHENSIVE SYNC:")
            recommended_fields = [
                # Basic fields
                'id', 'key', 'summary', 'description',
                # Status and workflow
                'status', 'priority', 'resolution', 'resolutiondate',
                # People
                'assignee', 'reporter',
                # Dates
                'created', 'updated', 'duedate',
                # Project context
                'project', 'issuetype', 'components', 'labels',
                # Content
                'attachment', 'comment',
                # Time tracking
                'timeoriginalestimate', 'timeestimate', 'timespent', 'worklog',
                # Versions
                'fixVersions', 'versions',
                # Agile (if available)
                'sprint'
            ]
            
            print(f"   Recommended count: {len(recommended_fields)}")
            print(f"   Fields: {recommended_fields}")
            print()
            
            # Test 3: Current vs recommended comparison
            print("4. CURRENT vs RECOMMENDED:")
            missing_fields = [f for f in recommended_fields if f not in current_fields]
            extra_fields = [f for f in current_fields if f not in recommended_fields]
            
            print(f"   Missing important fields: {len(missing_fields)}")
            if missing_fields:
                print(f"   {missing_fields}")
            
            print(f"   Extra fields: {len(extra_fields)}")
            if extra_fields:
                print(f"   {extra_fields}")
            
            print()
            print("=== RECOMMENDATION ===")
            print("Update sync service to use comprehensive field list:")
            print("  'fields': 'key,summary,description,status,priority,assignee,reporter,created,updated,project,issuetype,components,labels,attachment,comment'")
            print()
            print("This will provide rich data for your knowledge base!")
                    
    except Exception as e:
        print(f'Fatal: {e}')

if __name__ == "__main__":
    asyncio.run(check_fields())
