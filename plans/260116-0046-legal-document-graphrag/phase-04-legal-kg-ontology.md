# Phase 04: Legal Knowledge Graph & Ontology

## Context Links

- [Research: Semantica KG Pipeline](../reports/researcher-260117-1736-semantica-kg-ontology-pipeline.md)
- [Phase 01: Database](./phase-01-legal-document-database.md)
- [Phase 03: CrossRef Detection](./phase-03-legal-entity-extraction.md)
- [Phase 03.5: Abbreviation Extraction](./phase-03-5-legal-text-normalizer.md)
- [Main Plan](./plan.md)

## Overview

**REVISED APPROACH**: Feed legal text through full Semantica pipeline:
```
SQLite Data → NER → Relations → GraphBuilder → Ontology
```

This builds a semantic Knowledge Graph (not just structural), enabling:
- Multi-hop reasoning across articles
- Accurate citations with provenance
- Cross-reference navigation

## Progress (Updated 2026-01-18)

| Step | Component | Status | Notes |
|------|-----------|--------|-------|
| ~~0~~ | ~~Normalizer~~ | ✅ **Skip** | Scraper already handles (tvpl.py:415-422) |
| ~~0.5~~ | ~~Abbreviations~~ | ✅ **Done** | `abbreviation_extractor.py` (Phase 03.5) |
| 1 | Entity Types | 🔲 Pending | `entity_types.py` |
| 2 | Relation Types | 🔲 Pending | `relation_types.py` |
| 3 | NER Extractor | 🔲 Pending | `ner_extractor.py` |
| 4 | Relation Extractor | 🔲 Pending | `relation_extractor.py` |
| 5 | KG Builder | 🔲 Pending | `kg_builder.py` |
| 6 | Ontology Generator | 🔲 Pending | `ontology_generator.py` |
| 7 | KG Linker | 🔲 Pending | `kg_linker.py` |
| 8 | Pipeline | 🔲 Pending | `pipeline.py` |

## Key Decisions (Validated 2026-01-17)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Entity Types | Full extraction (all types) | Comprehensive QA chatbot |
| CrossRef | Multi-hop (KG edges + context expansion) | Best reasoning accuracy |
| Accuracy | Provenance + Confidence scoring | Trustworthy citations |
| Abbreviations | Keep original + dictionary mapping | LLM understands; preserves text |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Phase 04: Legal Semantica Pipeline                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ INPUT: Phase 01 SQLite + Phase 03 CrossRefs + Phase 03.5 Abbrevs    │   │
│  │ ├─ Article.content, Clause.text, Point.text                         │   │
│  │ ├─ CrossReferences (Phase 03)                                       │   │
│  │ └─ Abbreviations (Phase 03.5) - auto-detected full forms            │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: LegalNERExtractor (extends Semantica NERExtractor)          │   │
│  │ method="llm", entity_types=LEGAL_ENTITY_TYPES                       │   │
│  │                                                                      │   │
│  │ Entity Types:                                                        │   │
│  │ ├─ ORGANIZATION (doanh nghiệp, công ty, cơ quan)                    │   │
│  │ ├─ PERSON_ROLE (Giám đốc, thành viên HĐQT, TGĐ)                     │   │
│  │ ├─ LEGAL_TERM (vốn điều lệ, cổ phần, ĐHĐCĐ)                         │   │
│  │ ├─ MONETARY (10 triệu đồng, 50% vốn)                                │   │
│  │ ├─ DURATION (30 ngày, 06 tháng)                                     │   │
│  │ ├─ CONDITION (nếu, trường hợp, khi)                                 │   │
│  │ ├─ ACTION (thành lập, giải thể, đăng ký)                            │   │
│  │ └─ PENALTY (phạt tiền, đình chỉ)                                    │   │
│  │                                                                      │   │
│  │ Output: Entity[] with {text, type, confidence, source_id}           │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: LegalRelationExtractor (extends Semantica RelationExtractor)│   │
│  │ method="llm", relation_types=LEGAL_RELATION_TYPES                   │   │
│  │                                                                      │   │
│  │ Relation Types:                                                      │   │
│  │ ├─ REQUIRES (X requires Y)                                          │   │
│  │ ├─ HAS_PENALTY (violation has penalty)                              │   │
│  │ ├─ APPLIES_TO (rule applies to subject)                             │   │
│  │ ├─ CONDITION_FOR (condition for action)                             │   │
│  │ ├─ DEFINED_AS (term defined as)                                     │   │
│  │ └─ REFERENCES (from Phase 03 cross-refs)                            │   │
│  │                                                                      │   │
│  │ Output: Relation[] with {subject, predicate, object, confidence}    │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: CrossRef Integration (Multi-hop)                            │   │
│  │ Phase 03 CrossRefs → REFERENCES edges in KG                         │   │
│  │ + Context expansion for retrieval                                   │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: GraphBuilder (Semantica)                                    │   │
│  │ ├─ merge_entities=True                                              │   │
│  │ ├─ resolve_conflicts=True                                           │   │
│  │ ├─ enable_temporal=True (for law effective dates)                   │   │
│  │ └─ graph_store=FalkorDB/Neo4j (configurable)                        │   │
│  │                                                                      │   │
│  │ Provenance Tracking:                                                 │   │
│  │ ├─ Each node links to source_id (hierarchical ID)                   │   │
│  │ └─ source_id → SQLite record → full text for citation               │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 5: LegalOntologyGenerator (extends Semantica OntologyGenerator)│   │
│  │ ├─ Legal class hierarchy (LegalDocument, Article, Clause, etc.)     │   │
│  │ ├─ Vietnamese labels                                                │   │
│  │ └─ Output: legal_ontology.ttl                                       │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 6: KG-SQLite Linker                                            │   │
│  │ Update kg_node_id in SQLite ← KG node IDs                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Semantica Core (to extend)
- `semantica/semantic_extract/ner_extractor.py` - NERExtractor
- `semantica/semantic_extract/relation_extractor.py` - RelationExtractor
- `semantica/kg/graph_builder.py` - GraphBuilder
- `semantica/kg/provenance_tracker.py` - ProvenanceTracker
- `semantica/ontology/ontology_generator.py` - OntologyGenerator

