# Vietnamese Legal NLP & Relation Extraction Research

**Date:** 2026-01-21
**Context:** Semantica Phase 04 - Legal KG Ontology

## 1. Vietnamese Legal Document Structure

### Document Hierarchy
Vietnamese legal texts follow structured hierarchy:
- **Nghị định / Luật** (Decree / Law) - top level
- **Chương** (Chapter) - grouping articles
- **Điều** (Article) - primary semantic units
- **Khoản** (Clause) - sub-article provisions
- **Điểm** (Point) - sub-clause details

### Key Pattern: Regulatory Statements
Vietnamese legal language uses passive/impersonal constructions:
- "X phải..." (X must) = obligation
- "X được phép..." (X is permitted) = right
- "X không được..." (X is not permitted) = prohibition
- Predicate particles (**đã, sẽ, đang**) mark temporal relations

---

## 2. Trigger Words & Relation Patterns

### Critical Finding: Semantic Ambiguity
Vietnamese lacks morphological marking. Relations are identified via **context + verb particles + word order**. Key issues:

| Relation | Common Triggers | False Positives | Mitigation |
|----------|-----------------|-----------------|-----------|
| **CÓ_QUYỀN** | có quyền, được quyền, được phép | "có thể" (can/possible), "được" (passive marker) | Require agent subject (organizational entity) |
| **CÓ_NGHĨA_VỤ** | phải, có nghĩa vụ, bắt buộc | "phải" as question particle | Context window analysis |
| **ĐỊNH_NGHĨA_LÀ** | là, được định nghĩa là, có nghĩa là | General copula "là" (is) | Semantic type check (LHS = abstract concept) |
| **THAM_CHIẾU** | theo, căn cứ, quy định tại | Reference confusion (nested articles) | Exact article number matching |
| **VI_PHẠM** | vi phạm, không tuân thủ, trái với | Domain-dependent (medical: "trái với" = contradicts) | Sanction co-occurrence |

### Entity Resolution Challenge
Current implementation slugifies entities, causing false merges:
- "Công ty" + "Công ty TNHH" → single node (incorrect)
- "Điều 1" + "Điều 10" → both slugify to "dieu-1*" patterns
- Solution: **Preserve full entity text, use tuple matching (text, type, offset)**

---

## 3. LLM Misunderstandings of Vietnamese Legal Constructs

### Problem Areas

**A) Nested Modal Constructs**
```
"Công ty phải có ít nhất 2 thành viên để được Nhà nước bảo hộ"
= "Company must have ≥2 members [condition] to get State protection"
```
LLM mistakes condition (ĐIỀU_KIỆN_CHO) for obligation (CÓ_NGHĨA_VỤ).

**B) Implied Authority vs. Prohibition**
```
"Cơ quan X quy định về Y" (Agency X regulates Y)
→ Should infer: X CÓ_THẨM_QUYỀN Y
```
LLM may extract only explicit triple, missing implicit authority.

