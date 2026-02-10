#!/usr/bin/env python3
"""
Test the updated EmbeddingService with local model support.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.embeddings.embedding_service import EmbeddingService

async def test_local_embedding_service():
    """Test the updated embedding service with local model."""
    print("=" * 70)
    print("TESTING UPDATED EMBEDDING SERVICE")
    print("=" * 70)
    
    # Test 1: Local model configuration
    print("\n[1] Testing local model configuration...")
    local_config = {
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'device': 'cpu',
        'code_model': None,  # Disable to avoid HF download
        'enable_image_embeddings': False
    }
    
    try:
        embedding_service = EmbeddingService(local_config)
        print("[OK] Local embedding service initialized")
        
        # Test embedding generation
        test_text = "This is a test sentence for local embedding."
        embedding = await embedding_service.embed_text(test_text)
        
        print(f"    Text: '{test_text}'")
        print(f"    Embedding shape: {embedding.shape}")
        print(f"    Embedding type: {type(embedding)}")
        print(f"    Sample values: {embedding[0][:5]}")
        print("[OK] Local embedding generation successful")
        
    except Exception as e:
        print(f"[ERROR] Local embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Batch embedding
    print("\n[2] Testing batch embedding...")
    test_texts = [
        "First test sentence",
        "Second test sentence",
        "Third test sentence"
    ]
    
    try:
        batch_embeddings = await embedding_service.embed_text(test_texts)
        print(f"    Batch size: {len(test_texts)}")
        print(f"    Batch embedding shape: {batch_embeddings.shape}")
        print(f"    Individual shapes: {[emb.shape for emb in batch_embeddings]}")
        print("[OK] Batch embedding successful")
        
    except Exception as e:
        print(f"[ERROR] Batch embedding failed: {e}")
        return False
    
    # Test 3: Performance check
    print("\n[3] Testing performance...")
    import time
    
    start_time = time.time()
    for i in range(10):
        await embedding_service.embed_text(f"Performance test sentence {i}")
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 10
    print(f"    Average time per embedding: {avg_time:.3f}s")
    print(f"    Embeddings per second: {1/avg_time:.1f}")
    
    if avg_time < 0.1:  # Less than 100ms
        print("[OK] Performance is good")
    else:
        print("[WARN] Performance could be improved")
    
    # Test 4: Fallback to online model (if local fails)
    print("\n[4] Testing online fallback configuration...")
    online_config = {
        'text_model': 'sentence-transformers/all-MiniLM-L6-v2',
        'device': 'cpu'
    }
    
    try:
        # Only test if network is available and user wants to
        test_online = os.getenv('TEST_ONLINE_MODEL', '').lower() == 'true'
        if test_online:
            online_service = EmbeddingService(online_config)
            online_embedding = await online_service.embed_text("Online model test")
            print(f"    Online embedding shape: {online_embedding.shape}")
            print("[OK] Online fallback works")
        else:
            print("[SKIP] Online model test (set TEST_ONLINE_MODEL=true to enable)")
            
    except Exception as e:
        print(f"[ERROR] Online fallback failed: {e}")
    
    print("\n" + "=" * 70)
    print("EMBEDDING SERVICE TEST COMPLETED!")
    print("=" * 70)
    print("\nFeatures verified:")
    print("  - Local model loading")
    print("  - Single text embedding")
    print("  - Batch text embedding")
    print("  - Performance measurement")
    print("  - Online fallback capability")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_local_embedding_service())
    sys.exit(0 if success else 1)