### Legal Module - Already Done ✅
- `semantica/legal/scraper/tvpl.py` - Handles text normalization (lines 415-422)
- `semantica/legal/abbreviation_extractor.py` - Abbreviation detection + full form extraction
- `semantica/legal/models.py` - All models have `kg_node_id` field ready
- `semantica/legal/db_manager.py` - Has `link_to_kg()` method (line 596)

### Legal Module - To Create
- `semantica/legal/entity_types.py` - LEGAL_ENTITY_TYPES enum
- `semantica/legal/relation_types.py` - LEGAL_RELATION_TYPES enum
- `semantica/legal/ner_extractor.py` - LegalNERExtractor (extends Semantica)
- `semantica/legal/relation_extractor.py` - LegalRelationExtractor
- `semantica/legal/kg_builder.py` - LegalKGBuilder
- `semantica/legal/ontology_generator.py` - LegalOntologyGenerator
- `semantica/legal/kg_linker.py` - KG-SQLite linker
- `semantica/legal/pipeline.py` - Full pipeline orchestrator

## Implementation Steps

### ~~Step 0: Legal Text Normalizer~~ ✅ SKIP

> **Already handled by scraper** - `semantica/legal/scraper/tvpl.py` (lines 415-422):
> - Removes "Bổ sung", "Sửa đổi" elements during parsing
> - Normalizes whitespace in `_clean_text()` method
> - No separate normalizer needed

### ~~Step 0.5: Abbreviation Dictionary~~ ✅ DONE (Phase 03.5)

> **Implemented in** `semantica/legal/abbreviation_extractor.py`:
> - Generalizable detection using POS tagging + consonant ratio (no hardcoded list)
> - Auto-detects full forms from text patterns: "X (gọi tắt là ABBREV)"
> - Stored in `LegalAbbreviationModel` database table
> - Functions: `expand_search_terms()`, `get_full_form()`, `AbbreviationExtractor`

### Step 1: Legal Entity Types (0.5h)

Create `semantica/legal/entity_types.py`:

```python
"""Legal domain entity types for NER extraction."""
from enum import Enum


class LegalEntityType(Enum):
    """Entity types for Vietnamese legal documents."""

    # Organizations
    ORGANIZATION = "ORGANIZATION"  # doanh nghiệp, công ty, cơ quan

    # Persons/Roles
    PERSON_ROLE = "PERSON_ROLE"  # Giám đốc, TGĐ, thành viên HĐQT

    # Legal terms
    LEGAL_TERM = "LEGAL_TERM"  # vốn điều lệ, cổ phần, ĐHĐCĐ

    # Quantities
    MONETARY = "MONETARY"  # 10 triệu đồng, 50% vốn điều lệ
    DURATION = "DURATION"  # 30 ngày, 06 tháng
    PERCENTAGE = "PERCENTAGE"  # 51%, trên 50%

    # Logic
    CONDITION = "CONDITION"  # nếu, trường hợp, khi, trừ trường hợp
    ACTION = "ACTION"  # thành lập, giải thể, đăng ký, chuyển nhượng

    # Consequences
    PENALTY = "PENALTY"  # phạt tiền, đình chỉ hoạt động, tước quyền


# Entity types list for NERExtractor config
LEGAL_ENTITY_TYPES = [e.value for e in LegalEntityType]

# Example patterns for each type (used in pattern-based fallback)
ENTITY_PATTERNS = {
    LegalEntityType.ORGANIZATION: [
        r"(công ty|doanh nghiệp|tổ chức|cơ quan|hợp tác xã)",
        r"(CTCP|TNHH|DNTN|HTX)",
    ],
    LegalEntityType.PERSON_ROLE: [
        r"(Giám đốc|Tổng giám đốc|Chủ tịch|thành viên)",
        r"(GĐ|TGĐ|HĐQT|HĐTV|BKS|KSV)",
    ],
    LegalEntityType.MONETARY: [
        r"(\d+[\.,]?\d*)\s*(triệu|tỷ|nghìn)?\s*(đồng|VND|USD)",
        r"(\d+[\.,]?\d*)\s*%\s*(vốn|vốn điều lệ)",
    ],
    LegalEntityType.DURATION: [
        r"(\d+)\s*(ngày|tháng|năm|giờ)",
        r"trong thời hạn\s+(\d+)\s*(ngày|tháng|năm)",
    ],
    LegalEntityType.CONDITION: [
        r"(nếu|trường hợp|khi|trừ trường hợp|trong trường hợp)",
    ],
    LegalEntityType.ACTION: [
        r"(thành lập|giải thể|đăng ký|chuyển nhượng|sáp nhập|chia|tách)",
    ],
    LegalEntityType.PENALTY: [
        r"phạt tiền\s+(\d+[\.,]?\d*)\s*(triệu|tỷ)?",
        r"(đình chỉ hoạt động|tước quyền|cấm|thu hồi)",
    ],
}
```

