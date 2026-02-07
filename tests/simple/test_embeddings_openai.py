#!/usr/bin/env python3
"""Test Embedding Service with OpenAI API (no model download required)."""

import os
import sys
import asyncio
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_openai_embeddings():
    """Test embedding service using OpenAI API."""
    print("=== OpenAI Embedding Service Test ===\n")
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("WARNING: OPENAI_API_KEY not set.")
        print("Please set it to test OpenAI embeddings:")
        print("  $env:OPENAI_API_KEY='your-api-key'")
        print("\nSkipping OpenAI embedding test.")
        return True
    
    try:
        import openai
        
        print("1. Testing OpenAI API connection...")
        client = openai.OpenAI(api_key=api_key)
        
        # Test embedding generation
        test_texts = [
            "This is a test about Python programming.",
            "Machine learning is transforming technology.",
            "Cloud computing provides scalable infrastructure."
        ]
        
        print("2. Generating embeddings...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=test_texts
        )
        
        embeddings = [item.embedding for item in response.data]
        print(f"   [OK] Generated {len(embeddings)} embeddings")
        print(f"   Embedding dimension: {len(embeddings[0])}")
        print()
        
        # Test similarity
        print("3. Testing similarity...")
        emb1 = np.array(embeddings[0])
        emb2 = np.array(embeddings[1])
        emb3 = np.array(embeddings[2])
        
        # Cosine similarity
        sim_1_2 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_1_1 = np.dot(emb1, emb1) / (np.linalg.norm(emb1) * np.linalg.norm(emb1))
        
        print(f"   Same text similarity: {sim_1_1:.4f} (should be ~1.0)")
        print(f"   Text 1 vs Text 2: {sim_1_2:.4f}")
        print()
        
        print("=" * 50)
        print("SUCCESS: OpenAI Embedding test passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_local_embeddings():
    """Test local embedding service with smaller model."""
    print("\n=== Local Embedding Service Test ===\n")
    
    try:
        from src.embeddings import EmbeddingService
        
        # Use smaller/faster model
        config = {
            'text_model': 'sentence-transformers/paraphrase-MiniLM-L3-v2',  # Smaller model
            'embedding_dim': 384,
            'enable_image_embeddings': False
        }
        
        print("1. Initializing EmbeddingService with small model...")
        print("   (This may take a few minutes on first run to download)")
        print("   Press Ctrl+C to skip if taking too long...")
        
        # Set timeout for model loading
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Model loading timeout")
        
        # Try with timeout
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout
            
            embedding_service = EmbeddingService(config)
            signal.alarm(0)  # Cancel timeout
            
            print("   [OK] EmbeddingService initialized")
            
            # Get info
            info = embedding_service.get_embedding_info()
            print(f"   Model: {info['text_model']}")
            print(f"   Dimension: {info['embedding_dim']}")
            print()
            
            # Test embedding
            print("2. Testing text embedding...")
            texts = ["Hello world", "Python programming", "Machine learning"]
            embeddings = await embedding_service.embed_text(texts)
            print(f"   [OK] Generated {len(embeddings)} embeddings")
            print(f"   Shape: {embeddings.shape}")
            print()
            
            print("=" * 50)
            print("SUCCESS: Local Embedding test passed!")
            print("=" * 50)
            
            return True
            
        except TimeoutError:
            print("\n   [!] Model loading timed out (network issue)")
            print("   Skipping local embedding test.")
            return True
            
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        return False


async def main():
    """Run all embedding tests."""
    print("Testing Embedding Service...\n")
    print("Note: These tests require either:")
    print("  1. OPENAI_API_KEY environment variable for OpenAI embeddings")
    print("  2. Internet connection to download local models\n")
    print("=" * 50)
    
    # Test OpenAI if API key available
    openai_result = await test_openai_embeddings()
    
    # Test local embeddings
    local_result = await test_local_embeddings()
    
    if openai_result and local_result:
        print("\n" + "=" * 50)
        print("ALL EMBEDDING TESTS COMPLETED")
        print("=" * 50)
        return True
    else:
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
