"""
Embedding service using Google Gemini API + Chroma Vector DB.
Provides text embedding generation with persistent vector storage.
"""
import google.generativeai as genai
from typing import List, Dict, Optional
import os
from services.chroma_service import ChromaService


class EmbeddingService:
    """Service for generating and storing embeddings using Gemini + Chroma."""
    
    def __init__(self, api_key: str, chroma_path: Optional[str] = None):
        """
        Initialize the embedding service with Gemini API and Chroma storage.
        
        Args:
            api_key: Google API key for Gemini
            chroma_path: Path to Chroma persistent storage
        """
        if not chroma_path:
            chroma_path = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

        genai.configure(api_key=api_key)
        self.vector_size = 768
        self.model_locked = False  # Lock model after first successful embedding
        self.model_name = self._resolve_embedding_model()
        self.fallback_models = [
            "models/gemini-embedding-001",
            "models/embedding-001",
            "models/text-embedding-004",
        ]
        
        # Initialize Chroma for persistent storage
        self.chroma = ChromaService(persist_directory=chroma_path)
        print(f"✓ EmbeddingService initialized with Chroma at {chroma_path}")

    def _resolve_embedding_model(self) -> str:
        """Resolve an available model that supports embedContent."""
        preferred_order = [
            "models/gemini-embedding-001",
            "models/embedding-001",
            "models/text-embedding-004",
        ]

        try:
            available = {}
            for model in genai.list_models():
                methods = getattr(model, "supported_generation_methods", []) or []
                available[model.name] = methods

            for model_name in preferred_order:
                if "embedContent" in available.get(model_name, []):
                    return model_name
        except Exception:
            pass

        return "models/embedding-001"
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text. Checks Chroma first, generates if needed.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not isinstance(text, str) or not text.strip():
            # Return zero vector for empty/invalid text
            return [0.0] * self.vector_size
        
        # Check Chroma first (persistent storage)
        existing = self.chroma.get_embedding(text)
        if existing:
            # Update vector_size from actual stored embedding if needed
            self.vector_size = len(existing)
            return existing
        
        # Not in Chroma - generate with Gemini
        # If model is locked, only use that model. Otherwise try fallback models.
        if self.model_locked:
            model_try_order = [self.model_name]
        else:
            model_try_order = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]

        for model_name in model_try_order:
            try:
                result = genai.embed_content(
                    model=model_name,
                    content=text,
                    task_type="retrieval_document"
                )

                embedding = result['embedding']
                actual_dim = len(embedding)
                
                # If this is the first generation from Gemini, lock the dimensions
                if not self.model_locked:
                    self.vector_size = actual_dim
                
                self.model_name = model_name
                self.model_locked = True  # Lock model after first successful use
                
                # Store in Chroma (persistent)
                self.chroma.add_embedding(text, embedding, metadata={"source": "gemini", "model": model_name})
                return embedding
            except Exception as e:
                continue

        print(f"Error generating embedding: no supported embedding model worked for text='{text[:30]}'")
        return [0.0] * self.vector_size
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts efficiently.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            embeddings.append(self.get_embedding(text))
        
        return embeddings
    
    def clear_cache(self):
        """Clear embeddings from Chroma."""
        self.chroma.clear()
    
    def get_cache_size(self) -> int:
        """Get the number of cached embeddings in Chroma."""
        return self.chroma.count()
    
    def query_similar(self, embedding: List[float], k: int = 3, threshold: float = 0.85) -> List[tuple]:
        """
        Query for similar embeddings already stored in Chroma.
        
        Args:
            embedding: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (text, similarity, metadata) tuples
        """
        return self.chroma.query(embedding, k=k, threshold=threshold)
