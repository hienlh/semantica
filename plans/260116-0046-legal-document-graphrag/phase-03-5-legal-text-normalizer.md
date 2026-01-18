# Phase 3.5: Legal Text Normalizer

## Context Links

- [Phase 01: Database](./phase-01-legal-document-database.md)
- [Phase 03: CrossRef Detection](./phase-03-legal-entity-extraction.md)
- [Phase 04: KG & Ontology](./phase-04-legal-kg-ontology.md)
- [Main Plan](./plan.md)

## Overview

**Priority**: High (prerequisite for Phase 04)
**Status**: ✅ Done (2026-01-18)

Lightweight text normalization for Vietnamese legal documents before feeding to NER/Relation extractors.

**Key Principle**: YAGNI - only fix actual issues found in scraped data, don't over-engineer.

## Problem Analysis

### Deep Analysis Results (2026-01-18)

**Total text fields analyzed: 5876**

| Issue | Count | Status | Analysis |
|-------|-------|--------|----------|
| `<huongdan>` web UI element | 2 | ❌ **BUG** | Root cause in scraper |
| Mismatched brackets | 815 | ✅ OK | Legal format: "(a)", "(nếu có)" |
| Empty box '□' | 52 | ✅ OK | Form checkboxes |
| Ellipsis (`…` + `...`) | 4205 | ✅ OK | Form placeholders |
| Smart quotes | 582 | ✅ OK | Consistent usage |
| Very short content | 30 | ✅ OK | Table cell values |
| Leading/trailing whitespace | 0 | ✅ OK | Already clean |
| Excessive newlines | 0 | ✅ OK | Already clean |
| Unicode (not NFC) | 0 | ✅ OK | Already NFC |

**Conclusion: Data is VERY CLEAN! Only 2 real bugs found.**

### Root Cause: `<huongdan>` Element

The "Bổ sung" noise comes from TVPL's custom `<huongdan>` HTML element INSIDE `<p>` tags:

```html
<p>...cổ phần.</a><huongdan class="huong-dan-dieu-khoan">Bổ sung</huongdan></p>
```

- `<huongdan>` = Web UI element showing amendment guidance
- BeautifulSoup `get_text()` extracts ALL text including this element
- Only 2 occurrences across 10 HTML files

### Fix Location

**Option A: Fix in Scraper (Recommended)**
- Modify `_extract_text_from_paragraphs()` to strip `<huongdan>` before `get_text()`
- Prevents issue at source
- One-time fix

**Option B: Fix in Normalizer**
- Add regex pattern `Bổ sung$` to remove
- Workaround, not root fix
- May incorrectly remove valid "Bổ sung" at end of sentences

### Original Issues (Outdated)

| Issue | Example | Frequency | Solution |
|-------|---------|-----------|----------|
| ~~Web UI noise~~ | ~~"Bổ sung" at end~~ | ~~Common~~ | ~~Regex remove~~ |
| ~~Leading whitespace~~ | ~~`\n\n` at start~~ | ~~Common~~ | ~~Strip~~ |
| ~~Multiple newlines~~ | ~~`\n\n\n\n`~~ | ~~Occasional~~ | ~~Collapse~~ |
| Unicode form | Already NFC | ✓ | Verify only |

### Abbreviations Found in Corpus

| Abbreviation | Full Form | Count |
|--------------|-----------|-------|
| NĐ-CP | Nghị định - Chính phủ | 544 |
| TGĐ | Tổng giám đốc | 49 |
| HĐQT | Hội đồng quản trị | 9 |
| ĐHĐCĐ | Đại hội đồng cổ đông | 9 |
| HĐTV | Hội đồng thành viên | ~5 |
| TNHH | Trách nhiệm hữu hạn | 5 |
| BKS | Ban kiểm soát | ~5 |
| CTCP | Công ty cổ phần | ~3 |

**Decision**: Keep abbreviations in original text (LLM understands them), provide dictionary for search enhancement.

## Architecture

### Revised Approach (2026-01-18)

Since data is already clean, **Phase 3.5 scope is reduced to:**
1. Fix scraper bug (strip `<huongdan>`)
2. Re-scrape affected documents
3. Create abbreviation dictionary (for search enhancement)

