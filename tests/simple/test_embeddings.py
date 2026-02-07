#!/usr/bin/env python3
"""Test Embedding Service functionality."""

import os
import sys
import asyncio
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_embedding_service():
    """Test EmbeddingService operations."""
    print("=== Embedding Service Test ===\n")
    
    try:
        from src.embeddings import EmbeddingService
        from src.utils import ConfigLoader
        
        # Load configuration
        print("1. Loading embedding configuration...")
        config_path = Path(__file__).parent.parent.parent / "config"
        loader = ConfigLoader(str(config_path))
        config = loader.load_config("embedding_config")
        embedding_config = config.get('embeddings', {})
        print("   [OK] Config loaded")
        print(f"   Text model: {embedding_config.get('text_model', 'default')}")
        print(f"   Embedding dim: {embedding_config.get('embedding_dim', 384)}")
        print()
        
        # Initialize embedding service
        print("2. Initializing EmbeddingService...")
        print("   Loading models (this may take a moment)...")
        embedding_service = EmbeddingService(embedding_config)
        print("   [OK] EmbeddingService initialized")
        
        # Get model info
        info = embedding_service.get_embedding_info()
        print(f"   Text model: {info['text_model']}")
        print(f"   Embedding dimension: {info['embedding_dim']}")
        print(f"   Image embeddings: {info['image_embeddings_enabled']}")
        print(f"   Code embeddings: {info['code_embeddings_enabled']}")
        print()
        
        # Test text embedding
        print("3. Testing text embedding...")
        test_texts = [
            "This is a test sentence about software development.",
            "Python is a popular programming language for data science.",
            "Machine learning and artificial intelligence are transforming technology."
        ]
        
        embeddings = await embedding_service.embed_text(test_texts)
        print(f"   [OK] Generated {len(embeddings)} embeddings")
        print(f"   Embedding shape: {embeddings.shape}")
        print(f"   Embedding dimension: {embeddings.shape[1]}")
        print()
        
        # Test single text embedding
        print("4. Testing single text embedding...")
        single_embedding = await embedding_service.embed_text("Single test sentence.")
        print("   [OK] Generated single embedding")
        print(f"   Shape: {single_embedding.shape}")
        print()
        
        # Test similarity computation
        print("5. Testing similarity computation...")
        emb1 = embeddings[0]
        emb2 = embeddings[1]
        emb3 = embeddings[2]
        
        sim_1_2 = embedding_service.compute_similarity(emb1, emb2)
        sim_1_1 = embedding_service.compute_similarity(emb1, emb1)
        sim_1_3 = embedding_service.compute_similarity(emb1, emb3)
        
        print("   [OK] Similarity scores:")
        print(f"     Same text similarity: {sim_1_1:.4f} (should be ~1.0)")
        print(f"     Text 1 vs Text 2: {sim_1_2:.4f}")
        print(f"     Text 1 vs Text 3: {sim_1_3:.4f}")
        print()
        
        # Test text preprocessing
        print("6. Testing text preprocessing...")
        raw_text = """
        This is a   messy    text with   extra spaces
        and multiple lines that need cleaning up.
        """
        cleaned = embedding_service.preprocess_text_for_embedding(raw_text, 'text')
        print("   [OK] Text preprocessed")
        print(f"   Original length: {len(raw_text)}")
        print(f"   Cleaned length: {len(cleaned)}")
        print(f"   Cleaned text: {cleaned[:50]}...")
        print()
        
        # Test code embedding
        print("7. Testing code embedding...")
        code_text = """
        def fibonacci(n):
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
        """
        code_embedding = await embedding_service.embed_text(code_text, is_code=True)
        print("   [OK] Generated code embedding")
        print(f"   Shape: {code_embedding.shape}")
        print()
        
        # Test batch embedding
        print("8. Testing batch embedding with mixed content...")
        batch_items = [
            {'content': 'First document about Python.'},
            {'content': 'Second document about JavaScript.'},
            {'content': 'Third document about machine learning.'}
        ]
        batch_embeddings = await embedding_service.batch_embed(batch_items)
        print(f"   [OK] Batch embedded {len(batch_embeddings)} items")
        print(f"   Shapes: {[emb.shape for emb in batch_embeddings]}")
        print()
        
        print("=" * 50)
        print("SUCCESS: All Embedding Service tests passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_embedding_service())
    sys.exit(0 if success else 1)
