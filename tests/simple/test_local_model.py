#!/usr/bin/env python3
"""
Simple test to load local model directly without HuggingFace connection.
"""

import os
import sys
from pathlib import Path
import torch
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from transformers import AutoTokenizer, AutoModel
    print("[OK] Transformers library available")
except ImportError:
    print("[ERROR] Transformers not available")
    sys.exit(1)

def test_local_model():
    """Test loading local model directly."""
    
    print("=" * 70)
    print("LOCAL MODEL TEST - Direct loading without HF connection")
    print("=" * 70)
    
    model_path = "d:\\EVAgent\\models\\all-MiniLM-L6-v2"
    
    # Check if model exists
    if not Path(model_path).exists():
        print(f"[ERROR] Model path not found: {model_path}")
        return
    
    print(f"[1] Model path: {model_path}")
    print(f"[2] Files in model directory:")
    for file in Path(model_path).glob('*'):
        print(f"    {file.name}")
    
    try:
        print("\n[3] Loading tokenizer locally...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=False
        )
        print("[OK] Tokenizer loaded successfully")
        
        print("\n[4] Loading model locally...")
        model = AutoModel.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32
        )
        print("[OK] Model loaded successfully")
        
        print(f"\n[5] Model info:")
        print(f"    Model type: {type(model)}")
        print(f"    Hidden size: {model.config.hidden_size}")
        print(f"    Max position embeddings: {model.config.max_position_embeddings}")
        print(f"    Vocabulary size: {model.config.vocab_size}")
        
        # Test encoding
        print("\n[6] Testing tokenization...")
        test_text = "This is a test sentence for embedding."
        tokens = tokenizer(test_text, return_tensors='pt', padding=True, truncation=True)
        print(f"    Input text: {test_text}")
        print(f"    Token IDs shape: {tokens['input_ids'].shape}")
        print(f"    Attention mask shape: {tokens['attention_mask'].shape}")
        
        # Test embedding generation
        print("\n[7] Testing embedding generation...")
        with torch.no_grad():
            outputs = model(**tokens)
            # Use mean pooling of last hidden state
            embeddings = outputs.last_hidden_state.mean(dim=1)
            print(f"    Embedding shape: {embeddings.shape}")
            print(f"    Embedding type: {type(embeddings)}")
            print(f"    Sample values: {embeddings[0][:5].tolist()}")
        
        print("\n[8] Creating simple embedding function...")
        def create_embedding(text):
            """Create embedding using local model."""
            inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = model(**inputs)
                # Mean pooling
                embedding = outputs.last_hidden_state.mean(dim=1)
                return embedding.squeeze().numpy()
        
        # Test the function
        test_embedding = create_embedding("Hello world")
        print(f"    Test embedding shape: {test_embedding.shape}")
        print(f"    Test embedding type: {type(test_embedding)}")
        
        print("\n" + "=" * 70)
        print("SUCCESS: Local model working without HuggingFace connection!")
        print("=" * 70)
        
        return create_embedding
        
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    test_local_model()
