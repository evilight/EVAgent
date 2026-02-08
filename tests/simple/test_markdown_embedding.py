#!/usr/bin/env python3
"""
Test script to demonstrate embedding the processed markdown text.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Check for OpenAI API key
if not os.environ.get('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Please set: $env:OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

from src.langchain_integration.llm_integration import LLMManager
from src.embeddings.embedding_service import EmbeddingService

# Add debug for embedding service loading
import logging
logging.basicConfig(level=logging.DEBUG)

# Simple local embedding function
def create_local_embedding(text):
    """Create embedding using local model without HF connection."""
    model_path = "d:\\EVAgent\\models\\all-MiniLM-L6-v2"
    
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        
        # Load locally
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModel.from_pretrained(model_path, local_files_only=True)
        
        # Create embedding
        inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1)
            return embedding.squeeze().numpy()
            
    except Exception as e:
        print(f"[ERROR] Local embedding failed: {e}")
        # Return zero embedding as fallback
        return np.zeros(384)

def test_embedding():
    """Test embedding the processed markdown text."""
    
    print("=" * 70)
    print("EMBEDDING TEST - Processing markdown text for vector storage")
    print("=" * 70)
    
    # Read the processed plain text file
    txt_file = "C:\\Users\\evilight\\AppData\\Local\\Temp\\tmpenyjwm_b_GDB-core.txt"
    
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            plain_text = f.read()
        
        print(f"[1] Loaded plain text: {len(plain_text)} characters")
        
        # Skip embedding service initialization and use local function
        print("\n[2] Using local embedding function...")
        print("    Model: d:\\EVAgent\\models\\all-MiniLM-L6-v2")
        print("    Method: Direct transformers loading (no HF connection)")
        
        # Split text into chunks for embedding
        print("\n[3] Splitting text into chunks...")
        chunk_size = 500
        chunks = []
        
        for i in range(0, len(plain_text), chunk_size):
            chunk = plain_text[i:i + chunk_size]
            chunks.append(chunk)
        
        print(f"[OK] Created {len(chunks)} chunks of ~{chunk_size} characters each")
        
        # Generate embeddings for first few chunks
        print("\n[4] Generating embeddings for first 3 chunks...")
        
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n    Chunk {i+1}: {len(chunk)} chars")
            print(f"    Preview: {chunk[:100]}...")
            
            try:
                # Generate embedding using local function
                embedding = create_local_embedding(chunk)
                print(f"    Embedding shape: {embedding.shape}")
                print(f"    Embedding type: {type(embedding)}")
                print(f"    Sample values: {embedding[:5]}")
            except Exception as e:
                print(f"    [ERROR] Failed to generate embedding: {e}")
        
        print("\n[5] Embedding test completed!")
        print("    The processed markdown text is ready for vector storage")
        
    except FileNotFoundError:
        print(f"[ERROR] Could not find processed text file: {txt_file}")
        print("Please run test_jira_markdown.py first to generate the file")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_embedding()
