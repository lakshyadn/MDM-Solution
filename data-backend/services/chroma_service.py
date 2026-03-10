"""
Chroma Vector Database Service for storing and querying embeddings.
Provides persistent local vector storage with similarity search.
"""
import chromadb
from typing import List, Dict, Optional, Tuple
import os


class ChromaService:
    """Service for managing embeddings in Chroma vector database."""
    
    def __init__(self, persist_directory: str = "./chroma_data"):
        """
        Initialize Chroma service with persistent storage.
        
        Args:
            persist_directory: Path to store Chroma data
        """
        self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize Chroma client with persistence (new API)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create or get collection for storing embeddings
        self.collection = self.client.get_or_create_collection(
            name="embeddings"
        )
        
        print(f"✓ Chroma initialized with persistence at: {persist_directory}")
    
    def add_embedding(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a single embedding to the collection.
        
        Args:
            text: Text that was embedded
            embedding: Embedding vector
            metadata: Additional metadata (e.g., source, type)
        """
        if not metadata:
            metadata = {}
        
        # Use text as ID (prevents duplicates)
        text_id = self._create_id(text)
        
        try:
            self.collection.upsert(
                ids=[text_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
            print(f"✓ Added embedding for: {text[:50]}")
        except Exception as e:
            print(f"✗ Error adding embedding for {text}: {e}")
    
    def query(
        self,
        query_embedding: List[float],
        k: int = 3,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict]]:
        """
        Query for similar embeddings.
        
        Args:
            query_embedding: Embedding vector to search for
            k: Number of results to return
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of (text, similarity, metadata) tuples, sorted by similarity descending
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "distances", "metadatas"]
            )
            
            if not results or not results['documents'] or len(results['documents'][0]) == 0:
                return []
            
            # Convert distances to similarities (Chroma returns distances, not similarities)
            # For cosine: similarity = 1 - distance
            output = []
            for i, (text, distance, metadata) in enumerate(
                zip(
                    results['documents'][0],
                    results['distances'][0],
                    results['metadatas'][0]
                )
            ):
                # Chroma cosine distance is 1 - similarity, so convert back
                similarity = 1 - distance
                
                if similarity >= threshold:
                    output.append((text, similarity, metadata))
            
            return output
        
        except Exception as e:
            print(f"✗ Error querying Chroma: {e}")
            return []
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieve a stored embedding by text.
        
        Args:
            text: Text to look up
            
        Returns:
            Embedding vector if found, None otherwise
        """
        text_id = self._create_id(text)
        
        try:
            results = self.collection.get(
                ids=[text_id],
                include=["embeddings"]
            )
            
            if results and 'embeddings' in results and results['embeddings'] is not None:
                if len(results['embeddings']) > 0:
                    return list(results['embeddings'][0])
            return None
        
        except Exception as e:
            print(f"✗ Error retrieving embedding: {e}")
            return None
    
    def exists(self, text: str) -> bool:
        """
        Check if embedding exists for a text.
        
        Args:
            text: Text to check
            
        Returns:
            True if embedding exists, False otherwise
        """
        return self.get_embedding(text) is not None
    
    def count(self) -> int:
        """Get total number of embeddings in collection."""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"✗ Error counting: {e}")
            return 0
    
    def clear(self) -> None:
        """Clear all embeddings from the collection."""
        try:
            self.client.delete_collection(name="embeddings")
            self.collection = self.client.get_or_create_collection(
                name="embeddings"
            )
            print("✓ Chroma collection cleared")
        except Exception as e:
            print(f"✗ Error clearing collection: {e}")
    
    def persist(self) -> None:
        """Manually persist data to disk (Chroma auto-persists, but can be called explicitly)."""
        try:
            self.client.persist()
            print("✓ Chroma data persisted to disk")
        except Exception as e:
            print(f"✗ Error persisting: {e}")
    
    def _create_id(self, text: str) -> str:
        """Create a unique ID from text (hash-based)."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def get_collection_info(self) -> Dict:
        """Get metadata about the collection."""
        return {
            "collection_name": self.collection.name,
            "total_embeddings": self.count(),
            "metadata": self.collection.metadata
        }
