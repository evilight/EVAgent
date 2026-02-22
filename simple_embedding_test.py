#!/usr/bin/env python3
"""
Simple embedding test - show exact embedding result of a single string
"""

import asyncio
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from embeddings.embedding_service import EmbeddingService

async def simple_embedding_test():
    """Simple test for single string embedding"""
    
    # Configure embedding service - disable code model
    config = {
        'text_model': 'd:\\EVAgent\\models\\all-MiniLM-L6-v2',
        'code_model': None,  # Disable code model
        'embedding_dim': 384,
        'enable_image_embeddings': False  # Disable image embeddings
    }
    
    # Create service instance
    print("Loading embedding service...")
    service = EmbeddingService(config)
    
    # Test string
    test_string = "this is a test string"
    print(f"Input string: '{test_string}'")
    print()
    
    # Generate embedding
    print("Generating embedding...")
    embedding = await service.embed_text(test_string)
    
    # Print embedding results
    print("Embedding Results:")
    print(f"Shape: {embedding.shape}")
    print(f"Data type: {embedding.dtype}")
    print()
    
    print("Complete embedding vector:")
    print(embedding[0])
    print()
    
    print("Vector statistics:")
    print(f"Vector norm: {np.linalg.norm(embedding[0]):.6f}")
    print(f"Min value: {embedding.min():.6f}")
    print(f"Max value: {embedding.max():.6f}")
    print(f"Mean: {embedding.mean():.6f}")
    print(f"Std deviation: {embedding.std():.6f}")
    print()
    
    print("First 10 values:")
    for i, val in enumerate(embedding[0][:10]):
        print(f"  [{i}]: {val:.6f}")

if __name__ == "__main__":
    asyncio.run(simple_embedding_test())
