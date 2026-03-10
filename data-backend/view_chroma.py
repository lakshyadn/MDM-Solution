"""
View all embeddings stored in Chroma database.
"""
import sys
sys.path.insert(0, '.')
from services.chroma_service import ChromaService

def view_chroma_embeddings():
    """Display all embeddings in Chroma."""
    print("\n" + "="*60)
    print("CHROMA EMBEDDINGS VIEWER")
    print("="*60)
    
    chroma = ChromaService(persist_directory="./chroma_data")
    
    # Get collection info
    info = chroma.get_collection_info()
    print(f"\nCollection: {info['collection_name']}")
    print(f"Total embeddings: {info['total_embeddings']}")
    print(f"Metadata: {info['metadata']}")
    
    # Get all data from collection
    try:
        results = chroma.collection.get(
            include=["documents", "metadatas", "embeddings"]
        )
        
        if not results or not results['documents']:
            print("\nNo embeddings found in Chroma.")
            return
        
        print("\n" + "-"*60)
        print("STORED EMBEDDINGS")
        print("-"*60)
        
        for i, (doc, metadata, embedding) in enumerate(
            zip(results['documents'], results['metadatas'], results['embeddings']), 1
        ):
            print(f"\n[{i}] Text: {doc[:60]}")
            print(f"    Dimensions: {len(embedding)}")
            print(f"    First 5 values: {embedding[:5]}")
            if metadata:
                print(f"    Metadata: {metadata}")
        
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"\nError retrieving embeddings: {e}")


if __name__ == "__main__":
    view_chroma_embeddings()
