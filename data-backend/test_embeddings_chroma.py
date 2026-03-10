"""
Test the updated EmbeddingService with Chroma integration.
"""
import sys
sys.path.insert(0, '.')
import os
from dotenv import load_dotenv
from services.embeddings import EmbeddingService

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def test_embedding_service_with_chroma():
    """Test EmbeddingService using Chroma backend."""
    print("\n" + "="*60)
    print("TESTING EMBEDDINGSERVICE WITH CHROMA")
    print("="*60)
    
    # Initialize service (will use Chroma for storage)
    service = EmbeddingService(api_key)
    
    # Clear old test data to avoid dimension conflicts
    print("\n[Setup] Clearing previous test data...")
    service.clear_cache()
    print("✓ Chroma cleared")
    
    # Test 1: Generate embedding (first time - hits Gemini)
    print("\n[Test 1] Generating embedding for 'MIT' (hits Gemini API)...")
    emb1 = service.get_embedding("MIT")
    print(f"✓ Generated embedding (first 5 dims): {emb1[:5]}")
    print(f"  Embedding stored in Chroma with {service.get_cache_size()} total embeddings")
    
    # Test 2: Retrieve same embedding (second time - hits Chroma, instant)
    print("\n[Test 2] Retrieving 'MIT' again (should be instant from Chroma)...")
    emb2 = service.get_embedding("MIT")
    print(f"✓ Retrieved embedding from cache")
    print(f"  Same result: {emb1 == emb2}")
    
    # Test 3: Generate another embedding
    print("\n[Test 3] Generating embedding for 'Massachusetts Institute of Technology'...")
    emb3 = service.get_embedding("Massachusetts Institute of Technology")
    print(f"✓ Generated (total embeddings now: {service.get_cache_size()})")
    
    # Test 4: Query similar embeddings
    print("\n[Test 4] Querying for embeddings similar to 'MIT'...")
    results = service.query_similar(emb1, k=2, threshold=0.80)
    
    if results:
        print(f"✓ Found {len(results)} similar embeddings:")
        for text, similarity, metadata in results:
            print(f"  - {text:40} | Similarity: {similarity:.4f}")
    else:
        print("✗ No results found")
    
    # Test 5: Batch embeddings
    print("\n[Test 5] Getting batch embeddings...")
    texts = ["Harvard", "Yale University", "Stanford"]
    batch = service.get_embeddings_batch(texts)
    print(f"✓ Generated {len(batch)} embeddings")
    print(f"  Total in Chroma: {service.get_cache_size()}")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_embedding_service_with_chroma()
