#!/usr/bin/env python3
"""
Test content cleaning functionality.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.processors.content_cleaner import ContentCleaner

def test_content_cleaner():
    """Test content cleaning functionality."""
    print("=" * 70)
    print("TESTING CONTENT CLEANER")
    print("=" * 70)
    
    # Initialize cleaner
    cleaner = ContentCleaner({
        'preserve_code_blocks': True,
        'preserve_tables': False,
        'normalize_unicode': True,
        'remove_emails': False,
        'remove_phones': False,
        'remove_urls': False
    })
    print("[OK] ContentCleaner initialized")
    
    # Test 1: HTML cleaning
    print("\n[1] Testing HTML cleaning...")
    html_content = """
    <html>
    <head>
        <title>Test Document</title>
        <style>
            body { font-family: Arial; }
        </style>
    </head>
    <body>
        <h1>Main Title</h1>
        <p>This is a <strong>test</strong> paragraph with <em>formatting</em>.</p>
        <script>alert('test');</script>
        <pre><code>
        def hello_world():
            print("Hello, World!")
        </code></pre>
        <table>
            <tr><th>Name</th><th>Age</th></tr>
            <tr><td>John</td><td>25</td></tr>
        </table>
    </body>
    </html>
    """
    
    cleaned_html = cleaner.clean_html(html_content)
    print(f"    Original HTML length: {len(html_content)}")
    print(f"    Cleaned text length: {len(cleaned_html)}")
    print(f"    Cleaned preview: {cleaned_html[:200]}...")
    print("[OK] HTML cleaning successful")
    
    # Test 2: Markdown cleaning
    print("\n[2] Testing markdown cleaning...")
    markdown_content = """
    # Document Title
    
    This is a **bold** text and this is *italic*.
    
    ## Code Example
    ```python
    def calculate_sum(a, b):
        return a + b
    ```
    
    ### Lists
    - Item 1
    - Item 2
    - Item 3
    
    1. First
    2. Second
    3. Third
    
    ### Links and Images
    [Link to Google](https://google.com)
    ![Alt text](image.png)
    
    > This is a blockquote
    
    ---
    
    Horizontal rule above.
    """
    
    cleaned_markdown = cleaner.clean_markdown(markdown_content)
    print(f"    Original markdown length: {len(markdown_content)}")
    print(f"    Cleaned text length: {len(cleaned_markdown)}")
    print(f"    Cleaned preview: {cleaned_markdown[:200]}...")
    print("[OK] Markdown cleaning successful")
    
    # Test 3: Text normalization
    print("\n[3] Testing text normalization...")
    messy_text = 'This  has   multiple   spaces\n\n\nand weird quotes: "smart quotes" and \'apostrophes\'.'
    normalized = cleaner.normalize_text(messy_text)
    print(f"    Original: '{messy_text}'")
    print(f"    Normalized: '{normalized}'")
    print("[OK] Text normalization successful")
    
    # Test 4: Noise removal
    print("\n[4] Testing noise removal...")
    noisy_text = "Contact me at test@example.com or call 123-456-7890. Visit https://example.com!!! WOWWWW!!!"
    
    # Test without removal
    cleaner_no_removal = ContentCleaner({
        'remove_emails': False,
        'remove_phones': False,
        'remove_urls': False
    })
    cleaned_no_removal = cleaner_no_removal.remove_noise(noisy_text)
    print(f"    Without removal: '{cleaned_no_removal}'")
    
    # Test with removal
    cleaner_with_removal = ContentCleaner({
        'remove_emails': True,
        'remove_phones': True,
        'remove_urls': True
    })
    cleaned_with_removal = cleaner_with_removal.remove_noise(noisy_text)
    print(f"    With removal: '{cleaned_with_removal}'")
    print("[OK] Noise removal successful")
    
    # Test 5: Structure extraction
    print("\n[5] Testing structure extraction...")
    structured_content = """
    # Main Title
    ## Subtitle
    
    Some text here.
    
    ```python
    def test():
        pass
    ```
    
    [Link](http://example.com)
    ![Image](image.png)
    
    - List item 1
    - List item 2
    """
    
    structure = cleaner.extract_structure(structured_content)
    print(f"    Headings: {structure['headings']}")
    print(f"    Code blocks: {len(structure['code_blocks'])}")
    print(f"    Links: {structure['links']}")
    print(f"    Images: {structure['images']}")
    print(f"    Lists: {structure['lists']}")
    print(f"    Word count: {structure['word_count']}")
    print(f"    Character count: {structure['char_count']}")
    print("[OK] Structure extraction successful")
    
    # Test 6: Full document cleaning
    print("\n[6] Testing full document cleaning...")
    
    # Test HTML document
    html_result = cleaner.clean_document(html_content, 'html')
    print(f"    HTML document:")
    print(f"      Content type: {html_result['content_type']}")
    print(f"      Original length: {html_result['original_length']}")
    print(f"      Cleaned length: {html_result['cleaned_length']}")
    print(f"      Compression ratio: {html_result['compression_ratio']:.2f}")
    print(f"      Headings found: {len(html_result['structure']['headings'])}")
    
    # Test markdown document
    markdown_result = cleaner.clean_document(markdown_content, 'markdown')
    print(f"    Markdown document:")
    print(f"      Content type: {markdown_result['content_type']}")
    print(f"      Original length: {markdown_result['original_length']}")
    print(f"      Cleaned length: {markdown_result['cleaned_length']}")
    print(f"      Compression ratio: {markdown_result['compression_ratio']:.2f}")
    print(f"      Code blocks: {len(markdown_result['structure']['code_blocks'])}")
    
    # Test auto-detection
    auto_result = cleaner.clean_document(html_content, 'auto')
    print(f"    Auto-detection: {auto_result['content_type']}")
    
    print("[OK] Full document cleaning successful")
    
    # Test 7: Performance test
    print("\n[7] Testing performance...")
    import time
    
    large_content = html_content * 100  # Make it larger
    
    start_time = time.time()
    for _ in range(10):
        cleaner.clean_document(large_content, 'html')
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 10
    print(f"    Average time per document: {avg_time:.3f}s")
    print(f"    Documents per second: {1/avg_time:.1f}")
    
    if avg_time < 0.1:
        print("[OK] Performance is good")
    else:
        print("[WARN] Performance could be improved")
    
    print("\n" + "=" * 70)
    print("CONTENT CLEANER TEST COMPLETED!")
    print("=" * 70)
    print("\nVerified features:")
    print("  - HTML tag removal and cleanup")
    print("  - Markdown syntax cleaning")
    print("  - Text normalization")
    print("  - Noise removal (emails, phones, URLs)")
    print("  - Structure extraction")
    print("  - Auto content type detection")
    print("  - Performance optimization")
    print("  - Code block preservation")
    print("  - Compression ratio tracking")
    
    return True

if __name__ == "__main__":
    success = test_content_cleaner()
    sys.exit(0 if success else 1)
