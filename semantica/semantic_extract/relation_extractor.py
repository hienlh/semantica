"""
Relation Extraction Module

This module provides comprehensive relationship detection and extraction
between entities in text documents using multiple extraction methods, from
pattern matching to advanced LLM-based extraction.

Supported Methods:
    - "pattern": Pattern-based extraction using custom regex patterns (default)
    - "regex": Advanced regex-based relation extraction
    - "cooccurrence": Co-occurrence based relation detection (proximity-based)
    - "dependency": Dependency parsing-based extraction using spaCy
    - "huggingface": Custom HuggingFace relation extraction models
    - "llm": LLM-based relation extraction using various providers

Algorithms Used:
    - Pattern Matching: Regular expression and string pattern matching
    - Co-occurrence Analysis: Proximity-based entity co-occurrence detection
    - Dependency Parsing: Transition-based or graph-based dependency parsing
    - Sequence Classification: Transformer-based relation classification models
    - Large Language Models: GPT, Claude, Gemini for relation extraction
    - Context Window Analysis: Sliding window and context extraction algorithms
    - Weighted Confidence Scoring:
        * Formula: Score = (0.5 * Method_Confidence) + (0.5 * Type_Similarity_Score)
        * Method_Confidence: Confidence score from the extraction algorithm
        * Type_Similarity_Score: Semantic match with user-provided relation types
    - Hybrid Similarity Matching: Exact -> Synonym -> Substring -> Semantic Embedding
    - Last Resort Fallback: Adjacency-based heuristic when all other methods fail

Key Features:
    - Custom relation patterns: Pass your own regex patterns for any language
    - Custom fallback predicate: Configure the fallback relation type
    - Multiple extraction methods (pattern, regex, cooccurrence, dependency, etc.)
    - Fallback chain support: Try methods in order until one succeeds
    - Configurable fallbacks: Disable co-occurrence or last resort fallbacks
    - Robust Fallbacks: Prevents empty results via Primary -> Pattern -> Last Resort
    - Relation classification and grouping
    - Relation validation and consistency checking
    - Context extraction for each relation
    - Confidence scoring and filtering

Main Classes:
    - RelationExtractor: Main relation extractor with method selection
    - Relation: Relation representation dataclass

Example Usage:
    >>> from semantica.semantic_extract import RelationExtractor
    >>>
    >>> # Using default English patterns
    >>> extractor = RelationExtractor(method="pattern")
    >>> relations = extractor.extract_relations("Apple was founded by Steve Jobs.", entities)
    >>>
    >>> # Using custom Vietnamese patterns
    >>> VI_PATTERNS = {
    ...     "YÊU_CẦU": [r"(.+?)\\s+(?:phải có|cần có)\\s+(.+)"],
    ...     "ĐỊNH_NGHĨA_LÀ": [r"(.+?)\\s+(?:là|được định nghĩa là)\\s+(.+)"],
    ... }
    >>> extractor = RelationExtractor(
    ...     method="pattern",
    ...     relation_patterns=VI_PATTERNS,
    ...     fallback_predicate="LIÊN_QUAN",
    ... )
    >>> relations = extractor.extract_relations("Công ty phải có ít nhất 2 thành viên.", entities)
    >>>
    >>> # LLM-based extraction with custom fallback, disable noisy co-occurrence
    >>> extractor = RelationExtractor(
    ...     method="llm",
    ...     provider="gemini",
    ...     llm_model="gemini-2.0-flash",
    ...     fallback_predicate="LIÊN_QUAN",
    ...     disable_cooccurrence_fallback=True,
    ...     disable_last_resort_fallback=True,
    ... )
    >>> relations = extractor.extract_relations(text, entities)
    >>>
    >>> # Using dependency parsing
    >>> extractor = RelationExtractor(method="dependency", model="en_core_web_sm")
    >>> relations = extractor.extract_relations("Apple was founded by Steve Jobs.", entities)
    >>>
    >>> # Using fallback chain
    >>> extractor = RelationExtractor(method=["llm", "dependency", "pattern"])
    >>> relations = extractor.extract_relations("Apple was founded by Steve Jobs.", entities)

Author: Semantica Contributors
License: MIT
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .ner_extractor import Entity


@dataclass
class Relation:
    """Relation representation."""

    subject: Entity
    predicate: str
    object: Entity
    confidence: float = 1.0
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RelationExtractor:
    """Relation extractor for entity relationships."""

    # Default English relation patterns (used when no custom patterns provided)
    DEFAULT_RELATION_PATTERNS = {
        "founded_by": [
            r"(?P<subject>[\w\.\s]+?)\s+(?:was\s+)?founded\s+by\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
            r"(?P<object>[\w\.]+(?:\s+[\w\.]+)*)\s+founded\s+(?P<subject>[\w\.]+(?:\s+[\w\.]+)*)",
        ],
        "located_in": [
            r"(?P<subject>[\w\.\s]+?)\s+is\s+located\s+in\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
            r"(?P<subject>[\w\.\s]+?)\s+in\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
        ],
        "works_for": [
            r"(?P<subject>[\w\.\s]+?)\s+works?\s+for\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
            r"(?P<subject>[\w\.\s]+?)\s+is\s+an?\s+employee\s+of\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
        ],
        "born_in": [
            r"(?P<subject>[\w\.\s]+?)\s+was\s+born\s+in\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
            r"(?P<subject>[\w\.\s]+?)\s+born\s+in\s+(?P<object>[\w\.]+(?:\s+[\w\.]+)*)",
        ],
    }

    # Default fallback predicate
    DEFAULT_FALLBACK_PREDICATE = "related_to"

    def __init__(
        self,
        method: Union[str, List[str]] = "pattern",
        relation_types: Optional[List[str]] = None,
        relation_patterns: Optional[Dict[str, List[str]]] = None,
        fallback_predicate: Optional[str] = None,
        bidirectional: bool = False,
        confidence_threshold: float = 0.6,
        max_distance: int = 50,
        **config
    ):
        """
        Initialize relation extractor.

        Args:
            method: Extraction method(s). Can be:
                - "pattern": Pattern-based extraction (default)
                - "regex": Regex-based extraction
                - "cooccurrence": Co-occurrence based
                - "dependency": Dependency parsing based
                - "huggingface": HuggingFace model
                - "llm": LLM-based extraction
                - List of methods for fallback chain
            relation_types: Specific relation types to extract (e.g., ["founded", "works_at"])
            relation_patterns: Custom regex patterns for pattern-based extraction.
                Format: {"RELATION_TYPE": [r"pattern1", r"pattern2", ...]}
                Each pattern must have named groups "subject" and "object".
                If None, uses DEFAULT_RELATION_PATTERNS.
            fallback_predicate: Predicate to use for co-occurrence and last resort fallback.
                Default: "related_to". For Vietnamese, use "LIÊN_QUAN".
            bidirectional: Whether to extract bidirectional relations
            confidence_threshold: Minimum confidence score (0.0-1.0)
            max_distance: Maximum token distance between entities
            **config: Additional configuration options:
                - model: Model name (for dependency/HuggingFace methods)
                - huggingface_model: HuggingFace model name
                - provider: LLM provider (for LLM method)
                - llm_model: LLM model name
                - device: Device for HuggingFace models
                - validate: Enable validation (default: False)
                - disable_cooccurrence_fallback: Disable co-occurrence fallback (default: False)
                - disable_last_resort_fallback: Disable last resort fallback (default: False)
        """
        self.logger = get_logger("relation_extractor")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        # Store parameters
        self.relation_types = relation_types
        self.bidirectional = bidirectional
        self.confidence_threshold = confidence_threshold
        self.max_distance = max_distance
        self.verbose = config.get("verbose", False)

        # Fallback configuration
        self.disable_cooccurrence_fallback = config.get("disable_cooccurrence_fallback", False)
        self.disable_last_resort_fallback = config.get("disable_last_resort_fallback", False)

        # Method configuration
        self.method = method if isinstance(method, list) else [method]
        self.min_confidence = config.get("min_confidence", confidence_threshold)
        self.validate = config.get("validate", False)

        # Use custom patterns if provided, otherwise use defaults
        self.relation_patterns = (
            relation_patterns.copy() if relation_patterns
            else self.DEFAULT_RELATION_PATTERNS.copy()
        )

        # Use custom fallback predicate if provided, otherwise use default
        self._fallback_predicate = fallback_predicate or self.DEFAULT_FALLBACK_PREDICATE


    def extract(
        self,
        text: Union[str, List[Dict[str, Any]], List[str]],
        entities: Union[List[Entity], List[List[Entity]]],
        pipeline_id: Optional[str] = None,
        **kwargs
    ) -> Union[List[Relation], List[List[Relation]]]:
        """
        Alias for extract_relations.
        Handles both single string/entity-list and list of documents/entity-lists.
        
        Args:
            text: Input text or list of documents
            entities: List of entities or list of list of entities
            pipeline_id: Optional pipeline ID for progress tracking
            **kwargs: Extraction options
            
        Returns:
            Union[List[Relation], List[List[Relation]]]: Extracted relations
        """
        if isinstance(text, list) and isinstance(entities, list):
            # Handle batch extraction with progress tracking
            tracking_id = self.progress_tracker.start_tracking(
                module="semantic_extract",
                submodule="RelationExtractor",
                message=f"Batch extracting relations from {len(text)} documents",
                pipeline_id=pipeline_id,
            )
            
            try:
                # Ensure lists are same length
                min_len = min(len(text), len(entities))
                results = [None] * min_len
                total_relations_count = 0
                processed_count = 0
                
                # Update more frequently: every 1% or at least every 10 items, but always update for small datasets
                if min_len <= 10:
                    update_interval = 1  # Update every item for small datasets
                else:
                    update_interval = max(1, min(10, min_len // 100))
                
                # Initial progress update - ALWAYS show this
                self.progress_tracker.update_progress(
                    tracking_id,
                    processed=0,
                    total=min_len,
                    message=f"Starting batch extraction... 0/{min_len}"
                )
                
                # Determine max_workers
                max_workers = kwargs.get("max_workers", self.config.get("max_workers", 1))

                def process_item(i, doc_item, ent_item):
                    try:
                        doc_text = ""
                        if isinstance(doc_item, dict) and "content" in doc_item:
                            doc_text = doc_item["content"]
                        elif isinstance(doc_item, str):
                            doc_text = doc_item
                        else:
                            doc_text = str(doc_item)
                        
                        # Ensure ent_item is a list of entities
                        if not isinstance(ent_item, list):
                            ent_item = [] # Should not happen if entities is List[List[Entity]]
                        
                        current_relations = self.extract_relations(doc_text, ent_item, **kwargs)
                        
                        # Add provenance metadata
                        for rel in current_relations:
                            if rel.metadata is None:
                                rel.metadata = {}
                            rel.metadata["batch_index"] = i
                            if isinstance(doc_item, dict) and "id" in doc_item:
                                rel.metadata["document_id"] = doc_item["id"]
                        
                        return i, current_relations
                    except Exception as e:
                        self.logger.warning(f"Failed to process item {i}: {e}")
                        return i, []

                if max_workers > 1:
                    import concurrent.futures
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit tasks
                        future_to_idx = {
                            executor.submit(process_item, i, text[i], entities[i]): i
                            for i in range(min_len)
                        }
                        
                        for future in concurrent.futures.as_completed(future_to_idx):
                            i, relations = future.result()
                            results[i] = relations
                            total_relations_count += len(relations)
                            processed_count += 1
                            
                            should_update = (
                                processed_count % update_interval == 0 or 
                                processed_count == min_len or 
                                processed_count == 1 or
                                min_len <= 10
                            )
                            if should_update:
                                remaining = min_len - processed_count
                                self.progress_tracker.update_progress(
                                    tracking_id,
                                    processed=processed_count,
                                    total=min_len,
                                    message=f"Processing documents... {processed_count}/{min_len} (remaining: {remaining}) - Extracted {total_relations_count} relations so far"
                                )
                else:
                    # Sequential processing
                    for i in range(min_len):
                        _, relations = process_item(i, text[i], entities[i])
                        results[i] = relations
                        total_relations_count += len(relations)
                        processed_count += 1
                        
                        should_update = (
                            processed_count % update_interval == 0 or 
                            processed_count == min_len or 
                            processed_count == 1 or
                            min_len <= 10
                        )
                        if should_update:
                            remaining = min_len - processed_count
                            self.progress_tracker.update_progress(
                                tracking_id,
                                processed=processed_count,
                                total=min_len,
                                message=f"Processing documents... {processed_count}/{min_len} (remaining: {remaining}) - Extracted {total_relations_count} relations so far"
                            )
                
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Batch extraction completed. Processed {len(results)} documents, extracted {total_relations_count} relations.",
                )
                return results
            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                raise
        elif isinstance(text, str) and isinstance(entities, list):
             # Single text, single list of entities (standard case)
            return self.extract_relations(text, entities, **kwargs)
        else:
            # Fallback or invalid input combination
            return []

    def extract_relations(
        self, text: str, entities: List[Entity], **options
    ) -> List[Relation]:
        """
        Extract relations between entities.

        Args:
            text: Input text
            entities: List of extracted entities
            **options: Extraction options:
                - method: Override method (if not set in __init__)
                - min_confidence: Minimum confidence threshold
                - validate: Enable validation

        Returns:
            list: List of extracted relations
        """
        from .methods import get_relation_method, match_entity

        tracking_id = self.progress_tracker.start_tracking(
            module="semantic_extract",
            submodule="RelationExtractor",
            message=f"Extracting relations from {len(entities)} entities",
        )

        try:
            if not text or not entities:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message="No text or entities provided",
                )
                return []

            # Use method from options if provided, otherwise use instance method
            methods = options.get("method", self.method)
            if isinstance(methods, str):
                methods = [methods]

            min_confidence = options.get("min_confidence", self.min_confidence)
            validate = options.get("validate", self.validate)
            relation_types = options.get("relation_types", self.relation_types)

            # Merge config with options
            all_options = {**self.config, **options}

            # Try each method in order (fallback chain)
            all_relations = []
            for method_name in methods:
                try:
                    self.progress_tracker.update_tracking(
                        tracking_id,
                        message=f"Extracting relations using {method_name}...",
                    )
                    method_func = get_relation_method(method_name)

                    # Prepare method-specific options
                    method_options = all_options.copy()
                    
                    # Pass relation_types to all methods so they can use them (e.g. for similarity matching)
                    if relation_types:
                        method_options["relation_types"] = relation_types

                    if method_name == "huggingface":
                        method_options["model"] = all_options.get(
                            "huggingface_model", all_options.get("model")
                        )
                        method_options["device"] = all_options.get("device")
                    elif method_name == "llm":
                        method_options["provider"] = all_options.get(
                            "provider", "openai"
                        )
                        method_options["model"] = all_options.get(
                            "llm_model", all_options.get("model")
                        )
                        # Pass api_key if provided (needed for all providers)
                        if "api_key" in all_options:
                            method_options["api_key"] = all_options["api_key"]
                        elif "api_key" not in method_options:
                            # Try to get from environment as fallback
                            import os
                            provider = method_options.get("provider", "openai")
                            env_key = f"{provider.upper()}_API_KEY"
                            api_key = os.getenv(env_key)
                            if api_key:
                                method_options["api_key"] = api_key
                    elif method_name == "dependency":
                        method_options["model"] = all_options.get(
                            "model", "en_core_web_sm"
                        )

                    # Print progress if verbose mode is enabled (only for LLM method to avoid spam)
                    verbose_mode = self.verbose or options.get("verbose", False)
                    if verbose_mode and method_name == "llm":
                        import sys
                        print(f"    [RelationExtractor] Processing with {method_name}...", flush=True, file=sys.stdout)
                    
                    relations = method_func(text, entities, **method_options)
                    
                    # Print result count if verbose (only for LLM method)
                    if verbose_mode and method_name == "llm" and len(relations) > 0:
                        import sys
                        print(f"    [RelationExtractor] Extracted {len(relations)} relations", flush=True, file=sys.stdout)

                    # Apply weighted scoring if relation_types are provided
                    if relation_types:
                        try:
                            from .methods import calculate_weighted_confidence
                            for r in relations:
                                r.confidence = calculate_weighted_confidence(
                                    item_type=r.predicate,
                                    original_confidence=r.confidence,
                                    valid_types=relation_types,
                                    item_text=r.predicate # For relations, the predicate IS the text usually
                                )
                        except ImportError:
                            pass

                    # Filter by confidence
                    filtered = [r for r in relations if r.confidence >= min_confidence]

                    if filtered:
                        all_relations.append((method_name, filtered))

                        # If not using ensemble, return first successful result
                        if len(methods) == 1:
                            result = filtered
                            if validate:
                                result = self.validate_relations(result)
                            self.progress_tracker.stop_tracking(
                                tracking_id,
                                status="completed",
                                message=f"Extracted {len(result)} relations using {method_name}",
                            )
                            return result

                except Exception as e:
                    self.logger.warning(f"Method {method_name} failed: {e}")
                    continue

            # Use first successful method or combine
            if all_relations:
                relations = all_relations[0][1]  # Use first successful method
            else:
                # Fallback to pattern-based extraction if all models fail
                relations = self._extract_with_patterns(text, entities)
                
                # Last resort: if patterns also fail but we have entities, force some relations
                if not relations and entities and len(entities) >= 2:
                     relations = self._extract_last_resort_relations(text, entities)

            # Validate if enabled
            if validate:
                relations = self.validate_relations(relations)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Extracted {len(relations)} relations",
            )
            return relations

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _extract_last_resort_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """
        Last resort relation extraction based on simple adjacency.

        Uses language-appropriate fallback predicate:
        - Vietnamese: "LIÊN_QUAN"
        - English: "related_to"
        """
        # Skip if disabled
        if self.disable_last_resort_fallback:
            return []

        relations = []
        # Connect adjacent entities
        for i in range(len(entities) - 1):
            e1 = entities[i]
            e2 = entities[i+1]

            # Create a weak relation
            start_idx = min(e1.end_char, e2.start_char)
            end_idx = max(e1.end_char, e2.start_char)
            # Ensure context isn't too large or invalid
            if start_idx < 0: start_idx = 0
            if end_idx > len(text): end_idx = len(text)

            # Expand context a bit
            ctx_start = max(0, start_idx - 20)
            ctx_end = min(len(text), end_idx + 20)

            context = text[ctx_start:ctx_end]

            rel = Relation(
                subject=e1,
                predicate=self._fallback_predicate,
                object=e2,
                confidence=0.3,
                context=context,
                metadata={"extraction_method": "last_resort_adjacency"}
            )
            relations.append(rel)
        return relations

    def _extract_with_patterns(
        self, text: str, entities: List[Entity]
    ) -> List[Relation]:
        """
        Extract relations using pattern matching.

        Uses language-specific patterns (Vietnamese or English).
        Co-occurrence fallback can be disabled via config.
        """
        from .methods import match_entity
        relations = []

        # Check each relation pattern
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        # Safely extract subject and object
                        try:
                            subject_text = match.group("subject").strip()
                        except (IndexError, AttributeError):
                            subject_text = None

                        try:
                            object_text = match.group("object").strip()
                        except (IndexError, AttributeError):
                            object_text = None

                        if not subject_text or not object_text:
                            continue

                        subject_entity = match_entity(subject_text, entities)
                        object_entity = match_entity(object_text, entities)

                        if subject_entity and object_entity:
                            # Get context around the match
                            start = max(0, match.start() - 50)
                            end = min(len(text), match.end() + 50)
                            context = text[start:end]

                            relations.append(
                                Relation(
                                    subject=subject_entity,
                                    predicate=relation_type,
                                    object=object_entity,
                                    confidence=0.7,  # Pattern-based confidence
                                    context=context,
                                    metadata={
                                        "extraction_method": "pattern",
                                        "pattern": pattern,
                                    },
                                )
                            )
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern for {relation_type}: {e}")
                    continue

        # Co-occurrence based relations (entities close to each other)
        # Skip if disabled - co-occurrence creates many generic relations
        if not self.disable_cooccurrence_fallback:
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i + 1 :]:
                    # Check if entities are close in text
                    distance = abs(entity1.end_char - entity2.start_char)
                    if distance < 100:  # Within 100 characters
                        # Simple relation based on proximity
                        start = min(entity1.start_char, entity2.start_char)
                        end = max(entity1.end_char, entity2.end_char)
                        context = text[max(0, start - 30) : min(len(text), end + 30)]

                        relations.append(
                            Relation(
                                subject=entity1,
                                predicate=self._fallback_predicate,
                                object=entity2,
                                confidence=0.5,  # Lower confidence for co-occurrence
                                context=context,
                                metadata={
                                    "extraction_method": "co_occurrence",
                                    "distance": distance,
                                },
                            )
                        )

        return relations

    def classify_relations(
        self, relations: List[Relation]
    ) -> Dict[str, List[Relation]]:
        """
        Classify relations by type.

        Args:
            relations: List of relations

        Returns:
            dict: Relations grouped by predicate type
        """
        classified = {}
        for relation in relations:
            if relation.predicate not in classified:
                classified[relation.predicate] = []
            classified[relation.predicate].append(relation)

        return classified

    def validate_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        Validate relations for consistency.

        Args:
            relations: List of relations

        Returns:
            list: Validated relations
        """
        valid_relations = []

        for relation in relations:
            # Basic validation
            if not relation.subject or not relation.object:
                continue

            if not relation.predicate:
                continue

            # Check if subject and object are different
            if relation.subject.text == relation.object.text:
                continue

            valid_relations.append(relation)

        return valid_relations
