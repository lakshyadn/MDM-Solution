"""
Text normalization utilities for improving matching accuracy.
"""
import re
from typing import Dict

# Common abbreviations and their expansions
ABBREVIATION_MAP = {
    "univ": "university",
    "inst": "institute",
    "tech": "technology",
    "calif": "california",
    "ca": "california",
    "ny": "new york",
    "ma": "massachusetts",
    "tx": "texas",
    "uk": "united kingdom",
    "usa": "united states",
    "us": "united states",
    "st": "saint",
    "mt": "mount",
    "ft": "fort",
    "dr": "drive",
    "ave": "avenue",
    "blvd": "boulevard",
    "rd": "road",
    "dept": "department",
    "corp": "corporation",
    "inc": "incorporated",
    "ltd": "limited",
    "co": "company",
}


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by:
    - Converting to lowercase
    - Removing extra whitespace
    - Removing punctuation
    - Expanding common abbreviations
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text string
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Convert to lowercase
    text = text.lower().strip()
    
    # Remove punctuation except spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Expand abbreviations
    words = text.split()
    expanded_words = []
    for word in words:
        # Check if word (without dots) is in abbreviation map
        clean_word = word.replace('.', '')
        if clean_word in ABBREVIATION_MAP:
            expanded_words.append(ABBREVIATION_MAP[clean_word])
        else:
            expanded_words.append(word)
    
    return ' '.join(expanded_words)


def create_record_hash(record: Dict[str, str], fields: list = None) -> str:
    """
    Create a hash of a record for quick exact matching.
    
    Args:
        record: Dictionary containing record data
        fields: List of field names to include in hash. If None, uses all fields except ID fields.
        
    Returns:
        String hash of normalized record values
    """
    # Skip ID and metadata fields
    skip_fields = ['id', 'record_id', 'updated_at', 'updated_by']
    
    if fields is None:
        fields = [k for k in sorted(record.keys()) if k.lower() not in skip_fields]
    
    # Create normalized string of all field values
    values = []
    for field in fields:
        if field in record:
            values.append(normalize_text(record[field]))
    
    return '|'.join(values)