### Step 2: Legal Relation Types (0.5h)

Create `semantica/legal/relation_types.py`:

```python
"""Legal domain relation types for Relation extraction."""
from enum import Enum


class LegalRelationType(Enum):
    """Relation types for Vietnamese legal documents."""

    # Prerequisite relations
    REQUIRES = "REQUIRES"  # X requires Y (điều kiện tiên quyết)

    # Consequence relations
    HAS_PENALTY = "HAS_PENALTY"  # violation → penalty
    RESULTS_IN = "RESULTS_IN"  # action → result

    # Scope relations
    APPLIES_TO = "APPLIES_TO"  # rule applies to subject
    EXCLUDES = "EXCLUDES"  # rule excludes subject

    # Conditional relations
    CONDITION_FOR = "CONDITION_FOR"  # condition for action

    # Definition relations
    DEFINED_AS = "DEFINED_AS"  # term defined as
    INCLUDES = "INCLUDES"  # definition includes

    # Cross-reference relations (from Phase 03)
    REFERENCES = "REFERENCES"  # article references another
    AMENDS = "AMENDS"  # article amends another
    SUPERSEDES = "SUPERSEDES"  # article supersedes another

    # Structural relations
    CONTAINS = "CONTAINS"  # document → chapter → article


# Relation types list for RelationExtractor config
LEGAL_RELATION_TYPES = [r.value for r in LegalRelationType]

# LLM prompt hints for relation extraction
RELATION_EXAMPLES = {
    LegalRelationType.REQUIRES: [
        "Để thành lập công ty phải có ít nhất 3 cổ đông",
        "Điều kiện để được cấp phép là...",
    ],
    LegalRelationType.HAS_PENALTY: [
        "Vi phạm quy định này bị phạt tiền từ 10 đến 20 triệu",
        "Hành vi X bị xử phạt hành chính",
    ],
    LegalRelationType.APPLIES_TO: [
        "Quy định này áp dụng cho công ty cổ phần",
        "Điều này không áp dụng cho doanh nghiệp nhà nước",
    ],
    LegalRelationType.DEFINED_AS: [
        "Doanh nghiệp là tổ chức có tên riêng...",
        "Vốn điều lệ là tổng giá trị tài sản...",
    ],
    LegalRelationType.REFERENCES: [
        "theo quy định tại Điều 5",
        "căn cứ Khoản 2 Điều 10",
    ],
}
```

### Step 3: Legal NER Extractor (2h)

Create `semantica/legal/ner_extractor.py`:

