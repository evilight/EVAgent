#!/usr/bin/env python3
"""Test Embedding Service - lightweight version with smaller model."""

import os
import sys
import asyncio
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_embedding_service():
    """Test EmbeddingService with minimal model."""
    print("=== Embedding Service Test (Lightweight) ===\n")
    
    try:
        from src.embeddings import EmbeddingService
        from src.utils import ConfigLoader
        
        # Use the smallest/fastest available model
        # paraphrase-MiniLM-L3-v2 is only 22MB vs 400MB for all-MiniLM-L6-v2
        config = {
            'text_model': 'sentence-transformers/paraphrase-MiniLM-L3-v2',
            'embedding_dim': 384,
            'batch_size': 32,
            'max_seq_length': 128,
            'enable_image_embeddings': False,
            'enable_code_embeddings': False,
            'cache_dir': './storage/model_cache'
        }
        
        print("1. Initializing EmbeddingService...")
        print("   Model: paraphrase-MiniLM-L3-v2 (22MB - much faster download)")
        print("   (First run will download the model, please wait...)")
        print()
        
        embedding_service = EmbeddingService(config)
        print("   [OK] EmbeddingService initialized successfully!")
        
        # Get model info
        info = embedding_service.get_embedding_info()
        print(f"   Text model: {info['text_model']}")
        print(f"   Embedding dimension: {info['embedding_dim']}")
        print(f"   Max sequence length: {info.get('max_seq_length', 'N/A')}")
        print()
        
        # Test text embedding
        print("2. Testing text embedding...")
        test_texts = [
            "Python is a popular programming language.",
            "Machine learning transforms data into insights.",
            "Cloud computing provides scalable infrastructure."
        ]
        
        embeddings = await embedding_service.embed_text(test_texts)
        print(f"   [OK] Generated {len(embeddings)} embeddings")
        print(f"   Embedding shape: {embeddings.shape}")
        print(f"   Embedding dimension: {embeddings.shape[1]}")
        print()
        
        # Test single text
        print("3. Testing single text embedding...")
        single = await embedding_service.embed_text("This is a single sentence.")
        print(f"   [OK] Single embedding shape: {single.shape}")
        print()
        
        # Test similarity
        print("4. Testing similarity computation...")
        emb1 = embeddings[0]
        emb2 = embeddings[1]
        emb3 = embeddings[2]
        
        sim_1_1 = embedding_service.compute_similarity(emb1, emb1)
        sim_1_2 = embedding_service.compute_similarity(emb1, emb2)
        sim_1_3 = embedding_service.compute_similarity(emb1, emb3)
        
        print("   [OK] Cosine similarity scores:")
        print(f"     Same text (should be ~1.0): {sim_1_1:.4f}")
        print(f"     Python vs ML: {sim_1_2:.4f}")
        print(f"     Python vs Cloud: {sim_1_3:.4f}")
        print()
        
        # Test preprocessing
        print("5. Testing text preprocessing...")
        raw = """
        This   is    a   messy
        text with extra   spaces
        """
        cleaned = embedding_service.preprocess_text_for_embedding(raw, 'text')
        print(f"   [OK] Cleaned text length: {len(cleaned)}")
        print(f"   Preview: '{cleaned[:50]}...'")
        print()
        
        # Test batch processing
        print("6. Testing batch embedding...")
        batch_items = [
            {'content': 'First document about software.'},
            {'content': 'Second document about hardware.'},
            {'content': 'Third document about networks.'}
        ]
        batch_embeddings = await embedding_service.batch_embed(batch_items)
        print(f"   [OK] Batch embedded {len(batch_embeddings)} items")
        print(f"   Shapes: {[e.shape for e in batch_embeddings]}")
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
    print("Note: First run will download the model (~22MB).")
    print("If download fails, check your internet connection or try using a VPN.\n")
    
    success = asyncio.run(test_embedding_service())
    sys.exit(0 if success else 1)
