# Phase 04: Legal Knowledge Graph & Ontology

## Context Links

- [Research: Semantica KG Pipeline](../reports/researcher-260117-1736-semantica-kg-ontology-pipeline.md)
- [Phase 01: Database](./phase-01-legal-document-database.md)
- [Phase 03: CrossRef Detection](./phase-03-legal-entity-extraction.md)
- [Phase 03.5: Abbreviation Extraction](./phase-03-5-legal-text-normalizer.md)
- [Main Plan](./plan.md)

## Overview

**APPROACH**: Dùng trực tiếp Semantica core (không wrapper). Nếu thiếu feature cho legal → sửa Semantica core.

```
SQLite → Semantica NERExtractor → Semantica RelationExtractor → Semantica GraphBuilder
```

**Principles**: YAGNI - KISS - DRY

## Progress (Updated 2026-01-19)

| Step | Component | Status | Notes |
|------|-----------|--------|-------|
| ~~0~~ | ~~Normalizer~~ | ✅ **Skip** | Scraper handles |
| ~~0.5~~ | ~~Abbreviations~~ | ✅ **Done** | Phase 03.5 |
| 1 | Entity Types | ✅ **Done** | `legal/entity_types.py` |
| 2 | Relation Types | ✅ **Done** | `legal/relation_types.py` |
| 3 | Pipeline | ✅ **Done** | `legal/kg_pipeline.py` |
| 4 | Semantica Mods | ✅ **Not needed** | Core works as-is |
| 5 | Testing | ✅ **Done** | 13 entities, 195 relations (5 articles) |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture** | Direct Semantica | DRY - no duplicate |
| Entity Types | 8 types | QA chatbot needs |
| CrossRef | Multi-hop KG edges | Reasoning accuracy |
| Provenance | source_id metadata | Citations |
| Modifications | Sửa Semantica core | Single source |

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                   Phase 04: Direct Semantica Usage                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INPUT: SQLite (Phase 01) + CrossRefs (Phase 03)                   │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ kg_pipeline.py - Orchestrator                                │  │
│  │                                                              │  │
│  │  from semantica.semantic_extract import NERExtractor         │  │
│  │  from semantica.semantic_extract import RelationExtractor    │  │
│  │  from semantica.kg import GraphBuilder                       │  │
│  │  from .entity_types import LEGAL_ENTITY_TYPES                │  │
│  │  from .relation_types import LEGAL_RELATION_TYPES            │  │
│  │                                                              │  │
│  │  # Direct usage with config                                  │  │
│  │  ner = NERExtractor(                                         │  │
│  │      method="llm",                                           │  │
│  │      entity_types=LEGAL_ENTITY_TYPES,                        │  │
│  │  )                                                           │  │
│  │                                                              │  │
│  │  rel = RelationExtractor(                                    │  │
│  │      method="llm",                                           │  │
│  │      relation_types=LEGAL_RELATION_TYPES,                    │  │
│  │  )                                                           │  │
│  │                                                              │  │
│  │  builder = GraphBuilder(merge_entities=True)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  OUTPUT: KG (entities + relations + cross-refs as edges)           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Semantica Core (dùng trực tiếp, sửa nếu cần)
- `semantica/semantic_extract/ner_extractor.py` - NERExtractor
- `semantica/semantic_extract/relation_extractor.py` - RelationExtractor
- `semantica/kg/graph_builder.py` - GraphBuilder

### Legal Module - Already Done ✅
- `semantica/legal/scraper/tvpl.py` - Text normalization
- `semantica/legal/abbreviation_extractor.py` - Abbreviations (Phase 03.5)
- `semantica/legal/models.py` - Has `kg_node_id` field
- `semantica/legal/db_manager.py` - Has `link_to_kg()` method

### Legal Module - To Create (config only)
- `semantica/legal/entity_types.py` - LEGAL_ENTITY_TYPES list
- `semantica/legal/relation_types.py` - LEGAL_RELATION_TYPES list
- `semantica/legal/kg_pipeline.py` - Pipeline orchestrator

## Implementation Steps

### ~~Step 0: Normalizer~~ ✅ SKIP
Scraper handles (`tvpl.py`)

### ~~Step 0.5: Abbreviations~~ ✅ DONE
Phase 03.5 (`abbreviation_extractor.py`)

### Step 1: Entity Types Config

Create `semantica/legal/entity_types.py`:

```python
"""Legal entity types for NERExtractor config."""

LEGAL_ENTITY_TYPES = [
    "ORGANIZATION",   # công ty, doanh nghiệp, cơ quan
    "PERSON_ROLE",    # Giám đốc, TGĐ, thành viên HĐQT
    "LEGAL_TERM",     # vốn điều lệ, cổ phần, ĐHĐCĐ
    "MONETARY",       # 10 triệu đồng, 50% vốn
    "DURATION",       # 30 ngày, 06 tháng
    "PERCENTAGE",     # 51%, trên 50%
    "CONDITION",      # nếu, trường hợp, khi
    "ACTION",         # thành lập, giải thể, đăng ký
    "PENALTY",        # phạt tiền, đình chỉ
]
```

### Step 2: Relation Types Config

Create `semantica/legal/relation_types.py`:

```python
"""Legal relation types for RelationExtractor config."""

LEGAL_RELATION_TYPES = [
    "REQUIRES",       # X requires Y
    "HAS_PENALTY",    # violation → penalty
    "APPLIES_TO",     # rule applies to subject
    "CONDITION_FOR",  # condition for action
    "DEFINED_AS",     # term defined as
    "REFERENCES",     # article references another (from Phase 03)
    "AMENDS",         # article amends another
    "CONTAINS",       # document → chapter → article
]
```