```python
"""
Legal NER Extractor extending Semantica NERExtractor.

Extracts legal entities from Vietnamese legal text using LLM
with fallback to pattern-based extraction.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from semantica.semantic_extract import NERExtractor
from semantica.utils.logging import get_logger

from .entity_types import LEGAL_ENTITY_TYPES, ENTITY_PATTERNS, LegalEntityType
from .normalizer import LegalTextNormalizer
from .abbreviations import LEGAL_ABBREVIATIONS


@dataclass
class LegalEntity:
    """Extracted legal entity with provenance."""
    text: str
    entity_type: LegalEntityType
    confidence: float
    start_pos: int
    end_pos: int
    source_id: str  # Hierarchical ID from SQLite
    metadata: Dict[str, Any] = None


class LegalNERExtractor:
    """
    Extract legal entities from Vietnamese legal text.

    Uses Semantica NERExtractor with legal-specific configuration.

    Example:
        >>> extractor = LegalNERExtractor(llm_provider=llm)
        >>> entities = extractor.extract(
        ...     "Công ty TNHH phải có vốn điều lệ tối thiểu 10 tỷ đồng",
        ...     source_id="59-2020-QH14:d10:k1"
        ... )
    """

    def __init__(
        self,
        llm_provider=None,
        method: str = "llm",
        normalize: bool = True,
    ):
        self.logger = get_logger("legal_ner_extractor")
        self.method = method
        self.normalize = normalize

        # Initialize normalizer
        self.normalizer = LegalTextNormalizer() if normalize else None

        # Initialize Semantica NERExtractor
        self.ner = NERExtractor(
            method=method,
            entity_types=LEGAL_ENTITY_TYPES,
            llm_provider=llm_provider,
            fallback_chain=["llm", "pattern", "heuristic"],
            confidence_threshold=0.5,
        )

        # Custom LLM prompt for legal domain
        self._configure_llm_prompt()

    def _configure_llm_prompt(self):
        """Configure LLM with legal-specific prompt."""
        self.legal_prompt = """
Bạn là chuyên gia trích xuất thực thể từ văn bản pháp luật Việt Nam.

Trích xuất các loại thực thể sau:
- ORGANIZATION: tên công ty, tổ chức, cơ quan (bao gồm viết tắt CTCP, TNHH)
- PERSON_ROLE: chức vụ (Giám đốc, TGĐ, thành viên HĐQT)
- LEGAL_TERM: thuật ngữ pháp lý (vốn điều lệ, cổ phần, ĐHĐCĐ)
- MONETARY: số tiền (10 triệu đồng, 50% vốn)
- DURATION: thời gian (30 ngày, 06 tháng)
- CONDITION: điều kiện (nếu, trường hợp, khi)
- ACTION: hành động (thành lập, giải thể, đăng ký)
- PENALTY: hình phạt (phạt tiền, đình chỉ)

Lưu ý:
- Giữ nguyên viết tắt (HĐQT, TGĐ, TNHH)
- Trích xuất đầy đủ ngữ cảnh số tiền (bao gồm đơn vị)
- Nhận diện điều kiện kép (nếu... và...)

Văn bản:
{text}

Trả về JSON:
[{"text": "...", "type": "ENTITY_TYPE", "start": N, "end": M}]
"""

    def extract(
        self,
        text: str,
        source_id: str,
        **kwargs,
    ) -> List[LegalEntity]:
        """
        Extract legal entities from text.

        Args:
            text: Legal text content
            source_id: Hierarchical ID (e.g., "59-2020-QH14:d10:k1")

        Returns:
            List of LegalEntity objects with provenance
        """
        # Normalize text
        if self.normalizer:
            text = self.normalizer.normalize(text)

        # Extract using Semantica NERExtractor
        raw_entities = self.ner.extract_entities(
            text,
            prompt=self.legal_prompt.format(text=text) if self.method == "llm" else None,
            **kwargs,
        )

        # Convert to LegalEntity with provenance
        entities = []
        for e in raw_entities:
            entity = LegalEntity(
                text=e.text,
                entity_type=LegalEntityType(e.label),
                confidence=e.confidence,
                start_pos=e.start_char,
                end_pos=e.end_char,
                source_id=source_id,
                metadata={
                    "extraction_method": self.method,
                    "abbreviation_full": LEGAL_ABBREVIATIONS.get(e.text.upper()),
                }
            )
            entities.append(entity)

        return entities

    def extract_batch(
        self,
        items: List[Dict[str, str]],  # [{"text": ..., "source_id": ...}]
    ) -> Dict[str, List[LegalEntity]]:
        """
        Extract entities from multiple texts.

        Returns:
            Dict mapping source_id → entities
        """
        results = {}
        for item in items:
            entities = self.extract(item["text"], item["source_id"])
            results[item["source_id"]] = entities
        return results
```

### Step 4: Legal Relation Extractor (2h)

Create `semantica/legal/relation_extractor.py`:

```python
"""
Legal Relation Extractor extending Semantica RelationExtractor.

Extracts semantic relations between legal entities.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from semantica.semantic_extract import RelationExtractor
from semantica.utils.logging import get_logger

from .relation_types import LEGAL_RELATION_TYPES, RELATION_EXAMPLES, LegalRelationType
from .ner_extractor import LegalEntity


@dataclass
class LegalRelation:
    """Extracted legal relation with provenance."""
    subject: LegalEntity
    predicate: LegalRelationType
    object: LegalEntity
    confidence: float
    context: str  # Surrounding text
    source_id: str


class LegalRelationExtractor:
    """
    Extract legal relations from Vietnamese legal text.

    Uses Semantica RelationExtractor with legal-specific configuration.
    """

    def __init__(
        self,
        llm_provider=None,
        method: str = "llm",
    ):
        self.logger = get_logger("legal_relation_extractor")
        self.method = method

        # Initialize Semantica RelationExtractor
        self.rel_extractor = RelationExtractor(
            method=method,
            relation_types=LEGAL_RELATION_TYPES,
            llm_provider=llm_provider,
            fallback_chain=["llm", "dependency", "pattern"],
            context_window=100,
        )

    def extract(
        self,
        text: str,
        entities: List[LegalEntity],
        source_id: str,
    ) -> List[LegalRelation]:
        """
        Extract relations between entities in text.

        Args:
            text: Legal text content
            entities: Pre-extracted entities
            source_id: Hierarchical ID

        Returns:
            List of LegalRelation objects
        """
        # Convert LegalEntity to Semantica Entity format
        semantica_entities = [
            {"text": e.text, "label": e.entity_type.value,
             "start": e.start_pos, "end": e.end_pos}
            for e in entities
        ]

        # Extract relations
        raw_relations = self.rel_extractor.extract_relations(
            text,
            entities=semantica_entities,
        )

        # Convert to LegalRelation
        relations = []
        for r in raw_relations:
            # Find matching entities
            subject = self._find_entity(entities, r.subject.text)
            obj = self._find_entity(entities, r.object.text)

            if subject and obj:
                relation = LegalRelation(
                    subject=subject,
                    predicate=LegalRelationType(r.predicate),
                    object=obj,
                    confidence=r.confidence,
                    context=r.context,
                    source_id=source_id,
                )
                relations.append(relation)

        return relations

    def _find_entity(
        self,
        entities: List[LegalEntity],
        text: str
    ) -> Optional[LegalEntity]:
        """Find entity by text."""
        for e in entities:
            if e.text == text:
                return e
        return None
```

