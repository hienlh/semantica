"""
Legal NER Extractor for Vietnamese legal documents.

Extracts legal entities from Vietnamese legal text using multiple methods:
- LLM-based extraction (primary)
- Pattern-based extraction (fallback)
- Heuristic-based extraction (last resort)

Integrates with Semantica NERExtractor while adding legal domain specifics.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger

from .entity_types import (
    ABBREVIATION_TO_ENTITY_TYPE,
    ENTITY_EXTRACTION_PROMPT_VI,
    ENTITY_PATTERNS,
    LEGAL_ENTITY_TYPES,
    LegalEntityType,
)


@dataclass
class LegalEntity:
    """Extracted legal entity with provenance."""

    text: str
    entity_type: LegalEntityType
    confidence: float
    start_pos: int
    end_pos: int
    source_id: str  # Hierarchical ID from SQLite (e.g., "59-2020-QH14:d5:k1")
    metadata: Dict[str, Any] = field(default_factory=dict)


class LegalNERExtractor:
    """
    Extract legal entities from Vietnamese legal text.

    Uses pattern-based extraction with optional LLM enhancement.
    Designed for Vietnamese legal documents with abbreviation handling.

    Example:
        >>> extractor = LegalNERExtractor()
        >>> entities = extractor.extract(
        ...     "Công ty TNHH phải có vốn điều lệ tối thiểu 10 tỷ đồng",
        ...     source_id="59-2020-QH14:d10:k1"
        ... )
        >>> for e in entities:
        ...     print(f"{e.text} -> {e.entity_type.value}")
        Công ty TNHH -> ORGANIZATION
        vốn điều lệ -> LEGAL_TERM
        10 tỷ đồng -> MONETARY
    """

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        method: str = "pattern",
        confidence_threshold: float = 0.5,
        use_abbreviation_mapping: bool = True,
    ):
        """
        Initialize the Legal NER Extractor.

        Args:
            llm_provider: Optional LLM provider for LLM-based extraction
            method: Extraction method - "pattern", "llm", or "hybrid"
            confidence_threshold: Minimum confidence for extracted entities
            use_abbreviation_mapping: Use known abbreviation mappings
        """
        self.logger = get_logger("legal_ner_extractor")
        self.method = method
        self.llm_provider = llm_provider
        self.confidence_threshold = confidence_threshold
        self.use_abbreviation_mapping = use_abbreviation_mapping

        # Compile patterns for each entity type
        self._compiled_patterns: Dict[LegalEntityType, List[re.Pattern]] = {}
        for entity_type, patterns in ENTITY_PATTERNS.items():
            self._compiled_patterns[entity_type] = [
                re.compile(p, re.IGNORECASE | re.UNICODE)
                for p in patterns
            ]

        # Try to import Semantica NERExtractor for fallback
        self._semantica_ner = None
        if method in ("llm", "hybrid") and llm_provider:
            try:
                from ..semantic_extract import NERExtractor
                self._semantica_ner = NERExtractor(
                    method="llm",
                    entity_types=LEGAL_ENTITY_TYPES,
                    provider=getattr(llm_provider, "provider", "openai"),
                    llm_model=getattr(llm_provider, "model", "gpt-4"),
                )
            except ImportError:
                self.logger.warning(
                    "Could not import Semantica NERExtractor, "
                    "falling back to pattern-based extraction"
                )

    def extract(
        self,
        text: str,
        source_id: str,
        entity_types: Optional[List[LegalEntityType]] = None,
    ) -> List[LegalEntity]:
        """
        Extract legal entities from text.

        Args:
            text: Legal text content
            source_id: Hierarchical ID (e.g., "59-2020-QH14:d10:k1")
            entity_types: Optional filter for specific entity types

        Returns:
            List of LegalEntity objects with provenance
        """
        if not text or not text.strip():
            return []

        entities: List[LegalEntity] = []

        # Method selection
        if self.method == "llm" and self._semantica_ner:
            entities = self._extract_llm(text, source_id, entity_types)
        elif self.method == "hybrid" and self._semantica_ner:
            # Combine LLM and pattern results
            llm_entities = self._extract_llm(text, source_id, entity_types)
            pattern_entities = self._extract_pattern(text, source_id, entity_types)
            entities = self._merge_entities(llm_entities, pattern_entities)
        else:
            # Pattern-based extraction
            entities = self._extract_pattern(text, source_id, entity_types)

        # Filter by confidence threshold
        entities = [e for e in entities if e.confidence >= self.confidence_threshold]

        # Deduplicate overlapping entities
        entities = self._deduplicate_entities(entities)

        return entities

    def _extract_pattern(
        self,
        text: str,
        source_id: str,
        entity_types: Optional[List[LegalEntityType]] = None,
    ) -> List[LegalEntity]:
        """Extract entities using regex patterns."""
        entities: List[LegalEntity] = []
        types_to_extract = entity_types or list(LegalEntityType)

        for entity_type in types_to_extract:
            patterns = self._compiled_patterns.get(entity_type, [])
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity_text = match.group(1) if match.groups() else match.group(0)
                    entity_text = entity_text.strip()

                    if len(entity_text) < 2:
                        continue

                    entity = LegalEntity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=0.8,  # Pattern match confidence
                        start_pos=match.start(),
                        end_pos=match.end(),
                        source_id=source_id,
                        metadata={
                            "extraction_method": "pattern",
                            "pattern": pattern.pattern[:50],
                        },
                    )
                    entities.append(entity)

        # Also extract known abbreviations
        if self.use_abbreviation_mapping:
            for abbrev, entity_type in ABBREVIATION_TO_ENTITY_TYPE.items():
                if entity_types and entity_type not in entity_types:
                    continue

                # Find all occurrences of the abbreviation
                pattern = re.compile(r"\b" + re.escape(abbrev) + r"\b")
                for match in pattern.finditer(text):
                    entity = LegalEntity(
                        text=abbrev,
                        entity_type=entity_type,
                        confidence=0.95,  # High confidence for known abbreviations
                        start_pos=match.start(),
                        end_pos=match.end(),
                        source_id=source_id,
                        metadata={
                            "extraction_method": "abbreviation_mapping",
                            "is_abbreviation": True,
                        },
                    )
                    entities.append(entity)

        return entities

    def _extract_llm(
        self,
        text: str,
        source_id: str,
        entity_types: Optional[List[LegalEntityType]] = None,
    ) -> List[LegalEntity]:
        """Extract entities using LLM."""
        if not self._semantica_ner:
            return self._extract_pattern(text, source_id, entity_types)

        try:
            # Use Semantica NERExtractor with custom prompt
            prompt = ENTITY_EXTRACTION_PROMPT_VI.format(text=text)

            # Extract using Semantica
            raw_entities = self._semantica_ner.extract_entities(
                text,
                prompt=prompt,
            )

            # Convert to LegalEntity
            entities: List[LegalEntity] = []
            for e in raw_entities:
                try:
                    entity_type = LegalEntityType(e.label)
                except ValueError:
                    # Skip unknown entity types
                    continue

                if entity_types and entity_type not in entity_types:
                    continue

                entity = LegalEntity(
                    text=e.text,
                    entity_type=entity_type,
                    confidence=e.confidence,
                    start_pos=e.start_char,
                    end_pos=e.end_char,
                    source_id=source_id,
                    metadata={
                        "extraction_method": "llm",
                        **e.metadata,
                    },
                )
                entities.append(entity)

            return entities

        except Exception as e:
            self.logger.warning(f"LLM extraction failed: {e}, falling back to pattern")
            return self._extract_pattern(text, source_id, entity_types)

    def _merge_entities(
        self,
        llm_entities: List[LegalEntity],
        pattern_entities: List[LegalEntity],
    ) -> List[LegalEntity]:
        """Merge entities from LLM and pattern extraction."""
        # Start with LLM entities (higher priority)
        merged = list(llm_entities)
        llm_spans = {(e.start_pos, e.end_pos) for e in llm_entities}

        # Add pattern entities that don't overlap with LLM entities
        for pe in pattern_entities:
            overlaps = False
            for start, end in llm_spans:
                if not (pe.end_pos <= start or pe.start_pos >= end):
                    overlaps = True
                    break

            if not overlaps:
                merged.append(pe)

        return merged

    def _deduplicate_entities(
        self,
        entities: List[LegalEntity],
    ) -> List[LegalEntity]:
        """
        Remove overlapping entities, keeping highest confidence.

        For exact duplicates, merge metadata.
        For overlapping spans, keep the one with higher confidence.
        """
        if not entities:
            return []

        # Sort by start position, then by length (longer first)
        sorted_entities = sorted(
            entities,
            key=lambda e: (e.start_pos, -(e.end_pos - e.start_pos)),
        )

        deduped: List[LegalEntity] = []
        for entity in sorted_entities:
            # Check for overlaps with existing entities
            overlapping_idx = None
            for i, existing in enumerate(deduped):
                if not (entity.end_pos <= existing.start_pos or
                        entity.start_pos >= existing.end_pos):
                    overlapping_idx = i
                    break

            if overlapping_idx is None:
                deduped.append(entity)
            else:
                # Keep higher confidence entity
                existing = deduped[overlapping_idx]
                if entity.confidence > existing.confidence:
                    deduped[overlapping_idx] = entity
                elif (entity.confidence == existing.confidence and
                      entity.text == existing.text):
                    # Merge metadata for exact matches
                    existing.metadata.update(entity.metadata)

        return deduped

    def extract_batch(
        self,
        items: List[Dict[str, str]],
        entity_types: Optional[List[LegalEntityType]] = None,
    ) -> Dict[str, List[LegalEntity]]:
        """
        Extract entities from multiple texts.

        Args:
            items: List of {"text": ..., "source_id": ...}
            entity_types: Optional filter for specific entity types

        Returns:
            Dict mapping source_id → entities
        """
        results: Dict[str, List[LegalEntity]] = {}
        for item in items:
            text = item.get("text", "")
            source_id = item.get("source_id", "unknown")
            entities = self.extract(text, source_id, entity_types)
            results[source_id] = entities
        return results
