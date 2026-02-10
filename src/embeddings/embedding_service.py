"""
Embedding service for generating vector embeddings from text and images.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union
import torch
from sentence_transformers import SentenceTransformer
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from PIL import Image
    import torch.nn.functional as F
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False


class EmbeddingService:
    """
    Service for generating embeddings for text and multi-modal content.
    
    Supports different embedding models for different content types.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize embedding service.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        
        # Model configurations
        self.text_model_name = self.config.get('text_model', 'sentence-transformers/all-MiniLM-L6-v2')
        self.code_model_name = self.config.get('code_model', 'microsoft/codebert-base')
        self.image_model_name = self.config.get('image_model', 'openai/clip-vit-base-patch32')
        
        # Embedding dimensions
        self.embedding_dim = self.config.get('embedding_dim', 384)
        
        # Initialize models
        self.text_model = None
        self.code_model = None
        self.image_model = None
        self.clip_processor = None
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Load models
        self._load_models()
    
    def _load_models(self):
        """Load embedding models with local-first approach."""
        try:
            # Try local model first
            if self._is_local_model(self.text_model_name):
                self.logger.info(f"Loading local text model: {self.text_model_name}")
                self.text_model = self._load_local_model(self.text_model_name)
                self.embedding_dim = self.text_model.get_sentence_embedding_dimension()
                self.logger.info("Local text model loaded successfully")
            else:
                # Fallback to online model
                self.logger.info(f"Loading online text model: {self.text_model_name}")
                self.text_model = SentenceTransformer(self.text_model_name)
                self.embedding_dim = self.text_model.get_sentence_embedding_dimension()
                self.logger.info("Online text model loaded successfully")
            
            # Load code model if different from text model
            if (self.code_model_name and 
                self.code_model_name != self.text_model_name and 
                TRANSFORMERS_AVAILABLE):
                if self._is_local_model(self.code_model_name):
                    self.logger.info(f"Loading local code model: {self.code_model_name}")
                    self.code_tokenizer = AutoTokenizer.from_pretrained(
                        self.code_model_name, local_files_only=True
                    )
                    self.code_model = AutoModel.from_pretrained(
                        self.code_model_name, local_files_only=True
                    )
                else:
                    self.logger.info(f"Loading online code model: {self.code_model_name}")
                    self.code_tokenizer = AutoTokenizer.from_pretrained(self.code_model_name)
                    self.code_model = AutoModel.from_pretrained(self.code_model_name)
            
            # Load image model if available
            if (CLIP_AVAILABLE and 
                self.config.get('enable_image_embeddings', True) and
                self.image_model_name):
                if self._is_local_model(self.image_model_name):
                    self.logger.info(f"Loading local image model: {self.image_model_name}")
                    self.image_model = CLIPModel.from_pretrained(
                        self.image_model_name, local_files_only=True
                    )
                    self.clip_processor = CLIPProcessor.from_pretrained(
                        self.image_model_name, local_files_only=True
                    )
                else:
                    self.logger.info(f"Loading online image model: {self.image_model_name}")
                    self.image_model = CLIPModel.from_pretrained(self.image_model_name)
                    self.clip_processor = CLIPProcessor.from_pretrained(self.image_model_name)
            
            self.logger.info("All embedding models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load embedding models: {e}")
            # Try fallback for text model
            if self.text_model is None:
                self.logger.info("Attempting fallback to online model...")
                try:
                    self.text_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                    self.embedding_dim = self.text_model.get_sentence_embedding_dimension()
                    self.logger.info("Fallback online model loaded successfully")
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")
                    raise
            else:
                raise
    
    def _is_local_model(self, model_path: str) -> bool:
        """Check if model path is a local directory."""
        if model_path is None:
            return False
        import os
        from pathlib import Path
        return os.path.exists(model_path) and Path(model_path).is_dir()
    
    def _load_local_model(self, model_path: str) -> SentenceTransformer:
        """Load SentenceTransformer model from local path."""
        try:
            # First try with SentenceTransformer
            model = SentenceTransformer(model_path)
            return model
        except Exception as e:
            self.logger.warning(f"SentenceTransformer failed to load local model: {e}")
            # Fallback to transformers approach
            if TRANSFORMERS_AVAILABLE:
                return self._load_local_with_transformers(model_path)
            else:
                raise ImportError("transformers library not available for fallback loading")
    
    def _load_local_with_transformers(self, model_path: str) -> Any:
        """Load model using transformers library as fallback."""
        from transformers import AutoTokenizer, AutoModel
        import torch
        
        class LocalEmbeddingModel:
            """Wrapper for local model loaded with transformers."""
            
            def __init__(self, model_path: str):
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path, local_files_only=True, trust_remote_code=False
                )
                self.model = AutoModel.from_pretrained(
                    model_path, local_files_only=True, trust_remote_code=False
                )
                self.model.eval()
            
            def get_sentence_embedding_dimension(self) -> int:
                """Get embedding dimension from model config."""
                return self.model.config.hidden_size
            
            def encode(self, sentences, batch_size=32, show_progress_bar=False, **kwargs):
                """Encode sentences to embeddings."""
                if isinstance(sentences, str):
                    sentences = [sentences]
                
                embeddings = []
                for i in range(0, len(sentences), batch_size):
                    batch = sentences[i:i + batch_size]
                    
                    # Tokenize
                    inputs = self.tokenizer(
                        batch, 
                        padding=True, 
                        truncation=True, 
                        max_length=512,
                        return_tensors='pt'
                    )
                    
                    # Generate embeddings
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        # Mean pooling
                        batch_embeddings = outputs.last_hidden_state.mean(dim=1)
                        embeddings.extend(batch_embeddings.cpu().numpy())
                
                return np.array(embeddings)
        
        return LocalEmbeddingModel(model_path)
    
    async def embed_text(
        self,
        text: Union[str, List[str]],
        is_code: bool = False,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for text content.
        
        Args:
            text: Text or list of texts to embed
            is_code: Whether the text is code
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of embeddings
        """
        if not text:
            return np.array([])
        
        # Ensure list format
        if isinstance(text, str):
            text = [text]
        
        # Filter out empty strings
        texts = [t for t in text if t and t.strip()]
        if not texts:
            return np.array([])
        
        try:
            # Choose appropriate model
            if is_code and self.code_model and TRANSFORMERS_AVAILABLE:
                embeddings = await self._embed_code_batch(texts, batch_size)
            else:
                embeddings = await self._embed_text_batch(texts, batch_size)
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to embed text: {e}")
            # Return zero embeddings as fallback
            return np.zeros((len(texts), self.embedding_dim))
    
    async def _embed_text_batch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """
        Embed text using sentence-transformers model.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size
            
        Returns:
            Numpy array of embeddings
        """
        loop = asyncio.get_event_loop()
        
        def process_batch(batch_texts):
            return self.text_model.encode(
                batch_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        
        # Process in batches to avoid memory issues
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await loop.run_in_executor(self.executor, process_batch, batch)
            all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings) if all_embeddings else np.array([])
    
    async def _embed_code_batch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """
        Embed code using CodeBERT model.
        
        Args:
            texts: List of code texts to embed
            batch_size: Batch size
            
        Returns:
            Numpy array of embeddings
        """
        loop = asyncio.get_event_loop()
        
        def process_batch(batch_texts):
            # Tokenize code
            inputs = self.code_tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.code_model(**inputs)
                # Use [CLS] token embedding
                embeddings = outputs.last_hidden_state[:, 0, :]
                # Normalize
                embeddings = F.normalize(embeddings, p=2, dim=1)
            
            return embeddings.cpu().numpy()
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await loop.run_in_executor(self.executor, process_batch, batch)
            all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings) if all_embeddings else np.array([])
    
    async def embed_image(self, image_data: Union[bytes, Image.Image]) -> np.ndarray:
        """
        Generate embeddings for image content.
        
        Args:
            image_data: Image as bytes or PIL Image
            
        Returns:
            Numpy array of image embedding
        """
        if not CLIP_AVAILABLE:
            self.logger.warning("CLIP not available for image embeddings")
            return np.array([])
        
        try:
            # Convert bytes to PIL Image if needed
            if isinstance(image_data, bytes):
                import io
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data
            
            loop = asyncio.get_event_loop()
            
            def process_image(img):
                inputs = self.clip_processor(
                    images=img,
                    return_tensors="pt",
                    padding=True
                )
                
                with torch.no_grad():
                    outputs = self.image_model.get_image_features(**inputs)
                    # Normalize
                    outputs = F.normalize(outputs, p=2, dim=1)
                
                return outputs.cpu().numpy()
            
            embedding = await loop.run_in_executor(self.executor, process_image, image)
            return embedding[0]  # Return single embedding
            
        except Exception as e:
            self.logger.error(f"Failed to embed image: {e}")
            return np.array([])
    
    async def embed_multimodal(
        self,
        text: str,
        image_data: Optional[Union[bytes, Image.Image]] = None,
        code_blocks: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Generate multi-modal embeddings combining text, images, and code.
        
        Args:
            text: Main text content
            image_data: Optional image data
            code_blocks: Optional list of code blocks
            
        Returns:
            Combined embedding vector
        """
        embeddings = []
        
        # Embed main text
        if text:
            text_embedding = await self.embed_text(text)
            if text_embedding.size > 0:
                embeddings.append(text_embedding[0])
        
        # Embed image if provided
        if image_data and CLIP_AVAILABLE:
            image_embedding = await self.embed_image(image_data)
            if image_embedding.size > 0:
                embeddings.append(image_embedding)
        
        # Embed code blocks if provided
        if code_blocks:
            for code in code_blocks:
                code_embedding = await self.embed_text(code, is_code=True)
                if code_embedding.size > 0:
                    embeddings.append(code_embedding[0])
        
        if not embeddings:
            return np.array([])
        
        # Combine embeddings (simple averaging for now)
        combined = np.mean(embeddings, axis=0)
        
        # Normalize final embedding
        combined = combined / np.linalg.norm(combined)
        
        return combined
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score
        """
        if embedding1.size == 0 or embedding2.size == 0:
            return 0.0
        
        # Ensure embeddings are normalized
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Compute cosine similarity
        return float(np.dot(embedding1, embedding2))
    
    async def find_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        threshold: float = 0.7,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar embeddings to a query embedding.
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: Array of candidate embeddings
            threshold: Similarity threshold
            top_k: Maximum number of results
            
        Returns:
            List of similarity results with indices and scores
        """
        if query_embedding.size == 0 or candidate_embeddings.size == 0:
            return []
        
        # Compute similarities
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            if candidate.size > 0:
                similarity = self.compute_similarity(query_embedding, candidate)
                if similarity >= threshold:
                    similarities.append({
                        'index': i,
                        'similarity': similarity
                    })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    def preprocess_text_for_embedding(self, text: str, content_type: str = 'text') -> str:
        """
        Preprocess text for optimal embedding generation.
        
        Args:
            text: Raw text content
            content_type: Type of content ('text', 'code', 'mixed')
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        if content_type == 'code':
            # For code, preserve structure but remove comments if too long
            lines = text.split('\n')
            if len(lines) > 100:
                # Remove comment lines for very long code
                lines = [line for line in lines if not line.strip().startswith('#')]
                text = '\n'.join(lines[:200])  # Limit to 200 lines
        
        elif content_type == 'mixed':
            # For mixed content, try to separate code from text
            # This is a simple approach - could be enhanced
            code_blocks = []
            text_parts = []
            
            lines = text.split('\n')
            current_block = []
            in_code_block = False
            
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    if current_block:
                        if in_code_block:
                            text_parts.append('\n'.join(current_block))
                        else:
                            code_blocks.append('\n'.join(current_block))
                        current_block = []
                else:
                    current_block.append(line)
            
            # Add remaining content
            if current_block:
                if in_code_block:
                    code_blocks.append('\n'.join(current_block))
                else:
                    text_parts.append('\n'.join(current_block))
            
            # Combine with markers
            parts = []
            if text_parts:
                parts.append(' '.join(text_parts))
            if code_blocks:
                parts.append(' '.join(code_blocks))
            
            text = ' '.join(parts)
        
        # Truncate if too long (most models have limits)
        max_length = 8000  # Conservative limit
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    async def batch_embed(
        self,
        items: List[Dict[str, Any]],
        text_field: str = 'content',
        code_field: str = 'code',
        image_field: str = 'image'
    ) -> List[np.ndarray]:
        """
        Batch embed a list of items with mixed content types.
        
        Args:
            items: List of items to embed
            text_field: Field name for text content
            code_field: Field name for code content
            image_field: Field name for image content
            
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for item in items:
            # Extract content
            text = item.get(text_field, '')
            code = item.get(code_field, [])
            image_data = item.get(image_field)
            
            # Handle code blocks
            code_blocks = []
            if isinstance(code, str):
                code_blocks = [code]
            elif isinstance(code, list):
                code_blocks = code
            
            # Generate multi-modal embedding
            embedding = await self.embed_multimodal(
                text=text,
                image_data=image_data,
                code_blocks=code_blocks
            )
            
            embeddings.append(embedding)
        
        return embeddings
    
    def get_embedding_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding service.
        
        Returns:
            Dictionary with model information
        """
        return {
            'text_model': self.text_model_name,
            'code_model': self.code_model_name if TRANSFORMERS_AVAILABLE else None,
            'image_model': self.image_model_name if CLIP_AVAILABLE else None,
            'embedding_dim': self.embedding_dim,
            'image_embeddings_enabled': CLIP_AVAILABLE and self.config.get('enable_image_embeddings', True),
            'code_embeddings_enabled': TRANSFORMERS_AVAILABLE and self.code_model is not None
        }