### Step 5: Legal KG Builder (2h)

Create `semantica/legal/kg_builder.py`:

```python
"""
Legal Knowledge Graph Builder using Semantica GraphBuilder.

Builds KG from:
- Extracted entities (NER)
- Extracted relations
- Cross-references (Phase 03)
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from semantica.kg import GraphBuilder
from semantica.kg.provenance_tracker import ProvenanceTracker
from semantica.utils.logging import get_logger

from .ner_extractor import LegalEntity
from .relation_extractor import LegalRelation
from .models import LegalCrossReferenceModel


class LegalKGBuilder:
    """
    Build legal knowledge graph from extracted data.

    Example:
        >>> builder = LegalKGBuilder(graph_store=FalkorDB(...))
        >>> kg = builder.build(
        ...     entities=entities,
        ...     relations=relations,
        ...     cross_refs=cross_refs,
        ... )
    """

    def __init__(
        self,
        graph_store=None,  # Neo4j/FalkorDB
        track_provenance: bool = True,
    ):
        self.logger = get_logger("legal_kg_builder")

        # Use Semantica GraphBuilder
        self.graph_builder = GraphBuilder(
            merge_entities=True,
            entity_resolution_strategy="fuzzy",
            resolve_conflicts=True,
            enable_temporal=True,
            graph_store=graph_store,
        )

        self.provenance_tracker = ProvenanceTracker() if track_provenance else None

    def build(
        self,
        entities: List[LegalEntity],
        relations: List[LegalRelation],
        cross_refs: List[LegalCrossReferenceModel],
    ) -> Dict:
        """
        Build knowledge graph.

        Args:
            entities: Extracted legal entities
            relations: Extracted relations
            cross_refs: Cross-references from Phase 03

        Returns:
            KG dict with {entities, relationships, metadata}
        """
        # Convert to Semantica format
        semantica_entities = self._convert_entities(entities)
        semantica_relations = self._convert_relations(relations)

        # Add cross-reference edges
        crossref_edges = self._convert_crossrefs(cross_refs)
        semantica_relations.extend(crossref_edges)

        # Build graph
        kg = self.graph_builder.build(
            sources={
                "entities": semantica_entities,
                "relationships": semantica_relations,
            }
        )

        # Track provenance
        if self.provenance_tracker:
            self._track_provenance(entities, relations)

        return kg

    def _convert_entities(self, entities: List[LegalEntity]) -> List[Dict]:
        """Convert LegalEntity to Semantica format."""
        return [
            {
                "id": f"{e.source_id}:{e.start_pos}",
                "name": e.text,
                "type": e.entity_type.value,
                "confidence": e.confidence,
                "metadata": {
                    "source_id": e.source_id,
                    "start_pos": e.start_pos,
                    "end_pos": e.end_pos,
                    **e.metadata,
                }
            }
            for e in entities
        ]

    def _convert_relations(self, relations: List[LegalRelation]) -> List[Dict]:
        """Convert LegalRelation to Semantica format."""
        return [
            {
                "source": f"{r.subject.source_id}:{r.subject.start_pos}",
                "target": f"{r.object.source_id}:{r.object.start_pos}",
                "type": r.predicate.value,
                "confidence": r.confidence,
                "metadata": {
                    "context": r.context,
                    "source_id": r.source_id,
                }
            }
            for r in relations
        ]

    def _convert_crossrefs(
        self,
        cross_refs: List[LegalCrossReferenceModel]
    ) -> List[Dict]:
        """Convert Phase 03 cross-references to KG edges."""
        edges = []
        for ref in cross_refs:
            edges.append({
                "source": ref.source_id,
                "target": ref.target_id or f"unresolved:{ref.target_article}",
                "type": "REFERENCES",
                "confidence": ref.confidence or 0.8,
                "metadata": {
                    "reference_text": ref.reference_text,
                    "resolved": ref.target_id is not None,
                }
            })
        return edges

    def _track_provenance(
        self,
        entities: List[LegalEntity],
        relations: List[LegalRelation],
    ):
        """Track provenance for citation lookup."""
        for e in entities:
            self.provenance_tracker.track_entity(
                entity_id=f"{e.source_id}:{e.start_pos}",
                source=e.source_id,
                metadata={
                    "text": e.text,
                    "type": e.entity_type.value,
                    "extraction_method": e.metadata.get("extraction_method"),
                }
            )
```

### Step 6: Legal Ontology Generator (1.5h)

Create `semantica/legal/ontology_generator.py`:

