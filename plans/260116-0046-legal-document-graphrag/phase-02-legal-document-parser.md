# Phase 02: Legal Document Parser

## Context Links

- [Research: VN Legal Structure](./research/researcher-01-vn-legal-structure.md)
- [Phase 01: Database](./phase-01-legal-document-database.md)
- [Main Plan](./plan.md)

## Overview

Build custom parser for Vietnamese legal documents. Uses regex patterns to extract hierarchical structure (Điều/Khoản/Điểm), integrates with Semantica's DoclingParser for PDF/DOCX text extraction, and stores results in Phase 01 database schema.

## Key Insights (from Research)

- **Regex patterns**: `^Điều\s+(\d+)[:\.\s](.+)$` for articles
- **Clause markers**: `^\s*(\d+)\)\s+(.+)$`
- **Point markers**: `^\s*([a-z])\)\s+(.+)$`
- **Two-pass approach**: Structure first, content second
- **Vietnamese NLP**: underthesea for tokenization

## Requirements

### Functional

- FR-01: Parse PDF/DOCX using DoclingParser for text extraction
- FR-02: Extract document metadata (title, issuing authority, effective date)
- FR-03: Detect chapter boundaries (Chương I, Chương II, ...)
- FR-04: Detect article boundaries (Điều 1., Điều 2., ...)
- FR-05: Extract clause/point nesting (1), 2), a), b))
- FR-06: Output hierarchical dict matching database schema
- FR-07: Preserve original text for each structural element

### Non-Functional

- NFR-01: Parse 50-page law in <10s
- NFR-02: 95%+ accuracy on standard Vietnamese legal format
- NFR-03: Graceful degradation for non-standard formatting
- NFR-04: Logging for parse errors with line numbers

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LegalDocumentParser                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PDF/DOCX ──→ DoclingParser ──→ Raw Text                            │
│                                     │                                │
│                                     ↓                                │
│                          ┌──────────────────────┐                   │
│                          │ MetadataExtractor    │                   │
│                          │ - Title              │                   │
│                          │ - Document number    │                   │
│                          │ - Effective date     │                   │
│                          │ - Issuing authority  │                   │
│                          └──────────┬───────────┘                   │
│                                     ↓                                │
│                          ┌──────────────────────┐                   │
│                          │ StructureParser      │                   │
│                          │ (Pass 1 - Headers)   │                   │
│                          │ - Chương patterns    │                   │
│                          │ - Điều patterns      │                   │
│                          └──────────┬───────────┘                   │
│                                     ↓                                │
│                          ┌──────────────────────┐                   │
│                          │ ContentParser        │                   │
│                          │ (Pass 2 - Content)   │                   │
│                          │ - Khoản patterns     │                   │
│                          │ - Điểm patterns      │                   │
│                          └──────────┬───────────┘                   │
│                                     ↓                                │
│                          ┌──────────────────────┐                   │
│                          │ HierarchyBuilder     │                   │
│                          │ - Nest clauses/points│                   │
│                          │ - Validate structure │                   │
│                          │ - Output dict        │                   │
│                          └──────────────────────┘                   │
│                                     │                                │
│                                     ↓                                │
│                          Dict → LegalDocumentDB.store_document()    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

- `/Users/hienlh/Projects/semantica/semantica/parse/__init__.py` - Parse module
- `/Users/hienlh/Projects/semantica/semantica/parse/docling_parser.py` - DoclingParser
- `/Users/hienlh/Projects/semantica/semantica/parse/document_parser.py` - DocumentParser
- `/Users/hienlh/Projects/semantica/semantica/split/__init__.py` - TextSplitter

## Implementation Steps

### Step 1: Create Regex Patterns Module (1h)

Create `semantica/legal/patterns.py`:

