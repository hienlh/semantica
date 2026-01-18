# Phase 03: Cross-Reference Detection

## Context Links

- [Research: Legal Ontology & KG](./research/researcher-02-legal-ontology-kg.md)
- [Phase 01: Database](./phase-01-legal-document-database.md)
- [Main Plan](./plan.md)

## Overview

**SIMPLIFIED (YAGNI):** Build cross-reference detector for Vietnamese legal text. Detects "theo Điều X Luật Y" patterns and stores references in database. Full NER pipeline deferred - not needed for QA chatbot MVP.

**Status:** ✅ Completed (2026-01-17)

### What Was Implemented vs Planned

| Planned | Implemented | Reason |
|---------|-------------|--------|
| `entity_types.py` | ❌ Skipped | YAGNI - QA chatbot doesn't need entity extraction |
| `vn_preprocessor.py` | ❌ Skipped | YAGNI - crossref patterns work on raw text |
| `pattern_ner.py` | ❌ Skipped | YAGNI - defer to Phase 04/05 if needed |
| `crossref_detector.py` | ✅ Done | Core feature for linking articles |
| `ner_extractor.py` | ❌ Skipped | YAGNI - can add later |

### Original Plan (for reference)

Build Vietnamese legal NER pipeline and cross-reference detector. Extends Semantica's `NERExtractor` with domain-specific legal entity types (LEGISLATION, PENALTY, PARTY, etc.) using underthesea + custom patterns. Detects "theo Điều X Luật Y" cross-references for KG relationship building.

## Key Insights (from Research)

- **Entity types**: LEGISLATION, ARTICLE, CLAUSE, PENALTY, PARTY, DATE, AMOUNT, COURT
- **Models**: Legal-BERT achieves F1 >93%, LegNER >99%
- **Cross-reference**: BNF grammar for "theo Điều X" patterns
- **Vietnamese NLP**: underthesea for tokenization/POS, custom NER layer

## Requirements

### Functional

- FR-01: Extract legal entity types (LEGISLATION, PENALTY, PARTY, DATE, AMOUNT)
- FR-02: Detect article cross-references ("theo Điều X", "căn cứ Điều Y")
- FR-03: Extract penalty specifications (imprisonment duration, fine amounts)
- FR-04: Identify parties (government bodies, organizations, persons)
- FR-05: Output entities with confidence scores
- FR-06: Link cross-references to target articles in database

### Non-Functional

- NFR-01: F1 > 0.85 on Vietnamese legal text
- NFR-02: Cross-reference detection F1 > 0.90
- NFR-03: Process clause text in <100ms
- NFR-04: Support batch extraction for full documents

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LegalEntityPipeline                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Parsed Clauses ──→ ┌───────────────────────────────────────┐           │
│                     │ Vietnamese Preprocessor               │           │
│                     │ - underthesea word_tokenize           │           │
│                     │ - underthesea pos_tag                 │           │
│                     └───────────────────┬───────────────────┘           │
│                                         ↓                                │
│           ┌─────────────────────────────┴─────────────────────────────┐ │
│           ↓                             ↓                             ↓ │
│  ┌────────────────────┐   ┌────────────────────┐   ┌─────────────────┐ │
│  │ PatternNER         │   │ MLBasedNER         │   │ CrossRefDetector │ │
│  │ - Date patterns    │   │ - underthesea NER  │   │ - "theo Điều X"  │ │
│  │ - Amount patterns  │   │ - spaCy vi_core    │   │ - "căn cứ Điều Y"│ │
│  │ - Penalty patterns │   │ - Custom CRF/BERT  │   │ - "Luật số ABC"  │ │
│  └────────┬───────────┘   └────────┬───────────┘   └────────┬────────┘ │
│           ↓                         ↓                        ↓          │
│           └─────────────────────────┴────────────────────────┘          │
│                                     ↓                                    │
│                          ┌─────────────────────────┐                    │
│                          │ EntityMerger            │                    │
│                          │ - Deduplicate           │                    │
│                          │ - Resolve conflicts     │                    │
│                          │ - Assign confidence     │                    │
│                          └────────────┬────────────┘                    │
│                                       ↓                                  │
│  Output: List[LegalEntity] + List[CrossReference]                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

