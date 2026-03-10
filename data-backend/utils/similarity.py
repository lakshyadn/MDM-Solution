"""
Similarity calculation utilities for embeddings and text comparison.
"""
import numpy as np
from typing import List


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Cosine similarity measures the cosine of the angle between two vectors,
    ranging from -1 (opposite) to 1 (identical). For embeddings, values
    closer to 1 indicate higher semantic similarity.
    
    Args:
        vec1: First vector (embedding)
        vec2: Second vector (embedding)
        
    Returns:
        Cosine similarity score between 0 and 1
    """
    # Convert to numpy arrays
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Calculate cosine similarity
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # Avoid division by zero
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    similarity = dot_product / (norm_a * norm_b)
    
    # Clamp to [0, 1] range (embeddings are typically positive)
    return max(0.0, min(1.0, similarity))