```python
import re
from typing import Pattern, Dict

class LegalPatterns:
    """Vietnamese legal document regex patterns."""

    # Document metadata
    DOCUMENT_NUMBER = re.compile(
        r'Luật\s+số[:\s]*(\d+/\d{4}/[A-Z0-9]+)',
        re.IGNORECASE | re.UNICODE
    )
    EFFECTIVE_DATE = re.compile(
        r'(?:có\s+hiệu\s+lực\s+(?:từ\s+)?(?:ngày\s+)?|hiệu\s+lực\s+thi\s+hành\s+từ\s+ngày\s+)'
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
        re.IGNORECASE | re.UNICODE
    )

    # Structure patterns
    CHAPTER = re.compile(
        r'^Chương\s+([IVXLC]+|\d+)[:\.\s]+(.+?)$',
        re.MULTILINE | re.UNICODE
    )
    SECTION = re.compile(
        r'^Mục\s+(\d+)[:\.\s]+(.+?)$',
        re.MULTILINE | re.UNICODE
    )
    ARTICLE = re.compile(
        r'^Điều\s+(\d+)[:\.\s]+(.+?)$',
        re.MULTILINE | re.UNICODE
    )

    # Content patterns
    CLAUSE = re.compile(
        r'^\s*(\d+)\)\s+(.+)$',
        re.MULTILINE | re.UNICODE
    )
    POINT = re.compile(
        r'^\s*([a-zđ])\)\s+(.+)$',
        re.MULTILINE | re.UNICODE
    )

    # Cross-reference patterns
    CROSS_REF_ARTICLE = re.compile(
        r'(?:theo|quy\s+định\s+tại|căn\s+cứ)\s+Điều\s+(\d+)',
        re.IGNORECASE | re.UNICODE
    )
    CROSS_REF_LAW = re.compile(
        r'Luật\s+(?:số\s+)?(\d+/\d{4}/[A-Z0-9]+)',
        re.IGNORECASE | re.UNICODE
    )

    @classmethod
    def roman_to_int(cls, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = values.get(char, 0)
            result += curr if curr >= prev else -curr
            prev = curr
        return result
```

### Step 2: Create Metadata Extractor (1h)

Create `semantica/legal/metadata_extractor.py`:

```python
from dataclasses import dataclass
from datetime import date
from typing import Optional
from .patterns import LegalPatterns

@dataclass
class LegalMetadata:
    title: str
    document_number: Optional[str] = None
    document_type: str = 'law'  # law, decree, decision, circular
    issuing_authority: Optional[str] = None
    effective_date: Optional[date] = None

class MetadataExtractor:
    """Extract metadata from legal document header."""

    def __init__(self):
        self.patterns = LegalPatterns

    def extract(self, text: str) -> LegalMetadata:
        """Extract metadata from first ~1000 chars of document."""
        header = text[:2000]

        # Extract document number
        doc_match = self.patterns.DOCUMENT_NUMBER.search(header)
        doc_number = doc_match.group(1) if doc_match else None

        # Extract effective date
        date_match = self.patterns.EFFECTIVE_DATE.search(text)
        eff_date = None
        if date_match:
            day, month, year = date_match.groups()
            eff_date = date(int(year), int(month), int(day))

        # Extract title (first significant line)
        title = self._extract_title(header)

        # Detect document type
        doc_type = self._detect_type(header)

        return LegalMetadata(
            title=title,
            document_number=doc_number,
            document_type=doc_type,
            effective_date=eff_date
        )

    def _extract_title(self, header: str) -> str:
        """Extract document title from header."""
        lines = header.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 20:
                return line
        return "Unknown Legal Document"

    def _detect_type(self, header: str) -> str:
        """Detect document type from keywords."""
        header_lower = header.lower()
        if 'luật' in header_lower:
            return 'law'
        elif 'nghị định' in header_lower:
            return 'decree'
        elif 'quyết định' in header_lower:
            return 'decision'
        elif 'thông tư' in header_lower:
            return 'circular'
        return 'law'
```

### Step 3: Create Structure Parser (2h)

Create `semantica/legal/structure_parser.py`:

