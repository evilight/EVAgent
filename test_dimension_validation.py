#!/usr/bin/env python3
"""
Test script to verify embedding dimension validation in chroma_manager.py
"""

import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from database.chroma_manager import ChromaManager

def test_embedding_dimension_validation():
    """Test embedding dimension validation"""
    
    print("Testing embedding dimension validation...")
    print("=" * 60)
    
    # Initialize ChromaManager with test config
    config = {
        'persist_directory': './storage/test_dimension_db',
        'collection_name': 'test_dimensions'
    }
    
    try:
        manager = ChromaManager(config)
        print("OK ChromaManager initialized successfully")
    except Exception as e:
        print(f"ERROR Failed to initialize ChromaManager: {e}")
        return
    
    # Test cases
    test_cases = [
        {
            'name': 'Correct dimension (384)',
            'embedding': np.random.rand(384),
            'should_pass': True
        },
        {
            'name': 'Wrong dimension (256)',
            'embedding': np.random.rand(256),
            'should_pass': False
        },
        {
            'name': 'Wrong dimension (512)',
            'embedding': np.random.rand(512),
            'should_pass': False
        },
        {
            'name': 'Wrong dimension (768)',
            'embedding': np.random.rand(768),
            'should_pass': False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Embedding shape: {test_case['embedding'].shape}")
        
        try:
            doc_id = manager.add_document(
                content=f"Test document {i}",
                embedding=test_case['embedding'],
                metadata={
                    'source': 'test',
                    'source_id': f'test-{i}',
                    'title': f'Test Document {i}',
                    'type': 'test'
                }
            )
            
            if test_case['should_pass']:
                print(f"OK PASS: Document added with ID: {doc_id}")
            else:
                print(f"ERROR FAIL: Should have failed but passed with ID: {doc_id}")
                
        except ValueError as e:
            if test_case['should_pass']:
                print(f"ERROR FAIL: Should have passed but got error: {e}")
            else:
                print(f"OK PASS: Correctly caught dimension error: {e}")
        except Exception as e:
            print(f"ERROR ERROR: Unexpected error: {e}")
    
    print("\n" + "=" * 60)
    print("Dimension validation test completed!")
    
    # Clean up test database
    try:
        import shutil
        if Path('./storage/test_dimension_db').exists():
            shutil.rmtree('./storage/test_dimension_db')
            print("Cleaned up test database")
    except Exception as e:
        print(f"WARNING: Could not clean up test database: {e}")

if __name__ == "__main__":
    test_embedding_dimension_validation()
