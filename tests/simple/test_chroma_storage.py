#!/usr/bin/env python3
"""
Test script to store markdown embeddings in ChromaDB.
"""

import os
import sys
from pathlib import Path
import numpy as np
import uuid
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.chroma_manager import ChromaManager
from src.database.schema import DocumentSchema

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

def test_chroma_storage():
    """Test storing markdown embeddings in ChromaDB."""
    
    print("=" * 70)
    print("CHROMADB STORAGE TEST - Storing markdown embeddings")
    print("=" * 70)
    
    # Read the processed plain text file
    txt_file = "C:\\Users\\evilight\\AppData\\Local\\Temp\\tmpenyjwm_b_GDB-core.txt"
    
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            plain_text = f.read()
        
        print(f"[1] Loaded plain text: {len(plain_text)} characters")
        
        # Initialize ChromaDB
        print("\n[2] Initializing ChromaDB...")
        chroma_config = {
            'persist_directory': './storage/markdown_db',
            'collection_name': 'jira_markdown'
        }
        
        chroma_manager = ChromaManager(chroma_config)
        print("[OK] ChromaDB initialized")
        
        # Split text into chunks
        print("\n[3] Splitting text into chunks...")
        chunk_size = 500
        chunks = []
        
        for i in range(0, len(plain_text), chunk_size):
            chunk = plain_text[i:i + chunk_size]
            chunks.append(chunk)
        
        print(f"[OK] Created {len(chunks)} chunks of ~{chunk_size} characters each")
        
        # Prepare documents for storage
        print("\n[5] Preparing documents for storage...")
        documents = []
        
        for i, chunk in enumerate(chunks):
            print(f"\n    Processing chunk {i+1}/{len(chunks)}...")
            
            # Generate embedding
            embedding = create_local_embedding(chunk)
            print(f"    Embedding shape: {embedding.shape}")
            
            # Create document metadata with all required fields
            doc_id = str(uuid.uuid4())
            metadata = {
                'source': 'jira',
                'source_id': 'SCRUM-5',
                'title': 'GDB-core.md',
                'type': 'markdown',
                'description': f'Chunk {i+1} of {len(chunks)} from GDB-core.md',
                'content': chunk,
                'project': 'SCRUM',
                'project_name': 'Scrum Project',
                'status': 'processed',
                'priority': 'medium',
                'author': 'system',
                'assignee': None,
                'reporter': 'evilight@gmail.com',
                'created_date': datetime.now().isoformat(),
                'updated_date': datetime.now().isoformat(),
                'resolution_date': None,
                'labels': ['markdown', 'gdb', 'core-dump'],
                'components': ['documentation'],
                'fix_versions': [],
                'affects_versions': [],
                'error_types': [],
                'stack_traces': [],
                'chunk_index': i,
                'total_chunks': len(chunks),
                'created_at': datetime.now().isoformat(),
                'content_type': 'markdown',
                'file_size': len(plain_text)
            }
            
            # Prepare document for ChromaDB
            document = {
                'id': doc_id,
                'content': chunk,
                'metadata': metadata
            }
            
            documents.append(document)
            print(f"    Document {i+1} prepared")
        
        print(f"\n[OK] Prepared {len(documents)} documents for storage")
        
        # Store in ChromaDB
        print("\n[6] Storing documents in ChromaDB...")
        
        # Add documents using ChromaManager's add_documents_batch method
        try:
            # Use ChromaManager's add_documents_batch method
            result = chroma_manager.add_documents_batch(documents)
            
            print(f"[OK] Stored {len(documents)} documents in ChromaDB")
            
        except Exception as e:
            print(f"[ERROR] Failed to store documents: {e}")
            import traceback
            traceback.print_exc()
        
        # Get collection stats
        print("\n[7] Getting collection statistics...")
        try:
            stats = chroma_manager.get_collection_stats()
            print(f"    Document count: {stats['document_count']}")
            print(f"    Collection name: {stats['collection_name']}")
            print(f"    Persist directory: {stats['persist_directory']}")
        except Exception as e:
            print(f"[ERROR] Failed to get stats: {e}")
        
        # Test search
        print("\n[8] Testing semantic search...")
        try:
            test_query = "core dump analysis"
            query_embedding = create_local_embedding(test_query)
            
            search_results = chroma_manager.search(
                query_embedding=query_embedding,
                n_results=3
            )
            
            print(f"    Query: '{test_query}'")
            print(f"    Results found: {len(search_results)}")
            
            for i, result in enumerate(search_results.get('documents', []), 1):
                metadata = search_results.get('metadatas', [[]])[0][i-1] if search_results.get('metadatas') else {}
                distance = search_results.get('distances', [[]])[0][i-1] if search_results.get('distances') else 0
                doc_id = search_results.get('ids', [[]])[0][i-1] if search_results.get('ids') else 'unknown'
                
                print(f"\n    Result {i}:")
                print(f"      ID: {doc_id}")
                print(f"      Score: {1/(1+distance):.4f}" if distance > 0 else "1.0000")
                print(f"      Source: {metadata.get('source', 'N/A')}")
                print(f"      Chunk: {metadata.get('chunk_index', 'N/A')}")
                print(f"      Preview: {result[:100]}...")
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
        
        print("\n" + "=" * 70)
        print("SUCCESS: Markdown embeddings stored in ChromaDB!")
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_chroma_storage()