```python
"""
Legal Ontology Generator using Semantica OntologyGenerator.

Generates OWL/Turtle ontology for Vietnamese legal domain.
"""
from typing import Dict, List, Optional

from semantica.ontology import OntologyGenerator
from semantica.utils.logging import get_logger


class LegalOntologyGenerator:
    """
    Generate Vietnamese legal ontology.

    Output: legal_ontology.ttl
    """

    # Legal class hierarchy
    CLASS_HIERARCHY = {
        "owl:Thing": {
            "LegalDocument": {
                "label_vi": "Văn bản pháp luật",
                "subclasses": {
                    "Law": {"label_vi": "Luật"},
                    "Decree": {"label_vi": "Nghị định"},
                    "Circular": {"label_vi": "Thông tư"},
                    "Decision": {"label_vi": "Quyết định"},
                }
            },
            "LegalStructure": {
                "label_vi": "Cấu trúc văn bản",
                "subclasses": {
                    "Chapter": {"label_vi": "Chương"},
                    "Section": {"label_vi": "Mục"},
                    "Article": {"label_vi": "Điều"},
                    "Clause": {"label_vi": "Khoản"},
                    "Point": {"label_vi": "Điểm"},
                }
            },
            "LegalEntity": {
                "label_vi": "Chủ thể pháp lý",
                "subclasses": {
                    "Organization": {"label_vi": "Tổ chức"},
                    "PersonRole": {"label_vi": "Chức vụ"},
                }
            },
            "LegalConcept": {
                "label_vi": "Khái niệm pháp lý",
                "subclasses": {
                    "LegalTerm": {"label_vi": "Thuật ngữ"},
                    "Condition": {"label_vi": "Điều kiện"},
                    "Action": {"label_vi": "Hành vi"},
                }
            },
            "LegalConsequence": {
                "label_vi": "Hậu quả pháp lý",
                "subclasses": {
                    "Penalty": {"label_vi": "Hình phạt"},
                    "Sanction": {"label_vi": "Chế tài"},
                }
            },
        }
    }

    # Object properties
    OBJECT_PROPERTIES = {
        "references": {"domain": "Article", "range": "Article", "label_vi": "tham chiếu"},
        "amends": {"domain": "LegalDocument", "range": "LegalDocument", "label_vi": "sửa đổi"},
        "supersedes": {"domain": "LegalDocument", "range": "LegalDocument", "label_vi": "thay thế"},
        "contains": {"domain": "LegalStructure", "range": "LegalStructure", "label_vi": "bao gồm"},
        "appliesTo": {"domain": "Article", "range": "LegalEntity", "label_vi": "áp dụng cho"},
        "hasPenalty": {"domain": "Article", "range": "Penalty", "label_vi": "quy định hình phạt"},
        "requires": {"domain": "Action", "range": "Condition", "label_vi": "yêu cầu"},
    }

    def __init__(
        self,
        base_uri: str = "https://ontology.law.gov.vn/vn-legal/",
        llm_provider=None,
    ):
        self.base_uri = base_uri
        self.logger = get_logger("legal_ontology_generator")

        # Use Semantica OntologyGenerator if LLM available
        self.semantica_gen = OntologyGenerator(
            base_uri=base_uri,
            llm_provider=llm_provider,
        ) if llm_provider else None

    def generate(self, kg: Dict = None) -> str:
        """
        Generate legal ontology.

        Args:
            kg: Optional KG to infer additional classes

        Returns:
            OWL/Turtle string
        """
        ttl = self._generate_prefixes()
        ttl += self._generate_classes()
        ttl += self._generate_properties()

        if kg and self.semantica_gen:
            # Infer additional classes from KG
            inferred = self.semantica_gen.infer_classes(kg)
            ttl += self._generate_inferred_classes(inferred)

        return ttl

    def _generate_prefixes(self) -> str:
        """Generate Turtle prefixes."""
        return f"""
@prefix : <{self.base_uri}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{self.base_uri}> a owl:Ontology ;
    rdfs:label "Vietnamese Legal Ontology"@en ;
    rdfs:label "Bản thể luận pháp luật Việt Nam"@vi .

"""

    def _generate_classes(self) -> str:
        """Generate class definitions."""
        ttl = "# Classes\n"

        def add_class(name, parent, label_vi):
            nonlocal ttl
            ttl += f"""
:{name} a owl:Class ;
    rdfs:label "{name}"@en ;
    rdfs:label "{label_vi}"@vi"""
            if parent and parent != "owl:Thing":
                ttl += f" ;\n    rdfs:subClassOf :{parent}"
            ttl += " .\n"

        def process_hierarchy(hierarchy, parent=None):
            for class_name, class_def in hierarchy.items():
                if class_name == "owl:Thing":
                    process_hierarchy(class_def, None)
                else:
                    label = class_def.get("label_vi", class_name)
                    add_class(class_name, parent, label)
                    if "subclasses" in class_def:
                        process_hierarchy(class_def["subclasses"], class_name)

        process_hierarchy(self.CLASS_HIERARCHY)
        return ttl

    def _generate_properties(self) -> str:
        """Generate property definitions."""
        ttl = "\n# Object Properties\n"

        for prop_name, prop_def in self.OBJECT_PROPERTIES.items():
            ttl += f"""
:{prop_name} a owl:ObjectProperty ;
    rdfs:label "{prop_name}"@en ;
    rdfs:label "{prop_def['label_vi']}"@vi ;
    rdfs:domain :{prop_def['domain']} ;
    rdfs:range :{prop_def['range']} .
"""
        return ttl

    def _generate_inferred_classes(self, inferred: List[Dict]) -> str:
        """Generate classes inferred from KG."""
        ttl = "\n# Inferred Classes\n"
        for cls in inferred:
            ttl += f"""
:{cls['name']} a owl:Class ;
    rdfs:label "{cls['name']}"@en ;
    rdfs:subClassOf :{cls.get('parent', 'owl:Thing')} .
"""
        return ttl

    def save(self, filepath: str, kg: Dict = None):
        """Save ontology to file."""
        ttl = self.generate(kg)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ttl)
        self.logger.info(f"Saved ontology to {filepath}")
```

