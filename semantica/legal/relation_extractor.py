"""
Legal Relation Extractor for Vietnamese legal documents.

Extracts semantic relations between legal entities using multiple methods:
- Pattern-based extraction (primary)
- LLM-based extraction (optional)
- Cross-reference integration (Phase 03)

Designed for Vietnamese legal documents with support for:
- Prerequisite/dependency relations
- Penalty relations
- Scope/applicability relations
- Definition relations
- Cross-references
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging import get_logger

from .ner_extractor import LegalEntity
from .relation_types import (
    INVERSE_RELATIONS,
    LEGAL_RELATION_TYPES,
    LegalRelationType,
    RELATION_EXTRACTION_PROMPT_VI,
    RELATION_PATTERNS,
)


@dataclass
class LegalRelation:
    """Extracted relation between legal entities."""

    subject: LegalEntity
    predicate: LegalRelationType
    object: LegalEntity
    confidence: float
    source_id: str  # Hierarchical ID (e.g., "59-2020-QH14:d5:k1")
    context: str = ""  # Surrounding text for context
    metadata: Dict[str, Any] = field(default_factory=dict)


class LegalRelationExtractor:
    """
    Extract legal relations from Vietnamese legal text.

    Uses pattern-based extraction with optional LLM enhancement.
    Integrates with Phase 03 cross-reference detection for REFERENCES relations.

    Example:
        >>> entities = [entity1, entity2, ...]  # From LegalNERExtractor
        >>> extractor = LegalRelationExtractor()
        >>> relations = extractor.extract(
        ...     text="Nếu có đủ điều kiện tại Điều 5 thì được cấp phép kinh doanh",
        ...     entities=entities,
        ...     source_id="59-2020-QH14:d10:k1"
        ... )
        >>> for r in relations:
        ...     print(f"{r.subject.text} --{r.predicate.value}--> {r.object.text}")
    """

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        method: str = "pattern",
        confidence_threshold: float = 0.5,
        bidirectional: bool = False,
        max_context_window: int = 100,
    ):
        """
        Initialize the Legal Relation Extractor.

        Args:
            llm_provider: Optional LLM provider for LLM-based extraction
            method: Extraction method - "pattern", "llm", or "hybrid"
            confidence_threshold: Minimum confidence for extracted relations
            bidirectional: Extract inverse relations
            max_context_window: Characters around match for context
        """
        self.logger = get_logger("legal_relation_extractor")
        self.method = method
        self.llm_provider = llm_provider
        self.confidence_threshold = confidence_threshold
        self.bidirectional = bidirectional
        self.max_context_window = max_context_window

        # Compile patterns for each relation type
        self._compiled_patterns: Dict[LegalRelationType, List[re.Pattern]] = {}
        for rel_type, patterns in RELATION_PATTERNS.items():
            self._compiled_patterns[rel_type] = [
                re.compile(p, re.IGNORECASE | re.UNICODE | re.MULTILINE)
                for p in patterns
            ]

        # Try to import Semantica RelationExtractor for LLM fallback
        self._semantica_rel = None
        if method in ("llm", "hybrid") and llm_provider:
            try:
                from ..semantic_extract import RelationExtractor
                self._semantica_rel = RelationExtractor(
                    method="llm",
                    relation_types=LEGAL_RELATION_TYPES,
                    provider=getattr(llm_provider, "provider", "openai"),
                    llm_model=getattr(llm_provider, "model", "gpt-4"),
                )
            except ImportError:
                self.logger.warning(
                    "Could not import Semantica RelationExtractor, "
                    "falling back to pattern-based extraction"
                )

    def extract(
        self,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
        relation_types: Optional[List[LegalRelationType]] = None,
    ) -> List[LegalRelation]:
        """
        Extract legal relations from text.

        Args:
            text: Legal text content
            entities: Pre-extracted entities from LegalNERExtractor
            source_id: Hierarchical ID (e.g., "59-2020-QH14:d10:k1")
            relation_types: Optional filter for specific relation types

        Returns:
            List of LegalRelation objects
        """
        if not text or not text.strip() or not entities:
            return []

        relations: List[LegalRelation] = []

        # Method selection
        if self.method == "llm" and self._semantica_rel:
            relations = self._extract_llm(text, entities, source_id, relation_types)
        elif self.method == "hybrid" and self._semantica_rel:
            llm_relations = self._extract_llm(text, entities, source_id, relation_types)
            pattern_relations = self._extract_pattern(
                text, entities, source_id, relation_types
            )
            relations = self._merge_relations(llm_relations, pattern_relations)
        else:
            relations = self._extract_pattern(text, entities, source_id, relation_types)

        # Add bidirectional relations if enabled
        if self.bidirectional:
            inverse_relations = self._create_inverse_relations(relations)
            relations.extend(inverse_relations)

        # Filter by confidence threshold
        relations = [r for r in relations if r.confidence >= self.confidence_threshold]

        # Deduplicate relations
        relations = self._deduplicate_relations(relations)

        return relations

    def _extract_pattern(
        self,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
        relation_types: Optional[List[LegalRelationType]] = None,
    ) -> List[LegalRelation]:
        """Extract relations using regex patterns."""
        relations: List[LegalRelation] = []
        types_to_extract = relation_types or list(LegalRelationType)

        # Build entity index for quick lookup
        entity_by_pos = {(e.start_pos, e.end_pos): e for e in entities}
        entity_list = sorted(entities, key=lambda e: e.start_pos)

        for rel_type in types_to_extract:
            patterns = self._compiled_patterns.get(rel_type, [])
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Try to link matched groups to entities
                    relation = self._link_pattern_to_entities(
                        match, rel_type, text, entity_list, source_id, pattern.pattern
                    )
                    if relation:
                        relations.append(relation)

        # Also extract co-occurrence based relations
        cooc_relations = self._extract_cooccurrence_relations(
            text, entities, source_id, types_to_extract
        )
        relations.extend(cooc_relations)

        return relations

    def _link_pattern_to_entities(
        self,
        match: re.Match,
        rel_type: LegalRelationType,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
        pattern_str: str,
    ) -> Optional[LegalRelation]:
        """Link a pattern match to the nearest entities."""
        match_start = match.start()
        match_end = match.end()
        matched_text = match.group(0)

        # Find entities that overlap or are near the match
        nearby_entities = []
        for entity in entities:
            # Check if entity is within or near the match
            distance = min(
                abs(entity.start_pos - match_start),
                abs(entity.end_pos - match_end),
            )
            if distance < self.max_context_window:
                nearby_entities.append((distance, entity))

        # Sort by distance
        nearby_entities.sort(key=lambda x: x[0])

        if len(nearby_entities) < 2:
            # Not enough entities to form a relation
            # Create placeholder entities from matched groups if available
            if match.groups() and len(match.groups()) >= 2:
                # Use captured groups as entity texts
                return self._create_relation_from_groups(
                    match, rel_type, text, source_id
                )
            return None

        # Use first two nearest entities as subject and object
        subject = nearby_entities[0][1]
        obj = nearby_entities[1][1]

        # Get context around the match
        context_start = max(0, match_start - 50)
        context_end = min(len(text), match_end + 50)
        context = text[context_start:context_end].strip()

        return LegalRelation(
            subject=subject,
            predicate=rel_type,
            object=obj,
            confidence=0.7,  # Pattern match confidence
            source_id=source_id,
            context=context,
            metadata={
                "extraction_method": "pattern",
                "pattern": pattern_str[:50],
                "matched_text": matched_text[:100],
            },
        )

    def _create_relation_from_groups(
        self,
        match: re.Match,
        rel_type: LegalRelationType,
        text: str,
        source_id: str,
    ) -> Optional[LegalRelation]:
        """Create relation from regex capture groups."""
        from .entity_types import LegalEntityType

        groups = match.groups()
        if len(groups) < 2:
            return None

        # Create pseudo-entities from captured groups
        subject_text = groups[0].strip() if groups[0] else ""
        object_text = groups[1].strip() if groups[1] else ""

        if not subject_text or not object_text:
            return None

        # Determine entity types based on relation type
        subject_type = self._infer_entity_type_for_relation(rel_type, is_subject=True)
        object_type = self._infer_entity_type_for_relation(rel_type, is_subject=False)

        subject = LegalEntity(
            text=subject_text,
            entity_type=subject_type,
            confidence=0.6,
            start_pos=match.start(1) if match.lastindex >= 1 else match.start(),
            end_pos=match.end(1) if match.lastindex >= 1 else match.end(),
            source_id=source_id,
            metadata={"from_relation_extraction": True},
        )

        obj = LegalEntity(
            text=object_text,
            entity_type=object_type,
            confidence=0.6,
            start_pos=match.start(2) if match.lastindex >= 2 else match.start(),
            end_pos=match.end(2) if match.lastindex >= 2 else match.end(),
            source_id=source_id,
            metadata={"from_relation_extraction": True},
        )

        # Get context
        context_start = max(0, match.start() - 30)
        context_end = min(len(text), match.end() + 30)
        context = text[context_start:context_end].strip()

        return LegalRelation(
            subject=subject,
            predicate=rel_type,
            object=obj,
            confidence=0.65,
            source_id=source_id,
            context=context,
            metadata={
                "extraction_method": "pattern_groups",
                "matched_text": match.group(0)[:100],
            },
        )

    def _infer_entity_type_for_relation(
        self,
        rel_type: LegalRelationType,
        is_subject: bool,
    ):
        """Infer entity type based on relation type and position."""
        from .entity_types import LegalEntityType

        # Define typical entity types for relations
        type_map = {
            LegalRelationType.REQUIRES: (
                LegalEntityType.ACTION,
                LegalEntityType.CONDITION,
            ),
            LegalRelationType.HAS_PENALTY: (
                LegalEntityType.ACTION,
                LegalEntityType.PENALTY,
            ),
            LegalRelationType.APPLIES_TO: (
                LegalEntityType.LEGAL_TERM,
                LegalEntityType.ORGANIZATION,
            ),
            LegalRelationType.DEFINED_AS: (
                LegalEntityType.LEGAL_TERM,
                LegalEntityType.LEGAL_TERM,
            ),
            LegalRelationType.AUTHORIZED_BY: (
                LegalEntityType.ACTION,
                LegalEntityType.PERSON_ROLE,
            ),
            LegalRelationType.PERFORMED_BY: (
                LegalEntityType.ACTION,
                LegalEntityType.PERSON_ROLE,
            ),
        }

        default = (LegalEntityType.LEGAL_TERM, LegalEntityType.LEGAL_TERM)
        subject_type, object_type = type_map.get(rel_type, default)
        return subject_type if is_subject else object_type

    def _extract_cooccurrence_relations(
        self,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
        relation_types: List[LegalRelationType],
    ) -> List[LegalRelation]:
        """Extract relations based on entity co-occurrence patterns."""
        from .entity_types import LegalEntityType

        relations: List[LegalRelation] = []

        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_pos)

        # Look for entity pairs that commonly co-occur
        for i, e1 in enumerate(sorted_entities):
            for j, e2 in enumerate(sorted_entities[i + 1 :], i + 1):
                distance = e2.start_pos - e1.end_pos

                # Skip if too far apart
                if distance > self.max_context_window:
                    break

                # Get text between entities
                between_text = text[e1.end_pos : e2.start_pos].lower()

                # Check for relation indicators
                relation = self._check_cooccurrence_relation(
                    e1, e2, between_text, text, source_id, relation_types
                )
                if relation:
                    relations.append(relation)

        return relations

    def _check_cooccurrence_relation(
        self,
        e1: LegalEntity,
        e2: LegalEntity,
        between_text: str,
        full_text: str,
        source_id: str,
        relation_types: List[LegalRelationType],
    ) -> Optional[LegalRelation]:
        """Check if two entities have a relation based on text between them."""
        from .entity_types import LegalEntityType

        # Relation indicators (Vietnamese)
        indicators = {
            LegalRelationType.REQUIRES: [
                "phải có", "cần có", "yêu cầu", "bắt buộc",
            ],
            LegalRelationType.APPLIES_TO: [
                "áp dụng cho", "áp dụng đối với", "đối với",
            ],
            LegalRelationType.DEFINED_AS: [
                "là", "được định nghĩa", "có nghĩa là",
            ],
            LegalRelationType.AUTHORIZED_BY: [
                "được ủy quyền", "do", "bởi",
            ],
            LegalRelationType.PERFORMED_BY: [
                "do", "bởi", "thực hiện bởi",
            ],
            LegalRelationType.HAS_PENALTY: [
                "bị phạt", "bị xử phạt", "bị đình chỉ",
            ],
        }

        for rel_type in relation_types:
            indicator_list = indicators.get(rel_type, [])
            for indicator in indicator_list:
                if indicator in between_text:
                    # Get context
                    context_start = max(0, e1.start_pos - 20)
                    context_end = min(len(full_text), e2.end_pos + 20)
                    context = full_text[context_start:context_end].strip()

                    return LegalRelation(
                        subject=e1,
                        predicate=rel_type,
                        object=e2,
                        confidence=0.6,
                        source_id=source_id,
                        context=context,
                        metadata={
                            "extraction_method": "cooccurrence",
                            "indicator": indicator,
                        },
                    )

        return None

    def _extract_llm(
        self,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
        relation_types: Optional[List[LegalRelationType]] = None,
    ) -> List[LegalRelation]:
        """Extract relations using LLM."""
        if not self._semantica_rel:
            return self._extract_pattern(text, entities, source_id, relation_types)

        try:
            # Format entities for prompt
            entities_str = "\n".join([
                f"- {e.text} ({e.entity_type.value})"
                for e in entities
            ])

            prompt = RELATION_EXTRACTION_PROMPT_VI.format(
                text=text,
                entities=entities_str,
            )

            # Convert LegalEntity to Semantica Entity format
            from ..semantic_extract.ner_extractor import Entity
            semantica_entities = [
                Entity(
                    text=e.text,
                    label=e.entity_type.value,
                    start_char=e.start_pos,
                    end_char=e.end_pos,
                    confidence=e.confidence,
                )
                for e in entities
            ]

            # Extract using Semantica
            raw_relations = self._semantica_rel.extract_relations(
                text,
                entities=semantica_entities,
            )

            # Convert to LegalRelation
            relations: List[LegalRelation] = []
            entity_by_text = {e.text: e for e in entities}

            for r in raw_relations:
                try:
                    rel_type = LegalRelationType(r.predicate)
                except ValueError:
                    continue

                if relation_types and rel_type not in relation_types:
                    continue

                # Find matching entities
                subject = entity_by_text.get(r.subject.text)
                obj = entity_by_text.get(r.object.text)

                if not subject or not obj:
                    continue

                relation = LegalRelation(
                    subject=subject,
                    predicate=rel_type,
                    object=obj,
                    confidence=r.confidence,
                    source_id=source_id,
                    context=r.context,
                    metadata={
                        "extraction_method": "llm",
                        **r.metadata,
                    },
                )
                relations.append(relation)

            return relations

        except Exception as e:
            self.logger.warning(f"LLM extraction failed: {e}, falling back to pattern")
            return self._extract_pattern(text, entities, source_id, relation_types)

    def _create_inverse_relations(
        self,
        relations: List[LegalRelation],
    ) -> List[LegalRelation]:
        """Create inverse relations for bidirectional extraction."""
        inverse_relations: List[LegalRelation] = []

        for rel in relations:
            inverse_type = INVERSE_RELATIONS.get(rel.predicate)
            if inverse_type:
                inverse = LegalRelation(
                    subject=rel.object,
                    predicate=inverse_type,
                    object=rel.subject,
                    confidence=rel.confidence * 0.9,  # Slightly lower confidence
                    source_id=rel.source_id,
                    context=rel.context,
                    metadata={
                        **rel.metadata,
                        "is_inverse": True,
                        "original_predicate": rel.predicate.value,
                    },
                )
                inverse_relations.append(inverse)

        return inverse_relations

    def _merge_relations(
        self,
        llm_relations: List[LegalRelation],
        pattern_relations: List[LegalRelation],
    ) -> List[LegalRelation]:
        """Merge relations from LLM and pattern extraction."""
        merged = list(llm_relations)

        # Create a set of existing relation signatures
        existing = {
            (r.subject.text, r.predicate, r.object.text)
            for r in llm_relations
        }

        for pr in pattern_relations:
            sig = (pr.subject.text, pr.predicate, pr.object.text)
            if sig not in existing:
                merged.append(pr)

        return merged

    def _deduplicate_relations(
        self,
        relations: List[LegalRelation],
    ) -> List[LegalRelation]:
        """Remove duplicate relations, keeping highest confidence."""
        seen: Dict[Tuple[str, str, str], LegalRelation] = {}

        for rel in relations:
            key = (rel.subject.text, rel.predicate.value, rel.object.text)
            if key not in seen or rel.confidence > seen[key].confidence:
                seen[key] = rel

        return list(seen.values())

    def extract_batch(
        self,
        items: List[Dict],
        relation_types: Optional[List[LegalRelationType]] = None,
    ) -> Dict[str, List[LegalRelation]]:
        """
        Extract relations from multiple texts.

        Args:
            items: List of {"text": ..., "entities": [...], "source_id": ...}
            relation_types: Optional filter for specific relation types

        Returns:
            Dict mapping source_id → relations
        """
        results: Dict[str, List[LegalRelation]] = {}
        for item in items:
            text = item.get("text", "")
            entities = item.get("entities", [])
            source_id = item.get("source_id", "unknown")
            relations = self.extract(text, entities, source_id, relation_types)
            results[source_id] = relations
        return results