### Step 3: Pipeline Orchestrator

Create `semantica/legal/kg_pipeline.py`:

```python
"""
Legal KG Pipeline - Dùng trực tiếp Semantica components.
"""
from semantica.semantic_extract import NERExtractor, RelationExtractor
from semantica.kg import GraphBuilder

from .entity_types import LEGAL_ENTITY_TYPES
from .relation_types import LEGAL_RELATION_TYPES
from .db_manager import LegalDocumentDB


class LegalKGPipeline:
    """
    Pipeline dùng trực tiếp Semantica.

    Example:
        >>> pipeline = LegalKGPipeline("legal.db")
        >>> kg = pipeline.run()
    """

    def __init__(self, db_path: str, llm_provider=None):
        self.db = LegalDocumentDB(db_path)

        # Dùng trực tiếp Semantica NERExtractor
        self.ner = NERExtractor(
            method="llm",
            entity_types=LEGAL_ENTITY_TYPES,
            llm_provider=llm_provider,
        )

        # Dùng trực tiếp Semantica RelationExtractor
        self.rel = RelationExtractor(
            method="llm",
            relation_types=LEGAL_RELATION_TYPES,
            llm_provider=llm_provider,
        )

        # Dùng trực tiếp Semantica GraphBuilder
        self.builder = GraphBuilder(merge_entities=True)

    def run(self):
        """Run pipeline."""
        # 1. Load texts from SQLite
        items = self._load_items()

        # 2. Extract entities
        all_entities = []
        for item in items:
            entities = self.ner.extract_entities(item["text"])
            # Add source_id to metadata
            for e in entities:
                e.metadata["source_id"] = item["source_id"]
            all_entities.extend(entities)

        # 3. Extract relations
        all_relations = []
        for item in items:
            relations = self.rel.extract_relations(item["text"])
            all_relations.extend(relations)

        # 4. Add cross-refs from Phase 03
        cross_refs = self._load_crossrefs_as_relations()
        all_relations.extend(cross_refs)

        # 5. Build KG
        kg = self.builder.build(
            sources={"entities": all_entities, "relationships": all_relations}
        )

        # 6. Link back to SQLite
        self._link_kg_to_db(kg)

        return kg

    def _load_items(self):
        """Load articles/clauses from SQLite."""
        items = []
        for article in self.db.get_all_articles():
            if article.content:
                items.append({"source_id": article.id, "text": article.content})
        return items

    def _load_crossrefs_as_relations(self):
        """Convert Phase 03 cross-refs to relations."""
        relations = []
        for ref in self.db.get_all_cross_references():
            relations.append({
                "source": ref.source_id,
                "target": ref.target_id,
                "type": "REFERENCES",
            })
        return relations

    def _link_kg_to_db(self, kg):
        """Update kg_node_id in SQLite."""
        for entity in kg.get("entities", []):
            source_id = entity.get("metadata", {}).get("source_id")
            if source_id:
                self.db.link_to_kg(source_id, entity["id"])
```

## Todo List

- [x] ~~Normalizer~~ → Skip (scraper handles)
- [x] ~~Abbreviations~~ → Done (Phase 03.5)
- [x] Create `legal/entity_types.py`
- [x] Create `legal/relation_types.py`
- [x] Create `legal/kg_pipeline.py`
- [x] Test pipeline với real data
- [x] ~~Sửa Semantica core nếu cần~~ → Not needed

## Test Results (2026-01-19)

**Input**: 5 articles from legal_docs.db

**Output**:
- Entities: 13 (LEGAL_TERM: 7, ORGANIZATION: 4, PERSON_ROLE: 1, ACTION: 1)
- Relationships: 195 (REFERENCES: 169, related_to: 15, DEFINED_AS: 2, etc.)

**Verified**:
- NER extraction: Working (OpenAI gpt-4o-mini)
- Relation extraction: Working (multiple relation types)
- Cross-ref integration: Working (169 REFERENCES edges from Phase 03)
- GraphBuilder: Working (entity resolution, conflict detection)
- Ontology generation: Working (OntologyGenerator)
- Export: Working (JSON to data/kg_output/)
- Validation: Working (GraphValidator - 341 issues detected)
- Visualization: Requires plotly (graceful skip)

## Success Criteria

- [x] NER extracts entities with Semantica NERExtractor
- [x] Relations extracted with Semantica RelationExtractor
- [x] Cross-refs from Phase 03 → KG REFERENCES edges
- [x] KG nodes linked to SQLite via kg_node_id
- [x] Ontology generation from KG
- [x] Export to JSON (+ Neo4j, RDF support)
- [x] Quality validation with GraphValidator
- [x] Visualization (optional, requires plotly)

## Estimated Effort

| Step | Component | Effort |
|------|-----------|--------|
| 1 | Entity Types | 0.5h |
| 2 | Relation Types | 0.5h |
| 3 | Pipeline | 1h |
| 4 | Semantica mods | TBD |
| - | Testing | 1h |
| **Total** | | **~3h** |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Semantica NER không support Vietnamese | Sửa NERExtractor thêm Vietnamese prompt |
| Missing provenance tracking | Sửa GraphBuilder thêm metadata |

## Next Steps

After Phase 04:
- **Phase 05**: Legal GraphRAG Integration
