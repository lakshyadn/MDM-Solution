"""
Test script to verify embedding similarity is working correctly
"""
import os
from dotenv import load_dotenv
from services.embeddings import EmbeddingService
from utils.similarity import cosine_similarity

# Load environment variables from .env file
load_dotenv()

# Get API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: GOOGLE_API_KEY not set in .env file")
    exit(1)

# Initialize embedding service
print("Initializing embedding service...")
embedding_service = EmbeddingService(api_key)
print(f"✓ Service initialized (model: {embedding_service.model_name})\n")

# Test cases: abbreviations vs full forms
test_cases = [
    ('MIT', 'Massachusetts Institute of Technology'),
    ('UCLA', 'University of California Los Angeles'),
    ('UCL', 'University College London'),
    ('Caltech', 'California Institute of Technology'),
    ('NYU', 'New York University'),
    ('LSE', 'London School of Economics and Political Science'),
    
]

print('EMBEDDING SIMILARITY TEST')
print('=' * 70)
print(f"{'Abbreviation':<15} {'Full Name':<40} {'Similarity':<12} {'Status'}")
print('=' * 70)

for abbrev, full_name in test_cases:
    # Get embeddings
    emb1 = embedding_service.get_embedding(abbrev)
    emb2 = embedding_service.get_embedding(full_name)

    if not any(emb1) or not any(emb2):
        print(f"{abbrev:<15} {full_name:<40} {'0.0000':<12} ✗ EMBEDDING FAILED")
        continue
    
    # Calculate similarity
    similarity = cosine_similarity(emb1, emb2)
    
    # Determine status
    if similarity >= 0.85:
        status = '✓ EMIT ANOMALY'
    elif similarity >= 0.70:
        status = '→ FIND MATCH'
    else:
        status = '✗ GO TO LLM'
    
    print(f"{abbrev:<15} {full_name:<40} {similarity:.4f}       {status}")

print('=' * 70)
print("\nThresholds:")
print("  >= 0.85: Confident match, emit embedding anomaly")
print("  >= 0.70: Find match candidate for comparison")
print("  <  0.70: No match, send to LLM")
print("  0.0000 + EMBEDDING FAILED: model/API issue")