**No LegalTextNormalizer needed!** Original architecture was over-engineered.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Phase 3.5: Data Quality Fix                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 1: Fix Scraper (tvpl.py)                                     │  │
│  │ └─ Strip <huongdan> elements before get_text()                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Re-scrape Affected Documents                              │  │
│  │ └─ Only 59-2020-QH14.json needs re-scrape (2 bugs)                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              ↓                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 3: Create Abbreviation Dictionary                            │  │
│  │ └─ For search enhancement (not text modification)                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Original Architecture (Deprecated)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 3.5: LegalTextNormalizer (NOT NEEDED)          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: Raw text from SQLite (Article.content, Clause.text, Point.text) │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 1: Remove Web Noise ← NOT NEEDED (fix in scraper instead)    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Fix Whitespace ← NOT NEEDED (data already clean)          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 3: Unicode NFC ← NOT NEEDED (data already NFC)               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Abbreviation Dictionary (Lookup Only)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LEGAL_ABBREVIATIONS = {                                                │
│      "HĐQT": "Hội đồng quản trị",                                       │
│      "ĐHĐCĐ": "Đại hội đồng cổ đông",                                   │
│      "TGĐ": "Tổng giám đốc",                                            │
│      ...                                                                │
│  }                                                                      │
│                                                                         │
│  Usage:                                                                 │
│  ├─ NER: entity linking (map HĐQT → full form in metadata)             │
│  └─ Search: expand query "HĐQT" → ["HĐQT", "Hội đồng quản trị"]        │
│                                                                         │
│  NOT for: Expanding abbreviations in original text                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Existing Semantica (reference only)
- `semantica/normalize/text_normalizer.py` - Base TextNormalizer class

### Legal Module (to create)
- `semantica/legal/normalizer.py` - LegalTextNormalizer
- `semantica/legal/abbreviations.py` - Abbreviation dictionary

## Implementation Steps

### Step 1: Fix Scraper (tvpl.py)

**File:** `semantica/legal/scraper/tvpl.py`

**Change:** Modify `_extract_text_from_paragraphs()` to strip web UI elements:

```python
def _extract_text_from_paragraphs(self, content_el: "Tag") -> str:
    """Extract clean text from HTML content."""
    paragraphs = content_el.find_all("p")
    cleaned_paragraphs = []

    for p in paragraphs:
        # Remove web UI elements before extracting text
        for ui_element in p.find_all(['huongdan', 'tooltip']):
            ui_element.decompose()

        text = p.get_text()
        text = " ".join(text.split())
        if text:
            cleaned_paragraphs.append(text)

    return "\n\n".join(cleaned_paragraphs)
```

### Step 2: Re-scrape Affected Document

Only `59-2020-QH14.json` has the bug (2 occurrences). Re-scrape after fix.

### Step 3: Create Abbreviation Dictionary

Create `semantica/legal/abbreviations.py` (same as before - for search enhancement)

---

## Original Implementation (Deprecated)

### ~~Step 1: LegalTextNormalizer~~ (NOT NEEDED)

~~Create `semantica/legal/normalizer.py`:~~

```python
"""
Legal Text Normalizer for Vietnamese legal documents.

Lightweight normalization:
- Remove web scraping noise
- Fix whitespace issues
- Unicode NFC normalization
"""
import re
import unicodedata
from typing import Optional


class LegalTextNormalizer:
    """
    Normalize Vietnamese legal text before NER extraction.

    Does NOT expand abbreviations (LLM understands them).
    """

    # Web UI noise patterns to remove
    WEB_NOISE_PATTERNS = [
        r'Bổ sung$',
        r'Sửa đổi$',
        r'Hướng dẫn$',
        r'Quy định chi tiết$',
        r'Xem chi tiết$',
    ]

    def normalize(self, text: str) -> str:
        """
        Normalize legal text.

        Args:
            text: Raw legal text (content field from SQLite)

        Returns:
            Normalized text ready for NER extraction
        """
        if not text:
            return ""

        # 1. Remove web UI noise
        text = self._remove_web_noise(text)

        # 2. Fix whitespace
        text = self._normalize_whitespace(text)

        # 3. Unicode NFC (standard for Vietnamese)
        text = unicodedata.normalize('NFC', text)

        return text

    def _remove_web_noise(self, text: str) -> str:
        """Remove common web scraping artifacts."""
        for pattern in self.WEB_NOISE_PATTERNS:
            text = re.sub(pattern, '', text)
        return text.strip()

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph breaks."""
        # Remove leading/trailing whitespace
        text = text.strip()
        # Normalize multiple spaces to single
        text = re.sub(r' +', ' ', text)
        # Normalize 3+ newlines to double (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def normalize_batch(self, texts: list[str]) -> list[str]:
        """Normalize multiple texts."""
        return [self.normalize(t) for t in texts]
```

### Step 2: Abbreviation Dictionary

Create `semantica/legal/abbreviations.py`:

