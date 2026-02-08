#!/usr/bin/env python3
"""
Test script to fetch image from Jira SCRUM-5 and extract text using OCR.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
import tempfile

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

# Try to import OCR libraries
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
    print("[OK] OCR libraries available (Pillow + pytesseract)")
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"[WARNING] OCR libraries not available: {e}")
    print("To install: pip install pillow pytesseract")
    print("Also need Tesseract OCR installed: https://github.com/UB-Mannheim/tesseract/wiki")

# Try to find Tesseract executable
TESSERACT_PATH = None
if OCR_AVAILABLE:
    # Common Tesseract installation paths
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract\tesseract.exe",
        "tesseract"  # Assume it's in PATH
    ]
    
    for path in possible_paths:
        try:
            if path == "tesseract":
                # Check if tesseract is in PATH
                import shutil
                if shutil.which("tesseract"):
                    TESSERACT_PATH = path
                    break
            else:
                if os.path.exists(path):
                    TESSERACT_PATH = path
                    break
        except:
            continue
    
    if TESSERACT_PATH:
        print(f"[OK] Found Tesseract at: {TESSERACT_PATH}")
    else:
        print("[WARNING] Tesseract not found in common locations")
        print("Please install Tesseract or add it to your PATH")


async def fetch_and_ocr_image():
    """Fetch image from SCRUM-5 and extract text."""
    
    print("=" * 70)
    print("JIRA OCR TEST - Fetching SCRUM-5 image")
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
        # Initialize session
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
        
        for i, attachment in enumerate(attachments, 1):
            filename = attachment.get('filename', 'unknown')
            mime_type = attachment.get('mimeType', 'unknown')
            size = attachment.get('size', 0)
            
            print(f"\n    {i}. {filename}")
            print(f"       Type: {mime_type}")
            print(f"       Size: {size} bytes")
            
            # Check if it's an image
            if mime_type.startswith('image/'):
                print(f"\n[4] Downloading image: {filename}...")
                
                # Download attachment
                content_url = attachment.get('content')
                if content_url:
                    image_data = await connector.download_attachment(content_url)
                    print(f"[OK] Downloaded {len(image_data)} bytes")
                    
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(
                        suffix=f"_{filename}", 
                        delete=False,
                        mode='wb'
                    ) as tmp_file:
                        tmp_file.write(image_data)
                        tmp_path = tmp_file.name
                    
                    print(f"[OK] Saved to: {tmp_path}")
                    
                    # OCR the image
                    if OCR_AVAILABLE and TESSERACT_PATH:
                        print("\n[5] Running OCR to extract text...")
                        
                        try:
                            # Open image
                            with Image.open(tmp_path) as img:
                                print(f"    Image size: {img.size}")
                                print(f"    Image mode: {img.mode}")
                                
                                # Convert to RGB if needed (webp might have alpha channel)
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                    print(f"    Converted to RGB mode")
                                
                                # Set Tesseract path
                                import pytesseract
                                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
                                
                                # Extract text
                                text = pytesseract.image_to_string(img)
                                
                                print("\n" + "=" * 70)
                                print("EXTRACTED TEXT:")
                                print("=" * 70)
                                # Handle Unicode encoding for Windows console
                                try:
                                    print(text)
                                except UnicodeEncodeError:
                                    # Fallback: replace problematic characters
                                    safe_text = text.encode('ascii', 'replace').decode('ascii')
                                    print(safe_text)
                                    print("\n[NOTE] Some Unicode characters were replaced with ?")
                                print("=" * 70)
                                
                                # Also extract word-level data
                                print("\n[6] Extracting detailed OCR data...")
                                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                                
                                # Count detected words
                                word_count = sum(1 for conf in data['conf'] if int(conf) > 60)
                                print(f"    Detected words (confidence >60%): {word_count}")
                                
                        except Exception as e:
                            print(f"[ERROR] OCR failed: {e}")
                    else:
                        if not OCR_AVAILABLE:
                            print("\n[WARNING] OCR libraries not available. Install pytesseract to extract text.")
                        else:
                            print("\n[WARNING] Tesseract not found. Install Tesseract OCR to extract text.")
                        print(f"    Image saved at: {tmp_path}")
                        print(f"    To install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
                    
                    # Don't delete temp file so user can view it
                    print(f"\n[OK] Image saved at: {tmp_path}")
                else:
                    print("[ERROR] No content URL for attachment")
            else:
                print(f"    [SKIP] Not an image file")
        
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
    print("Starting JIRA OCR Test...")
    print(f"Python: {sys.version}")
    print(f"Working directory: {Path.cwd()}")
    
    # Run async test
    asyncio.run(fetch_and_ocr_image())
    
    print("\nTest completed!")


if __name__ == '__main__':
    main()