- `/Users/hienlh/Projects/semantica/semantica/semantic_extract/__init__.py` - Extract module
- `/Users/hienlh/Projects/semantica/semantica/semantic_extract/ner_extractor.py` - NERExtractor
- `/Users/hienlh/Projects/semantica/semantica/semantic_extract/relation_extractor.py` - RelationExtractor
- `/Users/hienlh/Projects/semantica/semantica/semantic_extract/named_entity_recognizer.py` - NamedEntityRecognizer

## Implementation Steps

### Step 1: Define Legal Entity Types (0.5h)

Create `semantica/legal/entity_types.py`:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

class LegalEntityType(Enum):
    """Vietnamese legal domain entity types."""
    LEGISLATION = "LEGISLATION"  # Luật, Nghị định, Thông tư
    ARTICLE = "ARTICLE"          # Điều X
    CLAUSE = "CLAUSE"            # Khoản Y
    POINT = "POINT"              # Điểm Z
    PENALTY = "PENALTY"          # Phạt tiền, phạt tù
    PARTY = "PARTY"              # Tổ chức, cá nhân
    GOVERNMENT_BODY = "GOV_BODY" # Quốc hội, Chính phủ
    DATE = "DATE"                # Ngày/tháng/năm
    AMOUNT = "AMOUNT"            # 50.000.000 đồng
    DURATION = "DURATION"        # 5 năm tù
    COURT = "COURT"              # Tòa án
    REFERENCE = "REFERENCE"      # Cross-reference to another article

@dataclass
class LegalEntity:
    """Represents an extracted legal entity."""
    text: str
    entity_type: LegalEntityType
    start_pos: int
    end_pos: int
    confidence: float
    metadata: Optional[dict] = None

    # For PENALTY entities
    penalty_type: Optional[str] = None  # 'fine', 'imprisonment', 'warning'
    penalty_value: Optional[str] = None  # '50000000' or '5 years'

    # For REFERENCE entities
    target_article: Optional[int] = None
    target_law: Optional[str] = None

@dataclass
class CrossReference:
    """Represents a cross-reference between legal provisions."""
    source_article_id: str
    target_article_num: int
    target_law_number: Optional[str]
    reference_text: str
    reference_type: str  # 'references', 'amends', 'supersedes'
    confidence: float
    start_pos: int
    end_pos: int
```

### Step 2: Create Vietnamese NER Preprocessor (1h)

Create `semantica/legal/vn_preprocessor.py`:

```python
from typing import List, Tuple
import re

class VietnamesePreprocessor:
    """Vietnamese text preprocessing for NER."""

    def __init__(self):
        try:
            from underthesea import word_tokenize, pos_tag
            self.word_tokenize = word_tokenize
            self.pos_tag = pos_tag
            self._has_underthesea = True
        except ImportError:
            self._has_underthesea = False

    def tokenize(self, text: str) -> List[str]:
        """Tokenize Vietnamese text."""
        if self._has_underthesea:
            return self.word_tokenize(text)
        # Fallback: simple whitespace tokenization
        return text.split()

    def pos_tags(self, text: str) -> List[Tuple[str, str]]:
        """Get POS tags for Vietnamese text."""
        if self._has_underthesea:
            return self.pos_tag(text)
        # Fallback: return tokens with 'UNK' tag
        return [(t, 'UNK') for t in text.split()]

    def normalize_numbers(self, text: str) -> str:
        """Normalize Vietnamese number formats."""
        # 50.000.000 đồng -> 50000000 đồng
        pattern = r'(\d{1,3}(?:\.\d{3})+)\s*(đồng|VND|VNĐ)'
        def replace_fn(m):
            num = m.group(1).replace('.', '')
            return f'{num} {m.group(2)}'
        return re.sub(pattern, replace_fn, text, flags=re.IGNORECASE)

    def preprocess(self, text: str) -> str:
        """Full preprocessing pipeline."""
        text = self.normalize_numbers(text)
        return text
```

### Step 3: Create Pattern-Based NER (1.5h)

Create `semantica/legal/pattern_ner.py`:

```python
import re
from typing import List
from .entity_types import LegalEntity, LegalEntityType