**C) Abbreviation Expansion**
Vietnamese legal texts use short forms: "TNHH" (Limited Liability), "HĐND" (People's Council).
Current db system stores abbreviations but doesn't normalize in extraction.

---

## 4. Post-Processing Validation Techniques

### 1. **Confidence Scoring Multi-Level**
```python
confidence = (
    base_llm_score * 0.4 +
    pattern_match_score * 0.3 +
    entity_type_consistency * 0.2 +
    semantic_sanity_check * 0.1
)
# Reject if < 0.55
```

### 2. **Semantic Type Validation**
- **CÓ_QUYỀN**: subject ∈ {ORG, PERSON, ROLE}, object ∈ {ACTION, ATTRIBUTE}
- **ĐỊNH_NGHĨA_LÀ**: subject ∈ {ABSTRACT_CONCEPT}, object ∈ {DEFINITION}
- **VI_PHẠM**: object ∈ {REGULATION} AND relation mentions sanction

### 3. **Coreference Resolution**
Link pronouns ("nó", "nó") to last referenced entity using distance + gender heuristics.

### 4. **Cross-Reference Consistency**
If article A references article B with "theo" (according to), validate extracted relations don't contradict B's content.

---

## 5. Entity Resolution Strategies

### Current Issue
Your implementation uses `slugify_vietnamese()` → loses precision:
- Multiple entities collapse to same slug (false edges)
- Article number normalization errors

### Recommended Approach

**Multi-Pass Resolution:**
1. **Exact Matching** (Phase 1): (text, type, char_offset) tuples
2. **Abbreviation Normalization** (Phase 2): Expand known abbreviations, re-match
3. **Fuzzy Matching** (Phase 3): Levenshtein distance for typos, only within 95% threshold
4. **Scope-Based Merging** (Phase 4): Only merge if same document + same section

**Implementation:**
```python
class EntityResolver:
    def resolve(self, entity_text, entity_type, document_id):
        # 1. Check exact cache
        exact_key = (entity_text, entity_type, document_id)
        if exact_key in self.cache:
            return self.cache[exact_key]

        # 2. Check abbreviations
        expanded = LEGAL_ABBREVIATIONS.get(entity_text.upper())
        if expanded:
            return self.resolve(expanded, entity_type, document_id)

        # 3. Fuzzy match within high threshold
        candidates = [...]  # fuzzywuzzy match

        return best_match or create_new()
```

---

## 6. Common Mistakes in Vietnamese Legal NLP

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Over-extraction (LIÊN_QUAN spam) | 40%+ relations are fallback type | Disable cooccurrence fallback, require explicit trigger |
| Abbreviation confusion | "TNHH" extracted as entity but also merged with "Công ty" | Normalize before relation extraction |
| Nested article refs unresolved | "Điều 1 sửa đổi Điều 2 khoản 3" fails to resolve | Build article graph first, validate targets exist |
| Modal scope errors | "Với điều kiện X, phải Y" incorrectly maps both to CÓ_NGHĨA_VỤ | Track syntactic scope (prepositional phrases) |
| Negation loss | "không được phép X" extracted as CÓ_QUYỀN | Check for "không" / "không được" / "cấm" before trigger |

---

## 7. Research Findings Summary

### Recent Advances (2024-2025)
1. **Graph RAG for Legal Texts** - Neo4j-based KG improving retrieval of Vietnamese legal info (SpringerLink)
2. **Hybrid Dependency Tree + LLM** - Combining syntactic parsing with LLMs for legal term detection (Springer Nature)
3. **Synthetic Data Generation** - Creating 620k+ synthetic legal queries to improve retrieval (arXiv)
4. **Legal-Onto Ontology** - Using Vietnamese SBert + ontology for semantic legal doc comparison
5. **VNLegalEase Chatbot** - GPT-4o + RAG for Vietnamese legal QA

### No Direct Solution For
- Domain-specific trigger word lists (each org has own terminology)
- Nested modal construction parsing (research gap)
- Dynamic abbreviation discovery (manual maintenance needed)

---

## Unresolved Questions

1. **How to handle domain-specific terminology variations?**
   - Different agencies use different wording for same legal concept
   - Suggest: Build terminology mapping per-agency or per-legal-corpus

2. **Should abbreviation normalization happen at extraction or post-processing?**
   - Early normalization may lose context for disambiguation
   - Late normalization causes duplicate entity issues

3. **What confidence threshold is appropriate for legal KG edges?**
   - Strict (>0.8): fewer errors but incomplete graph
   - Lenient (>0.6): more edges but hallucinations

4. **How to validate extracted relations against source legal intent?**
   - Manual review is expensive
   - Suggest: Sampling + semantic coherence checks

---

**Sources:**
- [Graph RAG for Vietnamese Legal Texts](https://link.springer.com/chapter/10.1007/978-3-031-98164-7_25)
- [Legal Term Detection with Dependency Trees & LLMs](https://link.springer.com/chapter/10.1007/978-981-96-7071-0_1)
- [Multi-stage Information Retrieval for Vietnamese Legal Texts](https://ar5iv.labs.arxiv.org/html/2209.14494)
- [Improving Vietnamese Legal Document Retrieval with Synthetic Data](https://arxiv.org/html/2412.00657v1)
- [Legal NLP Survey 2024](https://arxiv.org/pdf/2410.21306)
- [Legal-Onto Ontology for Document Analysis](https://link.springer.com/article/10.1007/s42979-025-04432-0)
- [VNLegalEase Vietnamese Legal Chatbot](https://link.springer.com/chapter/10.1007/978-981-97-9616-8_23)
- [VLSP NER Benchmark](https://vlsp.org.vn/)
- [Vietnamese Grammar Reference](https://en.wikipedia.org/wiki/Vietnamese_grammar)
