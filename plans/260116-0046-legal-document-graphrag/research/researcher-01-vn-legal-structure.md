# Vietnamese Legal Document Hierarchical Structure Research

**Date:** 2026-01-16
**Focus:** Structure, parsing patterns, and database schema for Vietnamese legal documents

---

## 1. Vietnamese Legal Document Hierarchy

Vietnamese normative legal documents (Văn bản quy phạm pháp luật) follow a standardized hierarchical structure:

```
Văn bản (Document)
├── Phần (Part) [optional, Roman numerals: I, II, III...]
├── Chương (Chapter) [Roman numerals or Arabic numerals: 1, 2, 3...]
│   ├── Mục (Section) [Arabic numerals: 1, 2, 3...]
│   │   ├── Tiểu mục (Subsection) [nested structure]
│   │   └── Điều (Article) [Arabic numerals with period: 1., 2., 3.]
│   │       ├── Khoản (Clause) [Arabic numerals: 1), 2), 3)]
│   │       │   └── Điểm (Point) [Lowercase Vietnamese letters: a), b), c)]
```

**Numbering Convention:**
- Part/Chapter: Roman numerals (I, II, III)
- Section/Article: Arabic numerals (1, 2, 3)
- Clause within article: Arabic numerals with parenthesis: 1), 2), 3)
- Points within clause: Vietnamese lowercase letters: a), b), c)

**Example Citation Format:** "Điều 5, Khoản 2, Điểm a" (Article 5, Clause 2, Point a)

---

## 2. Key Structural Characteristics

| Level | Purpose | Numbering | Independence |
|-------|---------|-----------|--------------|
| Chương | Group related articles by subject area | Roman | High - standalone topic |
| Mục | Subdivide chapters into logical groupings | Arabic | Medium - maintains subject coherence |
| Điều | Define specific provisions/rules | Arabic + period | Complete thoughts |
| Khoản | Separate independent ideas within articles | Arabic + paren | Each clause is self-contained |
| Điểm | Enumerate details/items within clauses | Letters + paren | Specific implementation details |

**Critical Parsing Rules:**
- Each clause (Khoản) must form complete sentence with independent meaning
- Points (Điểm) never stand alone; must belong to clause
- Article (Điều) numbering restarts within each chapter
- Clause (Khoản) numbering restarts within each article

---

## 3. Recommended Regex Patterns for Extraction

### Pattern 1: Article Header
```regex
^Điều\s+(\d+)[:\.\s](.+)$
```
Captures: `Điều 5: Tuyên bố chính sách` → group1=5, group2=Tuyên bố chính sách

### Pattern 2: Clause Marker
```regex
^\s*(\d+)\)\s+(.+)$
```
Captures: `1) Nội dung chính` → group1=1, group2=Nội dung chính

### Pattern 3: Point Marker (Vietnamese Letters)
```regex
^\s*([a-z])\)\s+(.+)$
```
Captures: `a) Chi tiết thực hiện` → group1=a, group2=Chi tiết thực hiện

### Pattern 4: Chapter/Section Header
```regex
^Chương\s+([IVX]+|[0-9]+)[:\.\s](.+)$
```
Flexible for both Roman and Arabic numerals

---

## 4. Parsing Strategy (Hierarchical)

**Two-Pass Approach:**

**Pass 1 - Structural Parsing:**
1. Extract document metadata (title, issuing authority, effective date)
2. Identify all chapters using chapter pattern
3. Map sections (Mục) within chapters
4. Map articles within sections

**Pass 2 - Content Parsing:**
1. Extract full text for each article
2. Split by clause markers (digit + parenthesis)
3. Split each clause by point markers (letter + parenthesis)
4. Preserve hierarchical relationships

**Data Structure Output:**
```python
{
  "document": {
    "title": str,
    "id": str,
    "effective_date": datetime,
    "chapters": [
      {
        "number": int,
        "title": str,
        "sections": [
          {
            "number": int,
            "title": str,
            "articles": [
              {
                "number": int,
                "title": str,
                "clauses": [
                  {
                    "number": int,
                    "text": str,
                    "points": [
                      {"letter": str, "text": str}
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

## 5. Database Schema (PostgreSQL + JSON)

### Core Tables

**documents**
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  type VARCHAR(50), -- 'law', 'decree', 'decision', 'circular'
  issuing_authority VARCHAR(200),
  effective_date DATE,
  effective_number VARCHAR(100),
  document_source TEXT, -- Original PDF/DOCX path
  created_at TIMESTAMP
);
```

**chapters**
```sql
CREATE TABLE chapters (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id),
  chapter_number INT NOT NULL,
  title VARCHAR(500),
  position INT, -- Document position for ordering
  created_at TIMESTAMP,
  UNIQUE(document_id, chapter_number)
);
```