```python
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from .patterns import LegalPatterns

@dataclass
class ParsedArticle:
    number: int
    title: str
    text: str
    start_pos: int
    end_pos: int
    clauses: List['ParsedClause'] = field(default_factory=list)

@dataclass
class ParsedClause:
    number: int
    text: str
    points: List['ParsedPoint'] = field(default_factory=list)

@dataclass
class ParsedPoint:
    letter: str
    text: str

class StructureParser:
    """Parse hierarchical structure from Vietnamese legal text."""

    def __init__(self):
        self.patterns = LegalPatterns

    def parse(self, text: str) -> Dict:
        """Parse full document structure."""
        chapters = self._extract_chapters(text)
        if not chapters:
            # Document without chapters - all articles at root
            articles = self._extract_articles(text)
            return {'chapters': [{'number': 0, 'title': 'Main', 'articles': articles}]}
        return {'chapters': chapters}

    def _extract_chapters(self, text: str) -> List[Dict]:
        """Extract chapter boundaries."""
        matches = list(self.patterns.CHAPTER.finditer(text))
        chapters = []

        for i, match in enumerate(matches):
            chapter_num = match.group(1)
            if chapter_num.isdigit():
                num = int(chapter_num)
            else:
                num = self.patterns.roman_to_int(chapter_num)

            # Get text until next chapter or end
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chapter_text = text[start:end]

            articles = self._extract_articles(chapter_text)

            chapters.append({
                'number': num,
                'title': match.group(2).strip(),
                'articles': articles
            })

        return chapters

    def _extract_articles(self, text: str) -> List[Dict]:
        """Extract articles and their clauses."""
        matches = list(self.patterns.ARTICLE.finditer(text))
        articles = []

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            article_text = text[start:end].strip()

            clauses = self._extract_clauses(article_text)

            articles.append({
                'number': int(match.group(1)),
                'title': match.group(2).strip(),
                'full_text': article_text,
                'clauses': clauses
            })

        return articles

    def _extract_clauses(self, article_text: str) -> List[Dict]:
        """Extract clauses and their points."""
        matches = list(self.patterns.CLAUSE.finditer(article_text))
        if not matches:
            return []

        clauses = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(article_text)
            clause_text = article_text[start:end].strip()

            # Remove clause number prefix for clean text
            text_content = self.patterns.CLAUSE.sub(r'\2', clause_text, count=1)
            points = self._extract_points(clause_text)

            clauses.append({
                'number': int(match.group(1)),
                'text': text_content.strip(),
                'points': points
            })

        return clauses

    def _extract_points(self, clause_text: str) -> List[Dict]:
        """Extract points within a clause."""
        matches = list(self.patterns.POINT.finditer(clause_text))
        points = []

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(clause_text)
            point_text = clause_text[start:end].strip()

            points.append({
                'letter': match.group(1),
                'text': match.group(2).strip() + ' ' + point_text
            })

        return points
```

### Step 4: Create Main Parser Class (2h)

Create `semantica/legal/parser.py`:

