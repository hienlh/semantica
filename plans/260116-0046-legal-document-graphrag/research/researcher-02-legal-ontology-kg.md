# Legal Ontology & Knowledge Graph Design Research

**Date:** 2026-01-16 | **Sources:** 9 | **Scope:** Legal KG standards, entity/relationship types, cross-reference patterns

## Executive Summary

Legal domain requires domain-specific ontologies (LKIF, ELI, LegalRuleML) mapping legislation to standardized identifiers. Entity extraction leverages pretrained legal-BERT models (F1 93-99%+). Cross-reference detection combines NLP patterns with deep learning. KG linking depends on structured metadata and semantic entity resolution.

## Key Findings

### 1. Legal Ontology Standards

**LKIF Core (15 modules):**
- Top-level concepts: place, time, mereology, spacetime, normative concepts
- Represents norms, agents, legal actions, obligations, permissions
- Uses OWL-DL + SWRL for knowledge representation
- Baseline for legal reasoning systems

**ELI (European Legislation Identifier):**
- HTTP URIs for legislation metadata (jurisdiction, type, date, version)
- Standardized format for cross-border legislation reuse
- Maps legislation relationships and legal basis
- Enables semantic interoperability via URI identifiers

**LegalRuleML:**
- XML-based extension of RuleML for legal rules/norms
- Enables exchange between legal docs, business rules, software
- Supports deontic logic (obligations, permissions, prohibitions)

### 2. Entity Types for Legal Domain

**Recommended NER Tags:**
- LEGISLATION (Act, Decree, Regulation, Ordinance)
- ARTICLE (Điều X)
- CLAUSE (specific provision)
- PENALTY (sentence, fine, imprisonment)
- PARTY (natural person, organization, government body)
- DATE (effective, enactment, amendment dates)
- AMOUNT (monetary penalties, thresholds)
- COURT (jurisdiction, tribunal)
- REFERENCE (statute citations, case citations)

**Recent Models:** Legal-BERT, CaseLawBERT, ContractBERT, LegNER (F1 >99%)

### 3. Relationship Types

**KG Relationships:**
- `references` (Article X references Article Y)
- `amends` (newer law modifies older law)
- `supersedes` (replaces previous legislation)
- `implements` (domestic law implements treaty)
- `defines` (defines legal concept)
- `establishes_penalty` (article → penalty)
- `applies_to` (law → entity/domain)
- `cited_in` (case/judgment → legislation)

### 4. Cross-Reference Detection Patterns

**Detection Approach:**
- BNF grammar formalizing natural language patterns
- Example: "theo Điều X Luật Y Năm Z" → Article X of Law Y (Year Z)
- NLP pattern matching + CRF/BiLSTM/BERT-based sequence labeling
- BERT achieves F1 ~0.98 on multi-jurisdictional tests

**Resolution:** Link extracted reference to target provision URI using ELI/ECLI identifiers

### 5. KG Linking Strategy

**Architecture:**
1. **Entity Extraction:** Legal-BERT NER → entity candidates
2. **Normalization:** Resolve "Điều 1 Luật số 20/2014" → canonical ELI URI
3. **Link Prediction:** Match extracted entities to KG nodes via semantic similarity
4. **Citation Resolution:** Extract article/law references, link to authoritative sources
5. **Versioning:** Track amendments, effective dates in metadata

**Data Structure:**
```
Node: {
  uri: "eli:vn:law:2014:20",
  type: "LEGISLATION",
  title: "Law on...",
  jurisdiction: "VN",
  date_enacted: "2014-01-15"
}

Edge: {
  source: "eli:vn:law:2014:20/article/1",
  target: "eli:vn:law:2014:20/article/5",
  relationship: "references",
  cited_text: "theo Điều 5"
}
```

### 6. Provenance Tracking

- Store original citation text for audit trail
- Track amendment chain with effective dates
- Link to source documents (gazette, legal database)
- Version control for evolving legislation
- Confidence scores from NER/linking models

## Implementation Recommendations

1. **Start with ELI/ECLI URIs** for legislation identifiers (standardized, cross-border compatible)
2. **Use LegNER or Legal-BERT** for entity extraction (>93% F1 out-of-box)
3. **Implement BNF-based pattern matching** for Vietnamese cross-reference syntax (high precision)
4. **Layer relationship extraction** via fine-tuned transformer or rule-based patterns
5. **Maintain provenance** with original text + extraction confidence

## Unresolved Questions

- Optimal Vietnamese-specific cross-reference grammar (patterns for Vietnamese legislative syntax)?
- How to handle ambiguous article references (e.g., "Điều 1" could resolve to multiple laws)?
- Should relationship types use semantic web standards (RDF properties) or property graph model?
- Best practice for versioning KG when legislation is amended (append history or replace)?

## Sources

- [LKIF Core Ontology](https://github.com/RinkeHoekstra/lkif-core)
- [ELI Standard](https://eur-lex.europa.eu/content/help/eurlex-content/eli.html)
- [Automated Cross-Reference Detection Framework](https://link.springer.com/article/10.1007/s00766-015-0241-3)
- [Legal Entity Recognition with BERT](https://arxiv.org/html/2410.08521v1)
- [LegNER Domain-Adapted Transformer](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1638971/full)
- [LegalRuleML Specification](https://www.researchgate.net/publication/225256462_LegalRuleML_XML-Based_Rules_and_Norms)
- [ELI & Akoma Ntoso Ontology Mapping](https://dl.acm.org/doi/fullHtml/10.1145/3614321.3614327)
