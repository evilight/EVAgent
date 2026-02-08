#!/usr/bin/env python3
"""
Test script to fetch markdown file from Jira SCRUM-5 and convert to plain text for embedding.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
import tempfile
import re

# Add project root to path (parent of src)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import as absolute package imports
from src.connectors.jira_connector import JiraConnector

# Check for required environment variables
if not os.environ.get('JIRA_USERNAME'):
    print("ERROR: JIRA_USERNAME environment variable not set")
    print("Please set: $env:JIRA_USERNAME='your-email'")
    sys.exit(1)

if not os.environ.get('JIRA_API_TOKEN'):
    print("ERROR: JIRA_API_TOKEN environment variable not set")
    print("Please set: $env:JIRA_API_TOKEN='your-token'")
    sys.exit(1)


def clean_markdown_to_text(markdown_content: str) -> str:
    """
    Convert markdown content to clean plain text for embedding.
    
    Args:
        markdown_content: Raw markdown content
        
    Returns:
        Cleaned plain text
    """
    if not markdown_content:
        return ""
    
    # Remove markdown syntax
    text = markdown_content
    
    # Remove headers (# ## ### etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic (*text*, **text**, __text__)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic*
    text = re.sub(r'__(.*?)__', r'\1', text)      # __bold__
    text = re.sub(r'_(.*?)_', r'\1', text)        # _italic_
    
    # Remove inline code (`code`)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove code blocks (```code```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove links [text](url) -> keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove images ![alt](url) -> keep alt text
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    
    # Remove blockquotes (> text)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules (---, ***)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove list markers (-, *, 1., 2.)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullet lists
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)     # numbered lists
    
    # Remove table syntax
    text = re.sub(r'\|.*?\|', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-\s]{3,}$', '', text, flags=re.MULTILINE)  # table separators
    
    # Remove extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # multiple newlines to double
    text = re.sub(r'[ \t]+', ' ', text)       # multiple spaces to single
    text = text.strip()
    
    return text


async def fetch_and_process_markdown():
    """Fetch markdown file from SCRUM-5 and convert to plain text."""
    
    print("=" * 70)
    print("JIRA MARKDOWN TEST - Fetching SCRUM-5 markdown file")
    print("=" * 70)
    
    # Jira configuration
    jira_config = {
        'url': 'https://evilight.atlassian.net',
        'username': os.environ.get('JIRA_USERNAME'),
        'api_token': os.environ.get('JIRA_API_TOKEN'),
        'api': {'version': '3'},
        'rate_limit': {
            'requests_per_second': 10,
            'burst_size': 10
        }
    }
    
    print(f"\n[1] Connecting to Jira at {jira_config['url']}...")
    
    # Initialize connector
    connector = JiraConnector(jira_config)
    
    try:
        # Connect to Jira
        await connector.connect()
        print("[OK] Connected to Jira successfully")
        
        # Fetch SCRUM-5 issue
        print("\n[2] Fetching SCRUM-5 issue...")
        issue = await connector.get_issue_details('SCRUM-5', fields=['*all'])
        
        print(f"[OK] Issue found: {issue.get('key', 'N/A')}")
        print(f"    Summary: {issue.get('fields', {}).get('summary', 'N/A')}")
        
        # Get attachments
        attachments = issue.get('fields', {}).get('attachment', [])
        
        if not attachments:
            print("[ERROR] No attachments found on SCRUM-5")
            return
        
        print(f"\n[3] Found {len(attachments)} attachment(s):")
        
        markdown_files = []
        
        for i, attachment in enumerate(attachments, 1):
            filename = attachment.get('filename', 'unknown')
            mime_type = attachment.get('mimeType', 'unknown')
            size = attachment.get('size', 0)
            
            print(f"\n    {i}. {filename}")
            print(f"       Type: {mime_type}")
            print(f"       Size: {size} bytes")
            
            # Check if it's a markdown file
            if mime_type in ['text/markdown', 'text/x-markdown'] or filename.lower().endswith(('.md', '.markdown')):
                markdown_files.append(attachment)
        
        if not markdown_files:
            print("[ERROR] No markdown files found in attachments")
            return
        
        # Process each markdown file
        for i, attachment in enumerate(markdown_files, 1):
            filename = attachment.get('filename', f'markdown_{i}.md')
            print(f"\n[4] Processing markdown file: {filename}")
            
            # Download attachment
            content_url = attachment.get('content')
            if content_url:
                print(f"[5] Downloading {filename}...")
                content = await connector.download_attachment(content_url)
                print(f"[OK] Downloaded {len(content)} bytes")
                
                # Decode markdown content
                try:
                    markdown_text = content.decode('utf-8')
                    print(f"[OK] Successfully decoded UTF-8 content")
                except UnicodeDecodeError:
                    # Try other encodings
                    for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                        try:
                            markdown_text = content.decode(encoding)
                            print(f"[OK] Successfully decoded with {encoding}")
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        print("[ERROR] Could not decode content")
                        continue
                
                # Save original markdown
                with tempfile.NamedTemporaryFile(
                    suffix=f"_{filename}", 
                    delete=False,
                    mode='w',
                    encoding='utf-8'
                ) as md_file:
                    md_file.write(markdown_text)
                    md_path = md_file.name
                
                print(f"[OK] Original markdown saved to: {md_path}")
                
                # Convert to plain text
                print(f"\n[6] Converting markdown to plain text...")
                plain_text = clean_markdown_to_text(markdown_text)
                
                # Save plain text
                with tempfile.NamedTemporaryFile(
                    suffix=f"_{filename.replace('.md', '.txt')}", 
                    delete=False,
                    mode='w',
                    encoding='utf-8'
                ) as txt_file:
                    txt_file.write(plain_text)
                    txt_path = txt_file.name
                
                print(f"[OK] Plain text saved to: {txt_path}")
                
                # Display content summary
                print(f"\n[7] Content Summary:")
                print(f"    Original markdown: {len(markdown_text)} characters")
                print(f"    Plain text: {len(plain_text)} characters")
                print(f"    Reduction: {len(plain_text)/len(markdown_text)*100:.1f}% of original")
                
                print("\n" + "=" * 70)
                print("PLAIN TEXT PREVIEW (first 500 chars):")
                print("=" * 70)
                print(plain_text[:500] + ("..." if len(plain_text) > 500 else ""))
                print("=" * 70)
                
                # Save both files for embedding usage
                print(f"\n[8] Files ready for embedding:")
                print(f"    Original: {md_path}")
                print(f"    Plain text: {txt_path}")
                
            else:
                print("[ERROR] No content URL for attachment")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await connector.disconnect()
        print("\n[OK] Connection closed")


def main():
    """Main entry point."""
    print("Starting JIRA Markdown Processing Test...")
    print(f"Python: {sys.version}")
    print(f"Working directory: {Path.cwd()}")
    
    # Run async test
    asyncio.run(fetch_and_process_markdown())
    
    print("\nTest completed!")


if __name__ == '__main__':
    main()
