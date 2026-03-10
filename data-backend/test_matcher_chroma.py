"""
Test the updated matcher with Chroma row embeddings integration.
"""
import sys
sys.path.insert(0, '.')
import os
from dotenv import load_dotenv
from services.matcher import MatcherService
import json

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Sample test data
GIVEN_DATA = [
    {
        "id": 1,
        "university_name": "MIT",
        "city": "Cambridge",
        "country": "USA",
        "website": "mit.edu",
        "type": "Private"
    },
    {
        "id": 2,
        "university_name": "Harvard",
        "city": "Cambridge",
        "country": "USA",
        "website": "harvard.edu",
        "type": "Private"
    }
]

MASTER1_DATA = [
    {
        "id": 101,
        "university_name": "Massachusetts Institute of Technology",
        "city": "Cambridge",
        "country": "USA",
        "website": "mit.edu",
        "type": "Private"
    },
    {
        "id": 102,
        "university_name": "Harvard University",
        "city": "Cambridge",
        "country": "USA",
        "website": "harvard.edu",
        "type": "Private"
    }
]

MASTER2_DATA = [
    {
        "id": 201,
        "university_name": "MIT (Alternative)",
        "city": "Cambridge",
        "country": "USA",
        "website": "web.mit.edu",
        "type": "Academic"
    }
]

def test_matcher_with_chroma():
    """Test matcher with Chroma row embeddings."""
    print("\n" + "="*60)
    print("TESTING MATCHER WITH CHROMA ROW EMBEDDINGS")
    print("="*60)
    
    # Initialize matcher
    print("\n[Init] Creating matcher service...")
    matcher = MatcherService(api_key)
    
    # Run analysis
    print("\n[Analysis] Running 4-step pipeline on sample data...")
    anomalies, stats = matcher.analyze_datasets(
        given_data=GIVEN_DATA,
        master1_data=MASTER1_DATA,
        master2_data=MASTER2_DATA,
        identifier_field="university_name"
    )
    
    # Print results
    print("\n" + "-"*60)
    print("STATISTICS")
    print("-"*60)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-"*60)
    print(f"ANOMALIES FOUND: {len(anomalies)}")
    print("-"*60)
    
    if anomalies:
        for i, anomaly in enumerate(anomalies, 1):
            print(f"\n[{i}] {anomaly.get('record_identifier')} - {anomaly.get('field')}")
            print(f"    Given: {anomaly.get('given_value')}")
            print(f"    Expected: {anomaly.get('correct_value')}")
            print(f"    Reason: {anomaly.get('reason')}")
            if 'secondary_reference' in anomaly:
                print(f"    Secondary: {anomaly.get('secondary_reference')}")
    else:
        print("No anomalies found")
    
    print("\n" + "="*60)
    print("✓ TEST COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_matcher_with_chroma()
