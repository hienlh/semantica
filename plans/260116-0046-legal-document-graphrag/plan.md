---
title: "Legal Document GraphRAG System"
description: "Vietnamese legal document GraphRAG with hierarchical database, entity extraction, and provenance-aware retrieval"
status: in_progress
priority: P1
effort: 16h
branch: legal
tags: [legal, graphrag, vietnamese, nlp, sqlite, knowledge-graph]
created: 2026-01-16
updated: 2026-01-17
---

# Legal Document GraphRAG System

## Overview

Build a Legal QA Chatbot for Vietnamese legal documents. System scrapes from thuvienphapluat.vn, stores hierarchical structure (Văn bản > Chương > Mục > Điều > Khoản > Điểm) in SQLite, detects cross-references, and provides AI answers with article citations.

## Phase Summary

| Phase | Description | Effort | Status | Dependencies |
|-------|-------------|--------|--------|--------------|
| **00** | Web Scraper (thuvienphapluat.vn) | 4h | ✅ **Done** | Playwright |
| **01** | Legal Document Database | 3h | ✅ **Done** | SQLite, SQLAlchemy |
| ~~02~~ | ~~Legal Document Parser~~ | ~~6h~~ | ⏭️ **Skip** | *(Scraper handles parsing)* |
| **03** | CrossRef Detection | 2h | ✅ **Done** | Phase 01 |
| **03.5** | Data Quality Fix (scraper bug) | 1.5h | ✅ **Done** | Phase 03 |
| **04** | Semantica Integration (KG/Ontology) | 12.5h | 🔲 Pending | Phase 03.5 (Step 0, 0.5 done) |
| **05** | AI Chatbot (QA) | 3h | 🔲 Pending | Phase 04 |

**Total: 26h** (remaining: ~15.5h)

## Architecture

```
Legal PDF/DOCX → FileIngestor → DoclingParser → LegalDocumentParser
                                                       ↓
                    ┌──────────────────────────────────┴──────────────────────────────────┐
                    ↓                                                                      ↓
            PostgreSQL (Hierarchical)                                           LegalNERExtractor
            documents/chapters/articles/clauses/points                                    ↓
                    ↓                                                          CrossReferenceDetector
            LegalProvenanceTracker ←──────────────────────────────────────────────────────┤
                    ↓                                                                      ↓
            LegalKGBuilder ←────────────────────────────────────── LegalRelationExtractor
                    ↓
            LegalOntologyGenerator (ELI/LKIF-inspired)
                    ↓
            AgentContext (GraphRAG) → Provenance-aware responses
```

## Key Components

1. **LegalDocumentDB** - PostgreSQL schema for hierarchical legal storage
2. **LegalDocumentParser** - Vietnamese regex patterns for structure extraction
3. **LegalNERExtractor** - Domain NER with underthesea + custom legal entities
4. **CrossReferenceDetector** - "theo Điều X Luật Y" pattern detection
5. **LegalKGBuilder** - ELI-inspired URIs, legal relationship types
6. **LegalProvenanceTracker** - Article/clause-level source tracking
7. **LegalGraphRAG** - Context retrieval with provenance citations

## Dependencies

- PostgreSQL 14+, SQLAlchemy 2.0
- underthesea (Vietnamese NLP), pyvi
- semantica.parse.DoclingParser
- semantica.semantic_extract.NERExtractor
- semantica.kg.GraphBuilder, ProvenanceTracker
- semantica.ontology.OntologyGenerator
- semantica.context.AgentContext

## Success Criteria

- [ ] Parse 10+ Vietnamese laws with 95% structural accuracy
- [ ] Cross-reference detection F1 > 0.90
- [ ] Article-level provenance in all GraphRAG responses
- [ ] Query "What penalty for X?" returns article citation

## Unresolved Questions

1. Vietnamese NER training data source for legal domain?
2. Handle amendments: new version or temporal edge?
3. Multi-paragraph clauses: preserve breaks or normalize?
4. Disambiguation for "Điều 1" referencing multiple laws?

## Validation Summary

**Last Validated:** 2026-01-18 11:45
**Validated by:** `/plan:validate`
**Status:** Phase 00-03.5 Done, Phase 04 Updated (Step 0/0.5 already done)

### Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 00 | ✅ Done | 10 docs scraped (619+ articles) |
| Phase 01 | ✅ Done | 615 articles, 2505 clauses, 1772 points in SQLite |
| Phase 02 | ⏭️ Skip | Scraper handles parsing |
| Phase 03 | ✅ Done | 168 cross-refs detected (132 resolved), NER skipped (YAGNI) |
| Phase 03.5 | ✅ Done | Fixed `<huongdan>` stripping, re-parsed HTML, re-imported DB, crossref restored (168) |
| Phase 04 | 🔲 Pending | Step 0 (skip), 0.5 (done) → NER→Relations→KG→Ontology |
| Phase 05 | 🔲 Pending | AI Chatbot QA |

### Confirmed Decisions (2026-01-17)

| Decision | User Choice |
|----------|-------------|
| Database | **SQLite** (zero-config, file-based) |
| Phase 02 | **Skip** (scraper already parses) |
| Use Case | **QA Chatbot** (trả lời câu hỏi luật với citation) |
| Citation format | Vietnamese: "Điều X, Khoản Y - Luật Z" |
| Cross-ref | Must include law ID (strict) |
| ID Format | **Hierarchical IDs** (human-readable, not UUID) |
| Phase 03 NER | **Skip** (YAGNI - only crossref needed for QA chatbot) |
| Abbreviations | **Keep original** (LLM understands), dictionary for search |
| Normalization | **On-read** (preserve raw data in DB) |
| Entity Types | Full extraction (8 types) for comprehensive QA |
| CrossRef approach | Multi-hop (KG edges + context expansion) |
| Accuracy tracking | Provenance + confidence scoring |

### Implementation Notes (2026-01-17)

**Phase 01 mở rộng hơn plan gốc:**
- Thêm `LegalSectionModel` (Mục) - hierarchy level giữa Chương và Điều
- Thêm `LegalAppendixModel` + `LegalAppendixItemModel` cho Phụ lục
- Sử dụng **Hierarchical IDs** thay vì UUID:
  - `59-2020-QH14:d5:k1:a` = Điểm a, Khoản 1, Điều 5, Luật 59/2020/QH14
  - Dễ đọc, self-documenting, natural sort

**Phase 03 đơn giản hóa theo YAGNI:**
- Plan gốc: Full NER pipeline (entity_types, vn_preprocessor, pattern_ner, crossref_detector, ner_extractor)
- Thực tế: Chỉ implement `crossref_detector.py` vì:
  - QA chatbot chỉ cần cross-reference để link các điều khoản
  - NER extraction có thể thêm sau nếu cần

### Scraped Data (Phase 00 Output)

Location: `./scraped_legal_docs/`

| File | Document | Chapters | Articles |
|------|----------|----------|----------|
| 59-2020-QH14.json | Luật Doanh nghiệp 2020 | 10 | 176 |
| 01-2021-ND.json | Nghị định 01/2021 | - | - |
| 16-2023-ND.json | Nghị định 16/2023 | - | - |
| + 7 more | ... | - | - |

### Implementation Files

| Phase | Files Implemented |
|-------|-------------------|
| 00 | `scraper/base.py`, `scraper/tvpl.py`, `scraper/hierarchy_extractor.py` |
| 01 | `models.py` (9 models), `db_manager.py`, `citation.py` |
| 03 | `crossref_detector.py` |

## Phase Files

- [Phase 00: Web Scraper](./phase-00-web-scraper.md) ✅ Done
- [Phase 01: Legal Document Database](./phase-01-legal-document-database.md) ✅ Done
- ~~[Phase 02: Legal Document Parser](./phase-02-legal-document-parser.md)~~ ⏭️ Skip
- [Phase 03: CrossRef Detection](./phase-03-legal-entity-extraction.md) ✅ Done (simplified)
- [Phase 03.5: Data Quality Fix](./phase-03-5-legal-text-normalizer.md) ← **Planning**
- [Phase 04: KG & Ontology](./phase-04-legal-kg-ontology.md)
- [Phase 05: AI Chatbot](./phase-05-legal-graphrag-integration.md)