class PatternNER:
    """Pattern-based NER for Vietnamese legal entities."""

    PATTERNS = {
        LegalEntityType.LEGISLATION: [
            (r'Luật\s+(?:số\s+)?(\d+/\d{4}/[A-Z0-9]+)', 'law'),
            (r'Nghị\s+định\s+(?:số\s+)?(\d+/\d{4}/NĐ-CP)', 'decree'),
            (r'Thông\s+tư\s+(?:số\s+)?(\d+/\d{4}/TT-[A-Z]+)', 'circular'),
        ],
        LegalEntityType.ARTICLE: [
            (r'Điều\s+(\d+)', 'article'),
        ],
        LegalEntityType.CLAUSE: [
            (r'Khoản\s+(\d+)', 'clause'),
        ],
        LegalEntityType.POINT: [
            (r'Điểm\s+([a-zđ])', 'point'),
        ],
        LegalEntityType.PENALTY: [
            # Fine patterns
            (r'phạt\s+tiền\s+(?:từ\s+)?(\d[\d\.]*)\s*(?:đến\s+(\d[\d\.]*))?.*?đồng', 'fine'),
            (r'(\d[\d\.]*)\s*đồng', 'fine'),
            # Imprisonment patterns
            (r'phạt\s+tù\s+(?:từ\s+)?(\d+)\s*(?:tháng|năm)', 'imprisonment'),
            (r'(\d+)\s*năm\s+tù', 'imprisonment'),
            (r'cải\s+tạo\s+không\s+giam\s+giữ', 'non_custodial'),
            (r'cảnh\s+cáo', 'warning'),
        ],
        LegalEntityType.DATE: [
            (r'ngày\s+(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', 'date'),
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', 'date'),
        ],
        LegalEntityType.AMOUNT: [
            (r'(\d{1,3}(?:\.\d{3})*)\s*(?:đồng|VND|VNĐ)', 'currency'),
            (r'(\d+(?:,\d+)?)\s*%', 'percentage'),
        ],
        LegalEntityType.GOVERNMENT_BODY: [
            (r'Quốc\s+hội', 'gov_body'),
            (r'Chính\s+phủ', 'gov_body'),
            (r'Bộ\s+[A-ZĐÀÁẢÃẠÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]+', 'gov_body'),
            (r'Ủy\s+ban\s+[A-Z][a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]+', 'gov_body'),
        ],
    }

    def extract(self, text: str) -> List[LegalEntity]:
        """Extract entities using pattern matching."""
        entities = []

        for entity_type, patterns in self.PATTERNS.items():
            for pattern, subtype in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
                    entity = LegalEntity(
                        text=match.group(0),
                        entity_type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.95,  # High confidence for pattern matches
                        metadata={'subtype': subtype, 'groups': match.groups()}
                    )

                    # Parse penalty details
                    if entity_type == LegalEntityType.PENALTY:
                        entity.penalty_type = subtype
                        if match.groups():
                            entity.penalty_value = match.group(1)

                    entities.append(entity)

        return entities
```

### Step 4: Create Cross-Reference Detector (1.5h)

Create `semantica/legal/crossref_detector.py`:

```python
import re
from typing import List, Optional, Tuple
from .entity_types import CrossReference