### Step 7: KG-SQLite Linker (1h)

Create `semantica/legal/kg_linker.py`:

```python
"""Link KG nodes to SQLite records for citation lookup."""
from typing import Dict, Optional
from semantica.utils.logging import get_logger

from .db_manager import LegalDocumentDB


class KGSQLiteLinker:
    """
    Bidirectional linking between KG nodes and SQLite records.

    Enables:
    - KG node → SQLite record → full text for citation
    - SQLite record → KG node → graph traversal
    """

    def __init__(self, db: LegalDocumentDB):
        self.db = db
        self.logger = get_logger("kg_linker")

    def link_kg_to_db(self, kg: Dict):
        """
        Update kg_node_id in SQLite for all KG nodes.

        Args:
            kg: KG dict with entities containing source_id
        """
        linked = 0
        for entity in kg.get("entities", []):
            source_id = entity.get("metadata", {}).get("source_id")
            kg_node_id = entity.get("id")

            if source_id and kg_node_id:
                success = self.db.update_kg_node_id(source_id, kg_node_id)
                if success:
                    linked += 1

        self.logger.info(f"Linked {linked} KG nodes to SQLite records")

    def get_citation_for_node(self, kg_node_id: str) -> Optional[Dict]:
        """
        Get citation info for a KG node.

        Returns:
            Dict with citation text and source info
        """
        record = self.db.get_by_kg_node_id(kg_node_id)
        if not record:
            return None

        return {
            "citation": self.db.format_citation(record["id"]),
            "text": record.get("text") or record.get("content"),
            "source_id": record["id"],
            "document_title": record.get("document_title"),
        }

    def expand_context(
        self,
        source_ids: list[str],
        include_references: bool = True,
    ) -> list[Dict]:
        """
        Expand context by including referenced articles.

        For multi-hop reasoning: when querying article A,
        also fetch articles that A references.
        """
        contexts = []

        for source_id in source_ids:
            # Get main record
            record = self.db.get_by_id(source_id)
            if record:
                contexts.append({
                    "source_id": source_id,
                    "text": record.get("text") or record.get("content"),
                    "citation": self.db.format_citation(source_id),
                    "type": "primary",
                })

            # Get referenced articles (multi-hop)
            if include_references:
                refs = self.db.get_cross_references(source_id)
                for ref in refs:
                    if ref.target_id:
                        ref_record = self.db.get_by_id(ref.target_id)
                        if ref_record:
                            contexts.append({
                                "source_id": ref.target_id,
                                "text": ref_record.get("text") or ref_record.get("content"),
                                "citation": self.db.format_citation(ref.target_id),
                                "type": "referenced",
                                "reference_text": ref.reference_text,
                            })

        return contexts
```

### Step 8: Full Pipeline (1h)

Create `semantica/legal/pipeline.py`:

