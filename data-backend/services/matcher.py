"""
4-Step Pipeline Matcher Service
Orchestrates exact matching, fuzzy matching, embedding similarity, and LLM reasoning.
"""
from typing import Dict, List, Tuple, Optional
from rapidfuzz import fuzz
from utils.normalize import normalize_text, create_record_hash
from utils.similarity import cosine_similarity
from services.embeddings import EmbeddingService
from services.gemini_reasoner import GeminiReasoner


class MatcherService:
    """
    Main service for matching records using 4-step pipeline:
    1. Exact match (normalized) - eliminates 60-70%
    2. Fuzzy match (RapidFuzz) - eliminates 50% of remaining
    3. Embedding similarity - eliminates 70% of remaining
    4. LLM reasoning - for final 5% uncertain cases
    """
    
    # Thresholds for each step
    FUZZY_THRESHOLD = 85  # 85% similarity for fuzzy match
    EMBEDDING_THRESHOLD = 0.85  # 0.85 cosine similarity for embeddings
    BATCH_SIZE = 10  # Number of records to send to LLM at once
    
    def __init__(self, api_key: str):
        """
        Initialize the matcher service.
        
        Args:
            api_key: Google API key for Gemini services
        """
        self.embedding_service = EmbeddingService(api_key)
        self.gemini_reasoner = GeminiReasoner(api_key)
        self.stats = {
            'total': 0,
            'exact_match': 0,
            'fuzzy_anomalies': 0,
            'embedding_anomalies': 0,
            'llm_analyzed': 0,
            'anomalies_found': 0
        }
        # Fast lookup for row_string -> master record (avoids repeated scans)
        self.master_row_lookup: Dict[str, Dict] = {}
    
    def analyze_datasets(
        self,
        given_data: List[Dict],
        master1_data: List[Dict],
        master2_data: List[Dict],
        identifier_field: str = "name"
    ) -> Tuple[List[Dict], Dict]:
        """
        Analyze given dataset against master datasets using 4-step pipeline.
        NOW EMITS ANOMALIES FROM ALL STEPS, not just LLM.
        
        Args:
            given_data: List of records to check
            master1_data: Primary reference dataset
            master2_data: Secondary reference dataset (alternative names)
            identifier_field: Field name used to match records across datasets
            
        Returns:
            Tuple of (anomalies_list, statistics_dict)
        """
        # Reset statistics
        self.stats = {
            'total': len(given_data),
            'exact_match': 0,
            'fuzzy_anomalies': 0,
            'embedding_anomalies': 0,
            'llm_analyzed': 0,
            'anomalies_found': 0
        }
        
        all_anomalies = []
        
        # Create lookup dictionaries for master data
        # Keep all candidates per identifier (do not overwrite duplicates).
        master1_lookup: Dict[str, List[Dict]] = {}
        for record in master1_data:
            identifier_value = record.get(identifier_field, '')
            if identifier_value:
                normalized_key = self._normalize_identifier(identifier_value)
                master1_lookup.setdefault(normalized_key, []).append(record)

        master2_lookup = {self._normalize_identifier(r.get(identifier_field, '')): r 
                         for r in master2_data if r.get(identifier_field)}
        master2_by_record_id = {
            str(r.get('id', r.get('record_id'))): r
            for r in master2_data
            if r.get('id', r.get('record_id')) is not None
        }

        # Pre-compute master row embeddings for Step 3 (stored in Chroma)
        self._precompute_master_row_embeddings(master1_data)
        
        # Track records that need LLM analysis
        llm_batch = []
        
        for given_record in given_data:
            identifier = given_record.get(identifier_field, '')
            normalized_id = self._normalize_identifier(identifier)
            
            # Find matching master1 record (preferred/primary)
            master1_candidates = master1_lookup.get(normalized_id, [])
            master1_record = self._select_best_duplicate_candidate(
                given_record=given_record,
                candidates=master1_candidates,
                identifier_field=identifier_field
            )
            
            # Step 1: Exact Match (Normalized) - against master1 only
            if master1_record and self._exact_match_single(given_record, master1_record):
                self.stats['exact_match'] += 1
                continue
            
            # Step 2: Fuzzy Match
            # If no exact identifier match, find best fuzzy match in master1
            if not master1_record:
                master1_record = self._find_best_fuzzy_match(
                    given_record, master1_data, identifier_field
                )
            
            fuzzy_confident, fuzzy_anomalies = self._fuzzy_match_with_anomalies_single(
                given_record, master1_record, identifier_field
            )
            if fuzzy_confident:
                # Fuzzy match is confident (>= 85% similar)
                if fuzzy_anomalies:
                    # Found anomalies - enrich with secondary reference
                    matched_identifier = master1_record.get(identifier_field, '') if master1_record else ''
                    self._enrich_anomalies_with_secondary(
                        anomalies=fuzzy_anomalies,
                        master2_lookup=master2_lookup,
                        master2_by_record_id=master2_by_record_id,
                        fallback_identifier=matched_identifier
                    )
                    all_anomalies.extend(fuzzy_anomalies)
                    self.stats['fuzzy_anomalies'] += len(fuzzy_anomalies)
                else:
                    # Perfect match, no anomalies
                    self.stats['exact_match'] += 1
                continue
            
            # Step 3: Row Embedding Similarity (Optimized)
            # Find best master match using full-row semantic similarity
            # (this catches abbreviation cases like MIT -> Massachusetts Institute of Technology)
            if not fuzzy_confident:
                master1_record, _ = self._embedding_match_with_row_similarity(
                    given_record, master1_data, identifier_field, k=3, threshold=0.80
                )
            
            embedding_confident, embedding_anomalies = self._embedding_match_with_anomalies_single(
                given_record, master1_record, identifier_field
            )
            if embedding_confident:
                # Embedding match is confident (>= 0.85 similar)
                if embedding_anomalies:
                    # Found anomalies - enrich with secondary reference
                    matched_identifier = master1_record.get(identifier_field, '') if master1_record else ''
                    self._enrich_anomalies_with_secondary(
                        anomalies=embedding_anomalies,
                        master2_lookup=master2_lookup,
                        master2_by_record_id=master2_by_record_id,
                        fallback_identifier=matched_identifier
                    )
                    all_anomalies.extend(embedding_anomalies)
                    self.stats['embedding_anomalies'] += len(embedding_anomalies)
                else:
                    # Perfect semantic match, no anomalies
                    self.stats['exact_match'] += 1
                continue
            
            # Step 4: Queue for LLM Analysis (only master1 has no confident match)
            llm_batch.append({
                'given_record': given_record,
                'master1_record': master1_record
            })
            
            # Process batch if it reaches size limit
            if len(llm_batch) >= self.BATCH_SIZE:
                batch_anomalies = self._process_llm_batch(llm_batch, identifier_field)
                self._enrich_anomalies_with_secondary(
                    anomalies=batch_anomalies,
                    master2_lookup=master2_lookup,
                    master2_by_record_id=master2_by_record_id
                )
                all_anomalies.extend(batch_anomalies)
                llm_batch = []
        
        # Process remaining records in final batch
        if llm_batch:
            batch_anomalies = self._process_llm_batch(llm_batch, identifier_field)
            self._enrich_anomalies_with_secondary(
                anomalies=batch_anomalies,
                master2_lookup=master2_lookup,
                master2_by_record_id=master2_by_record_id
            )
            all_anomalies.extend(batch_anomalies)
        
        self.stats['anomalies_found'] = len(all_anomalies)
        
        return all_anomalies, self.stats

    def _enrich_anomalies_with_secondary(
        self,
        anomalies: List[Dict],
        master2_lookup: Dict[str, Dict],
        master2_by_record_id: Dict[str, Dict],
        fallback_identifier: str = ""
    ) -> None:
        """Attach secondary_reference for anomalies when available in secondary master."""
        for anomaly in anomalies:
            if anomaly.get('secondary_reference') is not None:
                continue

            field = anomaly.get('field')
            if not field:
                continue

            master2_record = None

            # 1) Try anomaly's own identifier first
            anomaly_identifier = anomaly.get('record_identifier')
            if anomaly_identifier:
                master2_record = master2_lookup.get(self._normalize_identifier(str(anomaly_identifier)))

            # 2) Fallback to matched primary identifier (useful when given identifier is misspelled)
            if not master2_record and fallback_identifier:
                master2_record = master2_lookup.get(self._normalize_identifier(str(fallback_identifier)))

            # 3) Fallback to record id lookup
            if not master2_record:
                record_id = anomaly.get('record_id')
                if record_id is not None:
                    master2_record = master2_by_record_id.get(str(record_id))

            if not master2_record:
                continue

            secondary_value = master2_record.get(field)
            if secondary_value is not None and str(secondary_value).strip() != "":
                anomaly['secondary_reference'] = secondary_value
    
    def _find_best_fuzzy_match(
        self,
        given_record: Dict,
        master_data: List[Dict],
        identifier_field: str
    ) -> Optional[Dict]:
        """
        Find the best matching master record using fuzzy matching on identifier field.
        Used when exact identifier lookup fails.
        
        Args:
            given_record: Record to match
            master_data: List of master records to search
            identifier_field: Field to use for fuzzy matching
            
        Returns:
            Best matching master record, or None if no good match
        """
        given_id = given_record.get(identifier_field, '')
        if not given_id:
            return None
        
        given_id_normalized = normalize_text(given_id)
        best_score = 0
        best_match = None
        
        for master_record in master_data:
            master_id = master_record.get(identifier_field, '')
            if not master_id:
                continue
            
            master_id_normalized = normalize_text(master_id)
            score = fuzz.ratio(given_id_normalized, master_id_normalized)
            
            if score > best_score:
                best_score = score
                best_match = master_record
        
        # Only return match if score is reasonably high (>= 80%)
        return best_match if best_score >= 80 else None

    def _select_best_duplicate_candidate(
        self,
        given_record: Dict,
        candidates: List[Dict],
        identifier_field: str
    ) -> Optional[Dict]:
        """
        Select best record among duplicate identifier candidates.

        Uses deterministic multi-field scoring so duplicate names
        (e.g., Harvard USA vs Harvard UK) map to the closest row.
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        discriminator_fields = [
            'country',
            'city',
            'founded_year',
            'student_count',
            'website',
        ]

        given_identifier = normalize_text(str(given_record.get(identifier_field, '')))
        scored_candidates = []

        for index, candidate in enumerate(candidates):
            exact_matches = 0
            score = 0.0

            candidate_identifier = normalize_text(str(candidate.get(identifier_field, '')))
            if given_identifier and candidate_identifier:
                identifier_score = fuzz.ratio(given_identifier, candidate_identifier) / 100.0
                score += identifier_score * 2.0
                if given_identifier == candidate_identifier:
                    exact_matches += 1

            for field in discriminator_fields:
                given_val = normalize_text(str(given_record.get(field, '')))
                candidate_val = normalize_text(str(candidate.get(field, '')))

                if not given_val or not candidate_val:
                    continue

                field_score = fuzz.ratio(given_val, candidate_val) / 100.0
                score += field_score

                if given_val == candidate_val:
                    exact_matches += 1

            scored_candidates.append((score, exact_matches, -index, candidate))

        # Deterministic pick: highest score, then more exact matches, then stable order
        scored_candidates.sort(reverse=True, key=lambda x: (x[0], x[1], x[2]))
        return scored_candidates[0][3]
    
    def _normalize_identifier(self, identifier: str) -> str:
        """Normalize identifier for matching."""
        return normalize_text(identifier)
    def _exact_match_single(
        self,
        given: Dict,
        master1: Optional[Dict]
    ) -> bool:
        """
        Step 1 (Single-master): Check if records match exactly after normalization.
        Compare ONLY against preferred master (master1).
        
        Args:
            given: Record from given dataset
            master1: Record from preferred master dataset
            
        Returns:
            True if exact match found, False otherwise
        """
        if not master1:
            return False
        
        # Create normalized hashes
        given_hash = create_record_hash(given)
        master1_hash = create_record_hash(master1)
        
        return given_hash == master1_hash
    
    def _fuzzy_match_with_anomalies_single(
        self,
        given: Dict,
        master1: Optional[Dict],
        identifier_field: str
    ) -> Tuple[bool, List[Dict]]:
        """
        Step 2 (Single-master): Check fuzzy string similarity AND collect field-level anomalies.
        Compare ONLY against preferred master (master1).
        
        Args:
            given: Record from given dataset
            master1: Record from preferred master dataset
            identifier_field: Field used to identify records
            
        Returns:
            Tuple of (is_confident_match: bool, anomalies: List[Dict])
            - is_confident_match: True if fuzzy score >= threshold, False otherwise
            - anomalies: List of anomaly objects found (empty if no differences)
        """
        if not master1:
            return (False, [])
        
        # Skip ID fields
        skip_fields = ['id', 'record_id', 'updated_at', 'updated_by']
        fields_to_check = [k for k in given.keys() if k.lower() not in skip_fields]
        
        anomalies = []
        overall_scores = []
        
        for field in fields_to_check:
            given_val = str(given.get(field, ''))
            given_val_normalized = normalize_text(given_val)
            
            best_score = 0
            best_correct_val = None
            
            # Compare with master1 only
            if field in master1:
                master1_val = str(master1.get(field, ''))
                master1_val_normalized = normalize_text(master1_val)
                score = fuzz.ratio(given_val_normalized, master1_val_normalized)
                
                if score > best_score:
                    best_score = score
                    best_correct_val = master1_val
            
            overall_scores.append(best_score)
            
            # If field has a high-confidence fuzzy match but differs, create anomaly
            if best_score >= self.FUZZY_THRESHOLD and best_score < 100 and best_correct_val:
                # Only emit if values actually differ (post-normalization)
                if given_val_normalized != normalize_text(best_correct_val):
                    anomalies.append({
                        "record_id": given.get('id', given.get('record_id', '')),
                        "record_identifier": given.get(identifier_field, ''),
                        "field": field,
                        "given_value": given_val,
                        "correct_value": best_correct_val,
                        "reason": f"Spelling/formatting error (confidence: {best_score:.2f}%)",
                        "source": "fuzzy"
                    })
            # If field differs with low fuzzy score, still emit as value mismatch
            elif best_correct_val and given_val_normalized != normalize_text(best_correct_val):
                anomalies.append({
                    "record_id": given.get('id', given.get('record_id', '')),
                    "record_identifier": given.get(identifier_field, ''),
                    "field": field,
                    "given_value": given_val,
                    "correct_value": best_correct_val,
                    "reason": f"Value mismatch detected (confidence: {best_score:.2f}%)",
                    "source": "fuzzy"
                })
        
        # Check if overall average passes threshold
        if overall_scores:
            avg_score = sum(overall_scores) / len(overall_scores)
            if avg_score >= self.FUZZY_THRESHOLD:
                # Confident match - return True with any anomalies found
                return (True, anomalies)
        
        # Not confident enough - continue to next step
        return (False, [])
    
    def _embedding_match_with_anomalies_single(
        self,
        given: Dict,
        master1: Optional[Dict],
        identifier_field: str
    ) -> Tuple[bool, List[Dict]]:
        """
        Step 3 (Single-master): Check semantic similarity AND collect field-level anomalies.
        Compare ONLY against preferred master (master1).
        
        Args:
            given: Record from given dataset
            master1: Record from preferred master dataset
            identifier_field: Field used to identify records
            
        Returns:
            Tuple of (is_confident_match: bool, anomalies: List[Dict])
            - is_confident_match: True if embedding similarity >= threshold, False otherwise
            - anomalies: List of anomaly objects found (empty if no differences)
        """
        if not master1:
            return (False, [])
        
        # Skip ID fields
        skip_fields = ['id', 'record_id', 'updated_at', 'updated_by']
        fields_to_check = [k for k in given.keys() if k.lower() not in skip_fields]
        
        anomalies = []
        overall_similarity_scores = []
        
        for field in fields_to_check:
            given_val = str(given.get(field, ''))
            if not self._is_embedding_candidate(given_val):
                continue
            
            # Get embedding for given value
            given_embedding = self.embedding_service.get_embedding(given_val)
            
            best_similarity = 0
            best_correct_val = None
            
            # Compare with master1 only
            if field in master1:
                master1_val = str(master1.get(field, ''))
                if self._is_embedding_candidate(master1_val):
                    master1_embedding = self.embedding_service.get_embedding(master1_val)
                    sim = cosine_similarity(given_embedding, master1_embedding)
                    
                    if sim > best_similarity:
                        best_similarity = sim
                        best_correct_val = master1_val
            
            overall_similarity_scores.append(best_similarity)
            
            # If field has high semantic similarity but differs, create anomaly
            if best_similarity >= self.EMBEDDING_THRESHOLD and best_similarity < 0.99 and best_correct_val:
                # Only emit if values actually differ (post-normalization)
                if normalize_text(given_val) != normalize_text(best_correct_val):
                    anomalies.append({
                        "record_id": given.get('id', given.get('record_id', '')),
                        "record_identifier": given.get(identifier_field, ''),
                        "field": field,
                        "given_value": given_val,
                        "correct_value": best_correct_val,
                        "reason": f"Semantic/alias variation (confidence: {best_similarity * 100:.2f}%)",
                        "source": "embedding"
                    })
        
        # Check if overall average passes threshold
        if overall_similarity_scores:
            avg_similarity = sum(overall_similarity_scores) / len(overall_similarity_scores)
            if avg_similarity >= self.EMBEDDING_THRESHOLD:
                # Confident match - return True with any anomalies found
                return (True, anomalies)
        
        # Not confident enough - continue to next step
        return (False, [])

    
    def _build_row_string(self, record: Dict, skip_fields: List[str] = None) -> str:
        """
        Build a canonical row string for embedding (concatenates key fields).
        
        Args:
            record: Record to convert to string
            skip_fields: Fields to skip (e.g., id, timestamps)
            
        Returns:
            Canonical row string representation
        """
        if skip_fields is None:
            skip_fields = ['id', 'record_id', 'updated_at', 'updated_by']
        
        parts = []
        for key, value in record.items():
            if key.lower() not in skip_fields:
                text = str(value).strip()
                if text and self._is_embedding_candidate(text):
                    parts.append(text)
        
        return " | ".join(parts)
    
    def _is_embedding_candidate(self, value) -> bool:
        """Return True only for meaningful textual values suitable for embeddings."""
        text = str(value).strip()
        if not text:
            return False
        if len(text) < 2:
            return False
        return any(ch.isalpha() for ch in text)
    
    def _precompute_master_row_embeddings(self, master1_data: List[Dict]) -> None:
        """
        Pre-compute and store embeddings for master rows in Chroma.
        Called once per analysis session (or cached across sessions).
        
        Args:
            master1_data: List of preferred master records
        """
        print(f"\n[Step 3 Setup] Pre-computing {len(master1_data)} master row embeddings...")
        self.master_row_lookup = {}

        count = 0
        for record in master1_data:
            row_str = self._build_row_string(record)
            if row_str:  # Only embed non-empty rows
                # Keep first seen record for a row string key
                if row_str not in self.master_row_lookup:
                    self.master_row_lookup[row_str] = record
                # This will check Chroma first, only generate if missing
                _ = self.embedding_service.get_embedding(row_str)
                count += 1
        
        print(f"✓ Master row embeddings ready ({self.embedding_service.get_cache_size()} total in Chroma)")
    
    def _embedding_match_with_row_similarity(
        self,
        given: Dict,
        master1_data: List[Dict],
        identifier_field: str,
        k: int = 3,
        threshold: float = 0.80
    ) -> Tuple[Optional[Dict], float]:
        """
        Step 3 (Optimized): Find best master match using row embedding similarity.
        Returns the best matching master record and its similarity score.
        
        Args:
            given: Record from given dataset
            master1_data: List of preferred master records
            identifier_field: Field used to identify records
            k: Number of top candidates to retrieve
            threshold: Minimum similarity for candidate
            
        Returns:
            Tuple of (best_matching_master_record, similarity_score)
        """
        # Build given row string
        given_row_str = self._build_row_string(given)
        if not given_row_str:
            return (None, 0.0)
        
        # Get given row embedding (generates if new, retrieves from Chroma if cached)
        given_embedding = self.embedding_service.get_embedding(given_row_str)
        if given_embedding == [0.0] * len(given_embedding):
            # Embedding generation failed
            return (None, 0.0)
        
        # Query Chroma for top-k similar master rows
        similar_results = self.embedding_service.query_similar(
            embedding=given_embedding,
            k=k,
            threshold=threshold
        )
        
        if not similar_results:
            return (None, 0.0)
        
        # Find best matching master record from candidates
        best_match = None
        best_similarity = 0.0
        
        for master_row_str, similarity, metadata in similar_results:
            # Fast path: O(1) lookup from precomputed mapping
            master_record = self.master_row_lookup.get(master_row_str)

            # Fallback path: scan master rows if mapping key not found
            if master_record is None:
                for candidate_record in master1_data:
                    if self._build_row_string(candidate_record) == master_row_str:
                        master_record = candidate_record
                        break

            if master_record is not None and similarity > best_similarity:
                best_similarity = similarity
                best_match = master_record
        
        return (best_match, best_similarity)
    
    def _process_llm_batch(
        self,
        batch: List[Dict],
        identifier_field: str
    ) -> List[Dict]:
        """
        Step 4: Process uncertain records using LLM reasoning.
        
        Args:
            batch: List of record sets to analyze
            identifier_field: Field used to identify records
            
        Returns:
            List of anomalies found
        """
        self.stats['llm_analyzed'] += len(batch)
        
        anomalies = self.gemini_reasoner.analyze_records_batch(batch, identifier_field)
        
        return anomalies
    
    def get_statistics(self) -> Dict:
        """Get matching statistics from last analysis."""
        return self.stats.copy()
    
    def clear_cache(self):
        """Clear embedding cache."""
        self.embedding_service.clear_cache()
