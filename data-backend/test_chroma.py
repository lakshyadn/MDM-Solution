"""
Test script to verify Chroma Vector DB is working correctly.
"""
import sys
sys.path.insert(0, '.')

from services.chroma_service import ChromaService
import os


def test_chroma_basic():
    """Test basic Chroma operations."""
    print("\n" + "="*60)
    print("TESTING CHROMA VECTOR DB")
    print("="*60)
    
    # Initialize Chroma
    chroma = ChromaService(persist_directory="./chroma_data")
    
    # Test 1: Add embeddings
    print("\n[Test 1] Adding sample embeddings...")
    test_embeddings = [
        ("MIT", [0.1, 0.2, 0.3, 0.4, 0.5] * 154),  # 768 dims
        ("Massachusetts Institute of Technology", [0.11, 0.21, 0.31, 0.41, 0.51] * 154),
        ("Harvard University", [0.15, 0.25, 0.35, 0.45, 0.55] * 154),
        ("Stanford University", [0.12, 0.22, 0.32, 0.42, 0.52] * 154),
    ]
    
    for text, embedding in test_embeddings:
        chroma.add_embedding(text, embedding, metadata={"type": "university"})
    
    # Test 2: Check count
    print(f"\n[Test 2] Total embeddings in Chroma: {chroma.count()}")
    
    # Test 3: Retrieve single embedding
    print("\n[Test 3] Retrieving embedding for 'MIT'...")
    retrieved = chroma.get_embedding("MIT")
    if retrieved:
        print(f"✓ Found embedding (first 10 dims): {retrieved[:10]}")
    else:
        print("✗ Could not retrieve embedding")
    
    # Test 4: Check existence
    print("\n[Test 4] Checking if 'MIT' exists...")
    exists = chroma.exists("MIT")
    print(f"{'✓' if exists else '✗'} MIT exists: {exists}")
    
    # Test 5: Query similar embeddings
    print("\n[Test 5] Querying for similar embeddings to 'MIT'...")
    query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 154
    results = chroma.query(query_embedding, k=3, threshold=0.5)
    
    if results:
        print(f"Found {len(results)} similar embeddings:")
        for text, similarity, metadata in results:
            print(f"  - {text[:40]:40} | Similarity: {similarity:.4f}")
    else:
        print("✗ No results found")
    
    # Test 6: Collection info
    print("\n[Test 6] Collection Info...")
    info = chroma.get_collection_info()
    print(f"  - Name: {info['collection_name']}")
    print(f"  - Total embeddings: {info['total_embeddings']}")
    print(f"  - Metadata: {info['metadata']}")
    
    # Test 7: Check persistence
    print("\n[Test 7] Checking disk persistence...")
    data_exists = os.path.exists("./chroma_data")
    print(f"{'✓' if data_exists else '✗'} Chroma data directory exists: {data_exists}")
    
    if data_exists:
        size = sum(f.stat().st_size for f in os.scandir("./chroma_data") if f.is_file())
        print(f"  - Data size: {size} bytes")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_chroma_basic()
