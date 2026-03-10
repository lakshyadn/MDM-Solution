"""
LLM-based reasoning service for complex discrepancy analysis.
Used as final step when fuzzy matching and embeddings are uncertain.
"""
import google.generativeai as genai
import json
from typing import Dict, List, Optional


class GeminiReasoner:
    """Service for LLM-based reasoning on uncertain record matches."""
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini reasoning service.
        
        Args:
            api_key: Google API key for Gemini
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
    
    def analyze_records_batch(
        self,
        records_batch: List[Dict],
        identifier_field: str = "name"
    ) -> List[Dict]:
        """
        Analyze multiple records with no match in master1.
        Used when master1 has no confident match (all steps failed).
        
        Args:
            records_batch: List of dictionaries, each containing:
                - given_record: The record to analyze
                - master1_record: Corresponding master1 record (may be None)
            identifier_field: Field name used to identify records
            
        Returns:
            List of all anomalies found across all records
        """
        if not records_batch:
            return []
        
        # Build batch prompt
        prompt = self._build_batch_analysis_prompt(records_batch, identifier_field)
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            json_match = response_text
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_match = response_text.split("```")[1].split("```")[0]
            
            anomalies = json.loads(json_match.strip())
            
            # Ensure it's a list
            if isinstance(anomalies, dict):
                anomalies = [anomalies] if anomalies else []
            
            return anomalies
            
        except Exception as e:
            print(f"Error in batch LLM reasoning: {e}")
            return []
    
    def _build_batch_analysis_prompt(
        self,
        records_batch: List[Dict],
        identifier_field: str
    ) -> str:
        """Build prompt for batch record analysis."""
        records_text = ""
        for idx, record_set in enumerate(records_batch, 1):
            given = record_set.get('given_record', {})
            master1 = record_set.get('master1_record')
            
            records_text += f"\n--- Record {idx} ---\n"
            records_text += f"Given: {json.dumps(given)}\n"
            records_text += f"Master (Preferred): {json.dumps(master1) if master1 else 'Not found'}\n"
        
        prompt = f"""You are a data quality expert. Analyze these records that did not match confidently in the preferred database.

{records_text}

Task:
1. Compare each given record against its master (preferred) record if available
2. Identify any discrepancies, typos, or data quality issues
3. If no master record exists, flag as uncertain/missing
4. Focus on meaningful errors that should be corrected

Return a JSON array of anomalies found (empty array if no issues):
[
  {{
    "record_id": "id",
    "record_identifier": "identifier value",
    "field": "field_name",
    "given_value": "current value",
    "correct_value": "corrected value",
    "reason": "Brief explanation of the issue"
  }}
]

Return ONLY the JSON array, no additional text."""
        
        return prompt
