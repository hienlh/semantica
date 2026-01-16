---
title: "Legal Document GraphRAG System"
description: "Vietnamese legal document GraphRAG with hierarchical database, entity extraction, and provenance-aware retrieval"
status: pending
priority: P1
effort: 32h
branch: main
tags: [legal, graphrag, vietnamese, nlp, postgresql, knowledge-graph]
created: 2026-01-16
---

# Legal Document GraphRAG System

## Overview

Build a comprehensive Legal Document GraphRAG system for Vietnamese legal documents. The system parses hierarchical legal structures (Văn bản > Chương > Mục > Điều > Khoản > Điểm), stores in parallel PostgreSQL database, extracts legal entities with cross-reference detection, builds knowledge graphs with legal ontology, and provides provenance-aware GraphRAG retrieval.

## Phase Summary

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| **00** | **Web Scraper (thuvienphapluat.vn)** | **4h** | Playwright |
| 01 | Legal Document Database | 4h | PostgreSQL, SQLAlchemy |
| 02 | Legal Document Parser | 6h | Phase 00-01, underthesea |
| 03 | CrossRef Detection | 3h | Phase 02 |
| 04 | Semantica Integration | 2h | Phase 03, Semantica KG |
| 05 | AI Chatbot (AgentContext) | 3h | Phase 04 |

**Total: 22h** (simplified from 32h)

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

**Validated:** 2026-01-16 (Re-validated)
**Questions asked:** 10

### Re-validated Requirements

| Aspect | Original | Final Decision |
|--------|----------|----------------|
| **Core Goal** | Full GraphRAG | **Simplified: Parse + Store + CrossRef + Integrate Semantica** |
| **Use Case** | Generic | **AI Chatbot trả lời câu hỏi luật** |
| **DB Storage** | JSONB-only | **Normalized tables** (để query trực tiếp) |
| **KG/Ontology** | Custom build | **Integrate với Semantica pipeline có sẵn** |
| **NER** | Full extraction | **Skip NER, chỉ CrossRef detection** |

### Confirmed Decisions

| Decision | User Choice |
|----------|-------------|
| DB Storage | **Normalized tables** (documents → chapters → articles → clauses → points) |
| Cross-ref | **Must include law ID** (strict) |
| KG approach | **Simplified DB relations → Integrate Semantica later** |
| VN NLP | underthesea (for tokenization only) |
| Citation format | Vietnamese: "Điều X, Khoản Y - Luật Z" |

### Action Items (Plan Revisions Needed)

- [ ] **Phase 01**: Use normalized tables (NOT JSONB-only)
- [ ] **Phase 03**: Simplify to CrossRef detection only (skip full NER)
- [ ] **Phase 04**: Replace custom KG with Semantica integration code
- [ ] **Phase 05**: Use existing AgentContext instead of custom GraphRAG
- [ ] **Effort**: Reduce from 32h → 18h

### Simplified Scope

```
Original: Parse → JSONB → NER → Custom KG → Custom Ontology → Custom GraphRAG
Simplified: Parse → Normalized DB → CrossRef → Integrate Semantica KG/Ontology → AgentContext
```

## Phase Files

- [**Phase 00: Web Scraper (thuvienphapluat.vn)**](./phase-00-web-scraper.md) ⭐ NEW
- [Phase 01: Legal Document Database](./phase-01-legal-document-database.md)
- [Phase 02: Legal Document Parser](./phase-02-legal-document-parser.md)
- [Phase 03: CrossRef Detection](./phase-03-legal-entity-extraction.md)
- [Phase 04: Semantica Integration](./phase-04-legal-kg-ontology.md)
- [Phase 05: AI Chatbot](./phase-05-legal-graphrag-integration.md)