**articles**
```sql
CREATE TABLE articles (
  id UUID PRIMARY KEY,
  chapter_id UUID REFERENCES chapters(id),
  article_number INT NOT NULL,
  title VARCHAR(500),
  full_text TEXT,
  position INT,
  created_at TIMESTAMP,
  UNIQUE(chapter_id, article_number)
);
```

**clauses**
```sql
CREATE TABLE clauses (
  id UUID PRIMARY KEY,
  article_id UUID REFERENCES articles(id),
  clause_number INT NOT NULL,
  text TEXT NOT NULL,
  position INT,
  created_at TIMESTAMP,
  UNIQUE(article_id, clause_number)
);
```

**points**
```sql
CREATE TABLE points (
  id UUID PRIMARY KEY,
  clause_id UUID REFERENCES clauses(id),
  point_letter VARCHAR(1) NOT NULL,
  text TEXT NOT NULL,
  position INT,
  created_at TIMESTAMP,
  UNIQUE(clause_id, point_letter)
);
```

**Recommendation:** Add JSONB column to `documents` for full hierarchical storage alongside normalized tables for querying flexibility.

---

## 6. Vietnamese Legal NLP Tools

| Tool | Purpose | Language Support | Notes |
|------|---------|-----------------|-------|
| **underthesea** | Vietnamese NLP pipeline | Vietnamese | Word segmentation, POS tagging, NER trained on Vietnamese legal text |
| **VnCoreNLP** | Vietnamese text processing | Vietnamese | Better for legal terms, dependency parsing |
| **pyvi** | Vietnamese text tokenization | Vietnamese | Lightweight, word segmentation only |
| **SpaCy (vi_core_news)** | General NER/POS | Vietnamese | Limited legal domain training |

**Recommendation for Legal Documents:** Combine `underthesea` for preprocessing + custom domain-specific NER model trained on Vietnamese legal annotations.

---

## 7. Parsing Implementation Approach

**Phase 1 - Basic Parser:**
- Use regex patterns to extract chapter/article/clause/point structure
- Maintain hierarchy with integer tracking
- Store in normalized PostgreSQL schema

**Phase 2 - Enhanced Parser (with Semantica integration):**
- Use `DocumentParser` for initial text extraction
- Apply `TextSplitter` with custom boundaries (articles/clauses)
- Use `NERExtractor` with Vietnamese models (underthesea backend)
- Extract legal entities: Organizations, Officials, Dates, Regulations, Penalties
- Use `RelationExtractor` to identify legal relationships: "applies_to", "amends", "repeals"

**Phase 3 - Knowledge Graph:**
- Build graph nodes: Documents → Chapters → Articles → Clauses → Points
- Edge types: "contains", "amends", "references", "defines"
- Enable temporal relationships for effective dates

---

## Key Findings Summary

✓ Vietnamese legal documents have **standardized hierarchical structure** enabling regex-based parsing
✓ **Five-level nesting** (Chapter→Section→Article→Clause→Point) supports structured storage
✓ **Numbering patterns are consistent** (Roman for chapters, Arabic for articles, letters for points)
✓ **Clause/Point independence** requirement enables granular semantic extraction and querying
✓ Vietnamese NLP tools (underthesea) exist but require domain-specific training for accuracy
✓ Dual storage (normalized + JSONB) balances query flexibility with hierarchical preservation

---

## Unresolved Questions

1. **Multi-paragraph clauses:** How to handle clauses with internal paragraph breaks? Preserve as-is or normalize?
2. **Cross-references:** What's the best approach for storing/querying inter-document references (e.g., "See Article 5 of Law ABC")?
3. **Amendments:** Should document amendments create new versions or store as temporal edges in graph?
4. **Effective dates:** How to handle delayed effective dates and complex validity periods across clauses?
5. **Vietnamese NER training data:** Where to source or create annotated Vietnamese legal text for domain-specific NER?

---

## Sources

- [Thứ tự chương, mục, điều, khoản, điểm tiết trong văn bản](https://phapche.edu.vn/thu-tu-chuong-muc-dieu-khoan-diem-tiet-trong-van-ban-nhu-the-nao/)
- [Chi tiết về bố cục của văn bản pháp luật](https://luatvietnam.vn/linh-vuc-khac/chi-tiet-ve-bo-cuc-cua-van-ban-phap-luat-883-94999-article.html)
- [Hướng dẫn thể thức, kỹ thuật trình bày văn bản quy phạm pháp luật](https://trangtinphapluat.com/blog/bai-viet-hay/tu-phap/huong-dan-the-thuc-ky-thuat-trinh-bay-van-ban-quy-pham-phap-luat/)