```python
"""
Vietnamese Legal Abbreviation Dictionary.

Used for:
- NER entity linking (map HĐQT → "Hội đồng quản trị")
- Search enhancement (query both forms)

Does NOT expand in text (preserves original).
"""

# Vietnamese legal abbreviations found in corpus
LEGAL_ABBREVIATIONS = {
    # Document types
    "NĐ-CP": "Nghị định - Chính phủ",
    "NĐ": "Nghị định",
    "QH": "Quốc hội",
    "TT": "Thông tư",
    "QĐ": "Quyết định",

    # Corporate governance
    "HĐQT": "Hội đồng quản trị",
    "HĐTV": "Hội đồng thành viên",
    "ĐHĐCĐ": "Đại hội đồng cổ đông",
    "BKS": "Ban kiểm soát",
    "TGĐ": "Tổng giám đốc",
    "GĐ": "Giám đốc",
    "KSV": "Kiểm soát viên",

    # Company types
    "TNHH": "Trách nhiệm hữu hạn",
    "CTCP": "Công ty cổ phần",
    "DNTN": "Doanh nghiệp tư nhân",
    "HTX": "Hợp tác xã",
    "MTV": "Một thành viên",

    # Financial
    "VĐL": "Vốn điều lệ",
    "TSCĐ": "Tài sản cố định",

    # Government bodies
    "BKHĐT": "Bộ Kế hoạch và Đầu tư",
    "BTC": "Bộ Tài chính",
    "UBND": "Ủy ban nhân dân",
}

# Reverse mapping for search
ABBREVIATION_TO_FULL = LEGAL_ABBREVIATIONS
FULL_TO_ABBREVIATION = {v: k for k, v in LEGAL_ABBREVIATIONS.items()}


def get_full_form(abbrev: str) -> str | None:
    """Get full form of abbreviation."""
    return LEGAL_ABBREVIATIONS.get(abbrev.upper())


def get_abbreviation(full_form: str) -> str | None:
    """Get abbreviation for full form."""
    return FULL_TO_ABBREVIATION.get(full_form)


def expand_search_terms(query: str) -> list[str]:
    """
    Expand query with both abbreviation and full forms.

    Example: "HĐQT" → ["HĐQT", "Hội đồng quản trị"]
    """
    terms = [query]

    # Check if query contains abbreviation
    for abbrev, full in LEGAL_ABBREVIATIONS.items():
        if abbrev in query.upper():
            terms.append(query.upper().replace(abbrev, full))
        if full.lower() in query.lower():
            terms.append(query.lower().replace(full.lower(), abbrev))

    return list(set(terms))
```

## Discussion Points

### 1. Nên normalize trước khi lưu DB hay khi đọc ra?

**Option A: Normalize khi lưu (Phase 01)**
- Pros: Data sạch ngay từ đầu, query nhanh
- Cons: Mất raw data, khó debug

**Option B: Normalize khi đọc (Phase 3.5)**
- Pros: Giữ nguyên raw data, flexible
- Cons: Overhead mỗi lần đọc

**Recommendation**: Option B - normalize on read. Raw data valuable for debugging.

### 2. Cần thêm normalization rules nào?

Hiện tại chỉ có 3 rules:
1. Remove web noise
2. Fix whitespace
3. Unicode NFC

Có cần thêm:
- [ ] Fix số/ngày tháng format?
- [ ] Remove special characters?
- [ ] Fix encoding issues?

### 3. Abbreviation expansion?

Current decision: **Keep original, use dictionary for lookup only**

Reasons:
- LLM understands Vietnamese abbreviations
- Preserves original text for citations
- Search can expand both forms

Alternative: Expand abbreviations inline?
- Pros: Better for traditional NLP
- Cons: Changes original text, longer

## Todo List (Completed)

- [x] Fix `_extract_text_from_paragraphs()` in `tvpl.py`
- [x] Re-parse all HTML files to JSON (clean data)
- [x] Re-import to database
- [x] Verify "Bổ sung" noise removed
- [x] Re-run crossref detection (168 refs, 132 resolved)
- [ ] Create `semantica/legal/abbreviations.py` (optional - deferred to Phase 04)
- [ ] Add unit tests for scraper fix (optional - deferred)

## Success Criteria (Achieved)

- [x] `<huongdan>` elements stripped from all `<p>` tags
- [x] No "Bổ sung" noise at end of content
- [x] Database contains 615 articles, 2505 clauses, 1772 points (clean)
- [x] Cross-references restored (168 total, 132 resolved)

## Estimated Effort (Revised)

| Task | Effort |
|------|--------|
| Fix tvpl.py | 0.5h |
| Re-scrape | 0.25h |
| abbreviations.py | 0.5h |
| Unit tests | 0.25h |
| **Total** | **1.5h** |

*Reduced from 2.5h because LegalTextNormalizer is NOT needed.*

## Next Phase

After Phase 3.5 complete → Phase 04: NER Extractor (data is already clean)