```python
from typing import Dict, Optional, Union
from pathlib import Path
import uuid

from semantica.parse import DoclingParser, DocumentParser
from semantica.utils.logging import get_logger

from .patterns import LegalPatterns
from .metadata_extractor import MetadataExtractor, LegalMetadata
from .structure_parser import StructureParser
from .db_manager import LegalDocumentDB

class LegalDocumentParser:
    """
    Main parser for Vietnamese legal documents.

    Extracts hierarchical structure and stores in database.

    Example:
        >>> parser = LegalDocumentParser(db_connection="postgresql://...")
        >>> doc_id = parser.parse_and_store("path/to/law.pdf")
    """

    def __init__(
        self,
        db_connection: Optional[str] = None,
        use_docling: bool = True
    ):
        self.logger = get_logger("legal_parser")
        self.metadata_extractor = MetadataExtractor()
        self.structure_parser = StructureParser()

        # Initialize text extractor
        if use_docling:
            try:
                self.text_extractor = DoclingParser(enable_ocr=True)
            except ImportError:
                self.logger.warning("Docling not available, using DocumentParser")
                self.text_extractor = DocumentParser()
        else:
            self.text_extractor = DocumentParser()

        # Initialize DB if connection provided
        self.db = LegalDocumentDB(db_connection) if db_connection else None

    def parse(self, file_path: Union[str, Path]) -> Dict:
        """
        Parse legal document and return hierarchical structure.

        Args:
            file_path: Path to PDF or DOCX file

        Returns:
            Dict with structure: {metadata: {...}, chapters: [...]}
        """
        file_path = Path(file_path)
        self.logger.info(f"Parsing legal document: {file_path.name}")

        # Extract raw text
        result = self.text_extractor.parse(str(file_path))
        text = result.get('full_text', result.get('text', ''))

        # Extract metadata
        metadata = self.metadata_extractor.extract(text)

        # Parse structure
        structure = self.structure_parser.parse(text)

        return {
            'id': str(uuid.uuid4()),
            'metadata': {
                'title': metadata.title,
                'document_number': metadata.document_number,
                'document_type': metadata.document_type,
                'issuing_authority': metadata.issuing_authority,
                'effective_date': metadata.effective_date.isoformat() if metadata.effective_date else None,
            },
            'source_file': str(file_path),
            **structure
        }

    def parse_and_store(self, file_path: Union[str, Path]) -> uuid.UUID:
        """
        Parse legal document and store in database.

        Args:
            file_path: Path to PDF or DOCX file

        Returns:
            UUID of stored document
        """
        if not self.db:
            raise ValueError("Database connection required for parse_and_store")

        parsed = self.parse(file_path)
        return self.db.store_document(parsed)

    def parse_text(self, text: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Parse legal document from raw text.

        Args:
            text: Raw text content
            metadata: Optional metadata dict

        Returns:
            Parsed structure dict
        """
        extracted_metadata = self.metadata_extractor.extract(text)
        structure = self.structure_parser.parse(text)

        # Merge provided metadata
        if metadata:
            extracted_metadata = LegalMetadata(
                title=metadata.get('title', extracted_metadata.title),
                document_number=metadata.get('document_number', extracted_metadata.document_number),
                document_type=metadata.get('document_type', extracted_metadata.document_type),
                effective_date=metadata.get('effective_date', extracted_metadata.effective_date),
            )

        return {
            'id': str(uuid.uuid4()),
            'metadata': {
                'title': extracted_metadata.title,
                'document_number': extracted_metadata.document_number,
                'document_type': extracted_metadata.document_type,
                'effective_date': extracted_metadata.effective_date.isoformat() if extracted_metadata.effective_date else None,
            },
            **structure
        }
```

### Step 5: Add Validation & Error Handling (1h)

Create `semantica/legal/validation.py`:

```python
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ParseError:
    line_number: int
    message: str
    severity: str  # 'warning', 'error'

class StructureValidator:
    """Validate parsed legal document structure."""

    def validate(self, parsed: Dict) -> Tuple[bool, List[ParseError]]:
        """Validate structure completeness and consistency."""
        errors = []

        # Check metadata
        if not parsed.get('metadata', {}).get('title'):
            errors.append(ParseError(0, "Missing document title", "warning"))

        # Check chapters
        chapters = parsed.get('chapters', [])
        if not chapters:
            errors.append(ParseError(0, "No chapters found", "warning"))

        # Check article numbering
        for chapter in chapters:
            articles = chapter.get('articles', [])
            if not articles:
                errors.append(ParseError(
                    0, f"Chapter {chapter.get('number')} has no articles", "warning"
                ))

            # Check sequential numbering
            numbers = [a.get('number') for a in articles]
            expected = list(range(numbers[0], numbers[0] + len(numbers))) if numbers else []
            if numbers != expected:
                errors.append(ParseError(
                    0, f"Non-sequential article numbering in chapter {chapter.get('number')}", "warning"
                ))

        is_valid = not any(e.severity == 'error' for e in errors)
        return is_valid, errors
```