```python
"""
Full Legal Semantica Pipeline orchestrator.

SQLite → Normalize → NER → Relations → GraphBuilder → Ontology
"""
from typing import Optional
from semantica.utils.logging import get_logger

from .db_manager import LegalDocumentDB
from .normalizer import LegalTextNormalizer
from .ner_extractor import LegalNERExtractor
from .relation_extractor import LegalRelationExtractor
from .kg_builder import LegalKGBuilder
from .ontology_generator import LegalOntologyGenerator
from .kg_linker import KGSQLiteLinker


class LegalSemanticaPipeline:
    """
    Orchestrate full legal semantic extraction pipeline.

    Example:
        >>> pipeline = LegalSemanticaPipeline(
        ...     db_path="legal.db",
        ...     llm_provider=llm,
        ... )
        >>> kg, ontology = pipeline.run()
    """

    def __init__(
        self,
        db_path: str,
        llm_provider=None,
        graph_store=None,
    ):
        self.logger = get_logger("legal_pipeline")

        # Initialize components
        self.db = LegalDocumentDB(db_path)
        self.normalizer = LegalTextNormalizer()
        self.ner = LegalNERExtractor(llm_provider=llm_provider)
        self.rel_extractor = LegalRelationExtractor(llm_provider=llm_provider)
        self.kg_builder = LegalKGBuilder(graph_store=graph_store)
        self.ontology_gen = LegalOntologyGenerator(llm_provider=llm_provider)
        self.linker = KGSQLiteLinker(self.db)

    def run(
        self,
        output_ontology: str = "legal_ontology.ttl",
    ) -> tuple:
        """
        Run full pipeline.

        Returns:
            (kg_dict, ontology_ttl)
        """
        self.logger.info("Starting Legal Semantica Pipeline")

        # 1. Load data from SQLite
        items = self._load_items()
        self.logger.info(f"Loaded {len(items)} items from SQLite")

        # 2. Extract entities (NER)
        all_entities = []
        for item in items:
            entities = self.ner.extract(item["text"], item["source_id"])
            all_entities.extend(entities)
        self.logger.info(f"Extracted {len(all_entities)} entities")

        # 3. Extract relations
        all_relations = []
        # Group entities by source_id
        entities_by_source = {}
        for e in all_entities:
            entities_by_source.setdefault(e.source_id, []).append(e)

        for item in items:
            item_entities = entities_by_source.get(item["source_id"], [])
            if item_entities:
                relations = self.rel_extractor.extract(
                    item["text"],
                    item_entities,
                    item["source_id"]
                )
                all_relations.extend(relations)
        self.logger.info(f"Extracted {len(all_relations)} relations")

        # 4. Get cross-references from Phase 03
        cross_refs = self.db.get_all_cross_references()
        self.logger.info(f"Loaded {len(cross_refs)} cross-references")

        # 5. Build Knowledge Graph
        kg = self.kg_builder.build(all_entities, all_relations, cross_refs)
        self.logger.info(
            f"Built KG: {kg['metadata']['node_count']} nodes, "
            f"{kg['metadata']['edge_count']} edges"
        )

        # 6. Generate Ontology
        ontology_ttl = self.ontology_gen.generate(kg)
        self.ontology_gen.save(output_ontology, kg)
        self.logger.info(f"Generated ontology: {output_ontology}")

        # 7. Link KG to SQLite
        self.linker.link_kg_to_db(kg)

        self.logger.info("Pipeline complete!")
        return kg, ontology_ttl

    def _load_items(self) -> list[dict]:
        """Load text items from SQLite."""
        items = []

        # Load articles
        for article in self.db.get_all_articles():
            text = self.normalizer.normalize(article.content or "")
            if text:
                items.append({
                    "source_id": article.id,
                    "text": text,
                    "type": "article",
                })

        # Load clauses
        for clause in self.db.get_all_clauses():
            text = self.normalizer.normalize(clause.text or "")
            if text:
                items.append({
                    "source_id": clause.id,
                    "text": text,
                    "type": "clause",
                })

        return items
```

## Todo List

- [x] ~~Create `semantica/legal/normalizer.py` (Step 0)~~ → Skip (scraper handles)
- [x] ~~Create `semantica/legal/abbreviations.py` (Step 0.5)~~ → Done as `abbreviation_extractor.py`
- [ ] Create `semantica/legal/entity_types.py` (Step 1)
- [ ] Create `semantica/legal/relation_types.py` (Step 2)
- [ ] Create `semantica/legal/ner_extractor.py` (Step 3)
- [ ] Create `semantica/legal/relation_extractor.py` (Step 4)
- [ ] Create `semantica/legal/kg_builder.py` (Step 5)
- [ ] Create `semantica/legal/ontology_generator.py` (Step 6)
- [ ] Create `semantica/legal/kg_linker.py` (Step 7)
- [ ] Create `semantica/legal/pipeline.py` (Step 8)
- [ ] Test pipeline with sample documents
- [ ] Validate ontology output
- [ ] Test multi-hop context expansion

## Success Criteria

- [x] ~~Normalizer removes "Bổ sung" noise~~ → Scraper handles during parsing
- [x] Abbreviation extraction works → `abbreviation_extractor.py` detects + stores full forms
- [ ] NER extracts 8 entity types with >80% accuracy
- [ ] Relations extracted between entities
- [ ] Cross-references converted to KG REFERENCES edges
- [ ] Ontology exports valid Turtle (.ttl)
- [ ] KG nodes linked to SQLite via kg_node_id
- [ ] Multi-hop context expansion works for retrieval

## Estimated Effort

| Step | Component | Effort | Status |
|------|-----------|--------|--------|
| ~~0~~ | ~~Normalizer~~ | ~~1h~~ | ✅ Skip |
| ~~0.5~~ | ~~Abbreviations~~ | ~~0.5h~~ | ✅ Done |
| 1 | Entity Types | 0.5h | 🔲 |
| 2 | Relation Types | 0.5h | 🔲 |
| 3 | NER Extractor | 2h | 🔲 |
| 4 | Relation Extractor | 2h | 🔲 |
| 5 | KG Builder | 2h | 🔲 |
| 6 | Ontology Generator | 1.5h | 🔲 |
| 7 | KG Linker | 1h | 🔲 |
| 8 | Pipeline | 1h | 🔲 |
| - | Testing | 2h | 🔲 |
| **Remaining** | | **12.5h** | |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM extraction quality | Medium | High | Fallback to pattern-based |
| Large text processing | Medium | Medium | Batch processing |
| Ontology validation | Low | Medium | Pre-validate hierarchy |
| Cross-ref resolution | Low | Low | Mark unresolved |

## Next Steps

After Phase 04:
1. **Phase 05**: Legal GraphRAG Integration
   - Use KG with AgentContext for retrieval
   - Multi-hop reasoning with context expansion
   - Citation generation from provenance
