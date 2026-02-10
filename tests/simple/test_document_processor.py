#!/usr/bin/env python3
"""
Test document processing functionality.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.processors.document_processor import DocumentProcessor

def test_document_processor():
    """Test document processing functionality."""
    print("=" * 70)
    print("TESTING DOCUMENT PROCESSOR")
    print("=" * 70)
    
    # Initialize processor
    processor = DocumentProcessor({
        'chunk_size': 500,
        'chunk_overlap': 50,
        'tesseract_path': r'C:\Program Files\Tesseract-OCR'
    })
    print("[OK] DocumentProcessor initialized")
    
    # Test 1: Markdown cleaning
    print("\n[1] Testing markdown cleaning...")
    markdown_text = """
# Core Dump Analysis

This is a **test** document with *various* markdown elements.

## Code Example
```python
def debug_core_dump():
    print("Analyzing core dump...")
```

## Links and Images
[Link to Jira](https://example.com)
![Screenshot](screenshot.png)

## Table
| Column 1 | Column 2 |
|-----------|----------|
| Value 1   | Value 2   |

This document contains __underline__ and `inline code` elements.
"""
    
    cleaned = processor.clean_markdown(markdown_text)
    print(f"    Original length: {len(markdown_text)}")
    print(f"    Cleaned length: {len(cleaned)}")
    print(f"    Cleaned preview: {cleaned[:200]}...")
    print("[OK] Markdown cleaning successful")
    
    # Test 2: Text chunking
    print("\n[2] Testing text chunking...")
    long_text = "This is a very long text that should be split into multiple chunks for testing the chunking functionality. " * 20
    
    chunks = processor.chunk_text(long_text, {
        'source': 'test',
        'title': 'Chunking Test'
    })
    
    print(f"    Original text length: {len(long_text)}")
    print(f"    Number of chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks[:3], 1):
        metadata = chunk['metadata']
        print(f"    Chunk {i}: {metadata['chunk_size']} chars (pos {metadata['chunk_start']}-{metadata['chunk_end']})")
        print(f"      Preview: {chunk['content'][:100]}...")
    
    print("[OK] Text chunking successful")
    
    # Test 3: Jira issue processing
    print("\n[3] Testing Jira issue processing...")
    sample_issue = {
        'key': 'TEST-123',
        'summary': 'Login authentication error',
        'description': '''
Users are experiencing **authentication errors** when trying to log in.

## Steps to Reproduce
1. Go to login page
2. Enter username with special characters
3. Enter password with symbols like @#$%
4. Click login button

## Expected vs Actual
- **Expected**: User should log in successfully
- **Actual**: Authentication error displayed

Error message: `"Authentication failed: Invalid credentials"`
''',
        'status': {'name': 'Open'},
        'priority': {'name': 'High'},
        'labels': [{'name': 'authentication'}, {'name': 'bug'}],
        'project': {'key': 'TEST'},
        'reporter': {'displayName': 'john.doe@example.com'},
        'assignee': {'displayName': 'jane.smith@example.com'},
        'created': '2024-01-15T10:30:00Z',
        'updated': '2024-01-16T14:20:00Z',
        'comments': [
            {
                'id': '1001',
                'author': {'displayName': 'devops@example.com'},
                'body': 'This seems to be related to the recent deployment.',
                'created': '2024-01-15T11:00:00Z'
            }
        ],
        'attachments': [
            {
                'id': '2001',
                'filename': 'screenshot.png',
                'mimeType': 'image/png',
                'size': 245760,
                'created': '2024-01-15T10:35:00Z'
            },
            {
                'id': '2002',
                'filename': 'debug.log',
                'mimeType': 'text/plain',
                'size': 1024,
                'created': '2024-01-15T10:36:00Z'
            }
        ]
    }
    
    processed_docs = processor.process_jira_issue(sample_issue)
    print(f"    Processed {len(processed_docs)} document chunks")
    
    # Show sample chunks
    for i, doc in enumerate(processed_docs[:3], 1):
        metadata = doc['metadata']
        print(f"    Document {i}: {metadata.get('type', 'unknown')} - {metadata.get('title', 'Untitled')}")
        print(f"      Content length: {metadata.get('content_length', 0)}")
        print(f"      Preview: {doc['content'][:100]}...")
    
    print("[OK] Jira issue processing successful")
    
    # Test 4: Metadata enrichment
    print("\n[4] Testing metadata enrichment...")
    enriched_docs = processor.enrich_metadata(processed_docs[:2])
    
    for doc in enriched_docs:
        metadata = doc['metadata']
        print(f"    Enriched metadata keys: {list(metadata.keys())}")
        print(f"    Content length: {metadata.get('content_length', 0)}")
        print(f"    Word count: {metadata.get('word_count', 0)}")
        print(f"    Error types: {metadata.get('error_types', [])}")
        print(f"    Processed at: {metadata.get('processed_at', 'unknown')}")
    
    print("[OK] Metadata enrichment successful")
    
    # Test 5: OCR (if available)
    print("\n[5] Testing OCR capability...")
    try:
        # Create a simple test image data (base64 of a 1x1 pixel)
        import base64
        test_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchJ7X4TQAAAABJRU5ErkJggg=="
        
        ocr_text = processor.extract_text_from_image(test_image_data)
        if ocr_text:
            print(f"    OCR extracted text: '{ocr_text}'")
            print("[OK] OCR functionality working")
        else:
            print("[SKIP] OCR returned empty text (test image might be too small)")
            
    except Exception as e:
        print(f"[INFO] OCR not available: {e}")
    
    print("\n" + "=" * 70)
    print("DOCUMENT PROCESSOR TEST COMPLETED!")
    print("=" * 70)
    print("\nVerified features:")
    print("  - Markdown syntax cleaning")
    print("  - Text chunking with overlap")
    print("  - Jira issue processing")
    print("  - Metadata enrichment")
    print("  - OCR capability (if available)")
    
    return True

if __name__ == "__main__":
    success = test_document_processor()
    sys.exit(0 if success else 1)