### Step 6: Create Integration Tests (1h)

Create `tests/legal/test_parser.py`:

```python
import pytest
from semantica.legal.parser import LegalDocumentParser
from semantica.legal.patterns import LegalPatterns

SAMPLE_LAW_TEXT = """
QUỐC HỘI
LUẬT SỐ 20/2014/QH13

LUẬT BẢO HIỂM XÃ HỘI

Chương I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định chế độ, chính sách bảo hiểm xã hội.
1) Bảo hiểm xã hội bắt buộc;
2) Bảo hiểm xã hội tự nguyện;
a) Đối tượng tham gia;
b) Mức đóng và phương thức đóng.

Điều 2. Đối tượng áp dụng
1) Người lao động;
2) Người sử dụng lao động.
"""

def test_chapter_extraction():
    parser = LegalDocumentParser(db_connection=None)
    result = parser.parse_text(SAMPLE_LAW_TEXT)
    assert len(result['chapters']) == 1
    assert result['chapters'][0]['number'] == 1
    assert 'QUY ĐỊNH CHUNG' in result['chapters'][0]['title']

def test_article_extraction():
    parser = LegalDocumentParser(db_connection=None)
    result = parser.parse_text(SAMPLE_LAW_TEXT)
    articles = result['chapters'][0]['articles']
    assert len(articles) == 2
    assert articles[0]['number'] == 1
    assert articles[1]['number'] == 2

def test_clause_extraction():
    parser = LegalDocumentParser(db_connection=None)
    result = parser.parse_text(SAMPLE_LAW_TEXT)
    clauses = result['chapters'][0]['articles'][0]['clauses']
    assert len(clauses) == 2
    assert clauses[0]['number'] == 1
    assert clauses[1]['number'] == 2

def test_point_extraction():
    parser = LegalDocumentParser(db_connection=None)
    result = parser.parse_text(SAMPLE_LAW_TEXT)
    points = result['chapters'][0]['articles'][0]['clauses'][1]['points']
    assert len(points) == 2
    assert points[0]['letter'] == 'a'
    assert points[1]['letter'] == 'b'

def test_metadata_extraction():
    parser = LegalDocumentParser(db_connection=None)
    result = parser.parse_text(SAMPLE_LAW_TEXT)
    assert result['metadata']['document_number'] == '20/2014/QH13'
    assert result['metadata']['document_type'] == 'law'
```

## Todo List

- [ ] Create `semantica/legal/patterns.py` with regex patterns
- [ ] Create `semantica/legal/metadata_extractor.py`
- [ ] Create `semantica/legal/structure_parser.py`
- [ ] Create `semantica/legal/parser.py` main class
- [ ] Create `semantica/legal/validation.py`
- [ ] Integration with Phase 01 database
- [ ] Write unit tests with sample Vietnamese law
- [ ] Test with 5+ real Vietnamese law PDFs
- [ ] Handle edge cases (missing chapters, non-standard formats)

## Success Criteria

- [ ] Parse sample law with correct chapter/article/clause counts
- [ ] Metadata extraction works for 95% of laws
- [ ] Article numbering preserved correctly
- [ ] Clause/point nesting accurate
- [ ] Integration tests pass with real PDFs

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Non-standard formatting | High | Medium | Fallback patterns, logging |
| OCR errors in scanned PDFs | Medium | High | DoclingParser OCR, manual review |
| Multi-paragraph clauses | Medium | Medium | Track via line breaks |
| Unicode handling | Low | Medium | Use re.UNICODE flag |

## Security Considerations

- Validate file paths before processing
- Sanitize extracted text before DB storage
- Limit file size to prevent DoS

## Next Steps

After completing Phase 02:
1. Proceed to Phase 03: Legal Entity Extraction
2. NER will use parsed clause text as input
3. Cross-reference detector uses article text