class CrossReferenceDetector:
    """Detect and parse cross-references in Vietnamese legal text."""

    # Reference patterns with named groups
    PATTERNS = [
        # "theo Điều X Luật số Y"
        (
            r'(?:theo|căn\s+cứ|quy\s+định\s+tại)\s+'
            r'Điều\s+(?P<article>\d+)'
            r'(?:,?\s*Khoản\s+(?P<clause>\d+))?'
            r'(?:,?\s*Điểm\s+(?P<point>[a-zđ]))?'
            r'(?:\s+Luật\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Z0-9]+))?',
            'references'
        ),
        # "được sửa đổi, bổ sung bởi Điều X"
        (
            r'(?:được\s+)?(?:sửa\s+đổi|bổ\s+sung)\s+(?:bởi|theo)\s+'
            r'Điều\s+(?P<article>\d+)'
            r'(?:\s+Luật\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Z0-9]+))?',
            'amends'
        ),
        # "thay thế cho Điều X"
        (
            r'thay\s+thế\s+(?:cho\s+)?'
            r'Điều\s+(?P<article>\d+)'
            r'(?:\s+Luật\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Z0-9]+))?',
            'supersedes'
        ),
        # Simple "Điều X" reference (lower confidence)
        (
            r'(?<!^)Điều\s+(?P<article>\d+)(?!\s*[:\.])',
            'references'
        ),
    ]

    def detect(
        self,
        text: str,
        source_article_id: str,
        current_law_number: Optional[str] = None
    ) -> List[CrossReference]:
        """
        Detect cross-references in clause text.

        Args:
            text: Clause or article text to analyze
            source_article_id: ID of source article
            current_law_number: Current document's law number (for context)

        Returns:
            List of detected cross-references
        """
        references = []
        seen_positions = set()

        for pattern, ref_type in self.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
                # Skip if overlapping with previous match
                if any(match.start() < end and match.end() > start
                       for start, end in seen_positions):
                    continue

                seen_positions.add((match.start(), match.end()))

                # Extract named groups
                groups = match.groupdict()
                article_num = int(groups.get('article', 0))
                law_number = groups.get('law') or current_law_number

                # Confidence based on pattern specificity
                confidence = 0.95 if groups.get('law') else 0.80

                ref = CrossReference(
                    source_article_id=source_article_id,
                    target_article_num=article_num,
                    target_law_number=law_number,
                    reference_text=match.group(0),
                    reference_type=ref_type,
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                references.append(ref)

        return references

    def resolve_reference(
        self,
        ref: CrossReference,
        db_manager  # LegalDocumentDB instance
    ) -> Optional[str]:
        """
        Resolve cross-reference to target article ID in database.

        Args:
            ref: CrossReference to resolve
            db_manager: Database manager instance

        Returns:
            UUID of target article if found, None otherwise
        """
        # Query database for matching article
        if ref.target_law_number:
            return db_manager.find_article(
                document_number=ref.target_law_number,
                article_number=ref.target_article_num
            )
        else:
            # Same document reference
            return db_manager.find_article_in_document(
                document_id=ref.source_article_id.split('/')[0],
                article_number=ref.target_article_num
            )
```

### Step 5: Create Main NER Extractor (1.5h)

Create `semantica/legal/ner_extractor.py`:

```python
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

from semantica.semantic_extract import NERExtractor as BaseNERExtractor
from semantica.utils.logging import get_logger

from .entity_types import LegalEntity, LegalEntityType, CrossReference
from .vn_preprocessor import VietnamesePreprocessor
from .pattern_ner import PatternNER
from .crossref_detector import CrossReferenceDetector

@dataclass
class ExtractionResult:
    """Result of legal entity extraction."""
    entities: List[LegalEntity]
    cross_references: List[CrossReference]
    metadata: Dict

class LegalNERExtractor:
    """
    Vietnamese legal NER extractor.

    Combines pattern-based and ML-based extraction for legal entities.

    Example:
        >>> extractor = LegalNERExtractor()
        >>> result = extractor.extract(
        ...     "Theo Điều 5 Luật số 20/2014/QH13, phạt tiền từ 50.000.000 đồng"
        ... )
        >>> print(result.entities)  # [LegalEntity(LEGISLATION), LegalEntity(PENALTY)]
        >>> print(result.cross_references)  # [CrossReference(article=5, law='20/2014/QH13')]
    """

    def __init__(
        self,
        use_ml: bool = False,
        ml_model: Optional[str] = None,
        confidence_threshold: float = 0.7
    ):
        self.logger = get_logger("legal_ner")
        self.preprocessor = VietnamesePreprocessor()
        self.pattern_ner = PatternNER()
        self.crossref_detector = CrossReferenceDetector()
        self.confidence_threshold = confidence_threshold

        # Optional ML-based NER
        self.use_ml = use_ml
        if use_ml:
            try:
                self.ml_ner = BaseNERExtractor(method="ml", model=ml_model or "vi_core_news_sm")
            except Exception as e:
                self.logger.warning(f"ML NER unavailable: {e}, using pattern-only")
                self.use_ml = False

    def extract(
        self,
        text: str,
        source_article_id: Optional[str] = None,
        current_law_number: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract legal entities and cross-references from text.

        Args:
            text: Input text (clause or article content)
            source_article_id: ID of source article for cross-references
            current_law_number: Current document's law number

        Returns:
            ExtractionResult with entities and cross-references
        """
        # Preprocess
        processed_text = self.preprocessor.preprocess(text)

        # Pattern-based extraction
        entities = self.pattern_ner.extract(processed_text)

        # ML-based extraction (if enabled)
        if self.use_ml:
            ml_entities = self._extract_ml(processed_text)
            entities = self._merge_entities(entities, ml_entities)

        # Cross-reference detection
        cross_refs = []
        if source_article_id:
            cross_refs = self.crossref_detector.detect(
                processed_text,
                source_article_id,
                current_law_number
            )

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= self.confidence_threshold]
        cross_refs = [r for r in cross_refs if r.confidence >= self.confidence_threshold]

        return ExtractionResult(
            entities=entities,
            cross_references=cross_refs,
            metadata={
                'text_length': len(text),
                'entity_count': len(entities),
                'crossref_count': len(cross_refs)
            }
        )

    def extract_batch(
        self,
        clauses: List[Dict],  # List of {id, text, article_id, law_number}
    ) -> List[ExtractionResult]:
        """Extract from multiple clauses in batch."""
        results = []
        for clause in clauses:
            result = self.extract(
                text=clause['text'],
                source_article_id=clause.get('article_id'),
                current_law_number=clause.get('law_number')
            )
            results.append(result)
        return results

    def _extract_ml(self, text: str) -> List[LegalEntity]:
        """Extract using ML model."""
        # Use Semantica's NERExtractor
        raw_entities = self.ml_ner.extract(text)
        return self._convert_entities(raw_entities)

    def _convert_entities(self, raw_entities: List) -> List[LegalEntity]:
        """Convert Semantica entities to LegalEntity format."""
        converted = []
        type_mapping = {
            'ORG': LegalEntityType.PARTY,
            'PER': LegalEntityType.PARTY,
            'LOC': LegalEntityType.PARTY,
            'DATE': LegalEntityType.DATE,
            'MONEY': LegalEntityType.AMOUNT,
        }
        for entity in raw_entities:
            entity_type = type_mapping.get(entity.get('label'), LegalEntityType.PARTY)
            converted.append(LegalEntity(
                text=entity.get('text', ''),
                entity_type=entity_type,
                start_pos=entity.get('start', 0),
                end_pos=entity.get('end', 0),
                confidence=entity.get('confidence', 0.8),
            ))
        return converted

    def _merge_entities(
        self,
        pattern_entities: List[LegalEntity],
        ml_entities: List[LegalEntity]
    ) -> List[LegalEntity]:
        """Merge pattern and ML entities, preferring pattern for legal types."""
        merged = list(pattern_entities)
        pattern_spans = {(e.start_pos, e.end_pos) for e in pattern_entities}

        for ml_entity in ml_entities:
            # Skip if overlaps with pattern entity
            if any(self._overlaps(ml_entity, pe) for pe in pattern_entities):
                continue
            merged.append(ml_entity)

        return sorted(merged, key=lambda e: e.start_pos)

    def _overlaps(self, e1: LegalEntity, e2: LegalEntity) -> bool:
        """Check if two entities overlap."""
        return e1.start_pos < e2.end_pos and e1.end_pos > e2.start_pos
```

## Todo List (Simplified)

- [x] Create `semantica/legal/crossref_detector.py`
- [x] Detect patterns: "theo Điều X", "căn cứ Điều Y", "quy định tại Điều Z"
- [x] Extract article/clause/point numbers from references
- [x] Resolve references to target articles in database
- [x] Store cross-references with confidence scores
- [x] Test with 10 legal documents (168 refs detected, 132 resolved)
- [ ] ~~Create NER pipeline~~ → Deferred (YAGNI)
- [ ] ~~Measure F1 scores~~ → Deferred (no annotated test set)

## Success Criteria (Simplified)

- [x] Cross-reference detection works for common patterns
- [x] "theo Điều X Luật Y" patterns parsed accurately
- [x] References stored in `legal_cross_references` table
- [x] Resolution rate: 78.5% (132/168 resolved)
- [ ] ~~Pattern NER extracts LEGISLATION, PENALTY~~ → Deferred
- [ ] ~~Entity confidence scores meaningful~~ → Deferred

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Vietnamese NLP tool unavailable | Medium | High | Fallback to pattern-only |
| Ambiguous cross-references | High | Medium | Use document context |
| Pattern coverage gaps | Medium | Medium | Iterative pattern improvement |
| False positives from patterns | Medium | Low | Confidence thresholds |

## Security Considerations

- Validate extracted entity values before DB storage
- Sanitize text input for regex injection
- Limit text length for DoS prevention

## Next Steps

After completing Phase 03:
1. Proceed to Phase 04: Legal KG & Ontology
2. Use extracted entities as KG nodes
3. Cross-references become KG edges
