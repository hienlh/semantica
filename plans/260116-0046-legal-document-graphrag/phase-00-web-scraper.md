# Phase 00: Web Scraper (thuvienphapluat.vn)

## Context Links

- [Main Plan](./plan.md)
- [Phase 01: Database](./phase-01-legal-document-database.md)

## Overview

Build Playwright-based web scraper for Vietnamese legal document websites. Primary target: thuvienphapluat.vn. Extract hierarchical structure (Chương > Điều > Khoản > Điểm) và metadata.

**Priority:** P1
**Effort:** 4h
**Status:** ✅ Completed

## Key Insights

- thuvienphapluat.vn có anti-scraping (403 với direct fetch)
- Cần headless browser (Playwright) để bypass
- HTML structure: `#toanvancontent` chứa nội dung chính
- Metadata trong `.doc-info`, `.thuoc-tinh`

## Requirements

### Functional

- FR-01: Scrape document từ URL thuvienphapluat.vn
- FR-02: Extract metadata (số hiệu, ngày ban hành, cơ quan ban hành)
- FR-03: Parse hierarchical structure (Chương/Mục/Điều/Khoản/Điểm)
- FR-04: Handle pagination nếu có
- FR-05: Rate limiting để tránh bị block
- FR-06: Retry logic cho failed requests

### Non-Functional

- NFR-01: Scrape 1 document trong <10s
- NFR-02: Success rate >95%
- NFR-03: Respect robots.txt và rate limits

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LegalWebScraper                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  URL ──→ ┌──────────────────────────────────────────────┐   │
│          │ PlaywrightFetcher                             │   │
│          │ - Headless Chromium                           │   │
│          │ - Custom User-Agent                           │   │
│          │ - Wait for networkidle                        │   │
│          └───────────────────┬──────────────────────────┘   │
│                              ↓                               │
│          ┌──────────────────────────────────────────────┐   │
│          │ TVPLParser (thuvienphapluat.vn specific)      │   │
│          │ - Extract metadata (#thuoc-tinh)              │   │
│          │ - Parse content (#toanvancontent)             │   │
│          │ - Build hierarchy tree                        │   │
│          └───────────────────┬──────────────────────────┘   │
│                              ↓                               │
│          ┌──────────────────────────────────────────────┐   │
│          │ HierarchyExtractor                            │   │
│          │ - Regex patterns cho Chương/Điều/Khoản/Điểm   │   │
│          │ - Build nested structure                      │   │
│          │ - Validate completeness                       │   │
│          └───────────────────┬──────────────────────────┘   │
│                              ↓                               │
│  Output: LegalDocument (JSON) → Phase 01 Database            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Related Code Files

### New Files to Create

- `/Users/hienlh/Projects/semantica/semantica/legal/__init__.py`
- `/Users/hienlh/Projects/semantica/semantica/legal/scraper/__init__.py`
- `/Users/hienlh/Projects/semantica/semantica/legal/scraper/base.py`
- `/Users/hienlh/Projects/semantica/semantica/legal/scraper/tvpl.py`
- `/Users/hienlh/Projects/semantica/semantica/legal/scraper/hierarchy_extractor.py`

### Existing Files to Reference

- `/Users/hienlh/Projects/semantica/semantica/ingest/web_ingestor.py` - Reference implementation

## Implementation Steps

### Step 1: Setup Package Structure (0.5h)

```bash
mkdir -p semantica/legal/scraper
touch semantica/legal/__init__.py
touch semantica/legal/scraper/__init__.py
```

### Step 2: Create Base Scraper Class (0.5h)

Create `semantica/legal/scraper/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class LegalArticle:
    """Represents a single article (Điều)."""
    number: int
    title: str
    content: str
    clauses: List['LegalClause'] = field(default_factory=list)

@dataclass
class LegalClause:
    """Represents a clause (Khoản)."""
    number: int
    content: str
    points: List['LegalPoint'] = field(default_factory=list)

@dataclass
class LegalPoint:
    """Represents a point (Điểm)."""
    letter: str  # a, b, c, đ...
    content: str

@dataclass
class LegalChapter:
    """Represents a chapter (Chương)."""
    number: str  # Roman or Arabic
    title: str
    articles: List[LegalArticle] = field(default_factory=list)

@dataclass
class LegalDocument:
    """Complete legal document with hierarchy."""
    url: str
    so_hieu: str  # Document number
    title: str
    loai_van_ban: str  # Document type
    co_quan_ban_hanh: str  # Issuing authority
    nguoi_ky: str  # Signatory
    ngay_ban_hanh: Optional[datetime] = None
    ngay_hieu_luc: Optional[datetime] = None
    tinh_trang: str = ""  # Status
    chapters: List[LegalChapter] = field(default_factory=list)
    articles: List[LegalArticle] = field(default_factory=list)  # For docs without chapters
    raw_html: str = ""
    raw_text: str = ""
    metadata: Dict = field(default_factory=dict)

class BaseLegalScraper(ABC):
    """Base class for legal document scrapers."""

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Fetch HTML content from URL."""
        pass

    @abstractmethod
    def parse(self, html: str, url: str) -> LegalDocument:
        """Parse HTML into LegalDocument."""
        pass

    async def scrape(self, url: str) -> LegalDocument:
        """Fetch and parse a legal document."""
        html = await self.fetch(url)
        return self.parse(html, url)
```

### Step 3: Create TVPL Scraper (1.5h)

Create `semantica/legal/scraper/tvpl.py`:

```python
import asyncio
import re
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page
from .base import (
    BaseLegalScraper, LegalDocument, LegalChapter,
    LegalArticle, LegalClause, LegalPoint
)

class TVPLScraper(BaseLegalScraper):
    """Scraper for thuvienphapluat.vn"""

    SELECTORS = {
        'content': '#toanvancontent',
        'title': 'h1.title',
        'metadata': '.thuoc-tinh',
        'so_hieu': '.thuoc-tinh .so-hieu',
        'ngay_ban_hanh': '.thuoc-tinh .ngay-ban-hanh',
        'co_quan': '.thuoc-tinh .co-quan-ban-hanh',
    }

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._browser: Optional[Browser] = None

    async def fetch(self, url: str) -> str:
        """Fetch HTML using Playwright."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Wait for content to load
                await page.wait_for_selector(self.SELECTORS['content'], timeout=10000)

                return await page.content()
            finally:
                await browser.close()

    def parse(self, html: str, url: str) -> LegalDocument:
        """Parse TVPL HTML into LegalDocument."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Extract metadata
        doc = LegalDocument(
            url=url,
            so_hieu=self._extract_text(soup, '.so-hieu', ''),
            title=self._extract_text(soup, 'h1', ''),
            loai_van_ban=self._extract_text(soup, '.loai-van-ban', ''),
            co_quan_ban_hanh=self._extract_text(soup, '.co-quan-ban-hanh', ''),
            nguoi_ky=self._extract_text(soup, '.nguoi-ky', ''),
            raw_html=html
        )

        # Extract dates
        ngay_str = self._extract_text(soup, '.ngay-ban-hanh', '')
        if ngay_str:
            doc.ngay_ban_hanh = self._parse_date(ngay_str)

        # Extract content and build hierarchy
        content_el = soup.select_one(self.SELECTORS['content'])
        if content_el:
            doc.raw_text = content_el.get_text()
            doc.chapters, doc.articles = self._extract_hierarchy(doc.raw_text)

        return doc

    def _extract_text(self, soup, selector: str, default: str) -> str:
        """Extract text from selector."""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else default

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse Vietnamese date format."""
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                d, m, y = match.groups()
                return datetime(int(y), int(m), int(d))
        return None

    def _extract_hierarchy(self, text: str):
        """Extract hierarchical structure from text."""
        from .hierarchy_extractor import HierarchyExtractor
        extractor = HierarchyExtractor()
        return extractor.extract(text)
```

### Step 4: Create Hierarchy Extractor (1h)

Create `semantica/legal/scraper/hierarchy_extractor.py`:

```python
import re
from typing import List, Tuple
from .base import LegalChapter, LegalArticle, LegalClause, LegalPoint

class HierarchyExtractor:
    """Extract hierarchical structure from Vietnamese legal text."""

    PATTERNS = {
        'chapter': r'Chương\s+([IVXLC]+|\d+)[:\.\s]*([^\n]+)',
        'section': r'Mục\s+(\d+)[:\.\s]*([^\n]+)',
        'article': r'Điều\s+(\d+)[:\.\s]*([^\n]*)',
        'clause': r'^\s*(\d+)\.\s+',
        'point': r'^\s*([a-zđ])\)\s+',
    }

    def extract(self, text: str) -> Tuple[List[LegalChapter], List[LegalArticle]]:
        """
        Extract chapters and articles from legal text.

        Returns:
            Tuple of (chapters, standalone_articles)
        """
        chapters = []
        standalone_articles = []

        # Find all chapters
        chapter_matches = list(re.finditer(self.PATTERNS['chapter'], text))

        if chapter_matches:
            for i, match in enumerate(chapter_matches):
                # Get chapter content (until next chapter or end)
                start = match.end()
                end = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else len(text)
                chapter_text = text[start:end]

                chapter = LegalChapter(
                    number=match.group(1),
                    title=match.group(2).strip(),
                    articles=self._extract_articles(chapter_text)
                )
                chapters.append(chapter)
        else:
            # No chapters, extract articles directly
            standalone_articles = self._extract_articles(text)

        return chapters, standalone_articles

    def _extract_articles(self, text: str) -> List[LegalArticle]:
        """Extract articles from text segment."""
        articles = []
        article_matches = list(re.finditer(self.PATTERNS['article'], text))

        for i, match in enumerate(article_matches):
            start = match.end()
            end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(text)
            article_text = text[start:end].strip()

            article = LegalArticle(
                number=int(match.group(1)),
                title=match.group(2).strip() if match.group(2) else "",
                content=article_text,
                clauses=self._extract_clauses(article_text)
            )
            articles.append(article)

        return articles

    def _extract_clauses(self, text: str) -> List[LegalClause]:
        """Extract clauses (khoản) from article text."""
        clauses = []
        lines = text.split('\n')
        current_clause = None
        current_content = []

        for line in lines:
            clause_match = re.match(self.PATTERNS['clause'], line)
            if clause_match:
                # Save previous clause
                if current_clause is not None:
                    current_clause.content = '\n'.join(current_content).strip()
                    current_clause.points = self._extract_points(current_clause.content)
                    clauses.append(current_clause)

                # Start new clause
                current_clause = LegalClause(
                    number=int(clause_match.group(1)),
                    content=""
                )
                current_content = [line[clause_match.end():]]
            elif current_clause is not None:
                current_content.append(line)

        # Save last clause
        if current_clause is not None:
            current_clause.content = '\n'.join(current_content).strip()
            current_clause.points = self._extract_points(current_clause.content)
            clauses.append(current_clause)

        return clauses

    def _extract_points(self, text: str) -> List[LegalPoint]:
        """Extract points (điểm) from clause text."""
        points = []
        lines = text.split('\n')
        current_point = None
        current_content = []

        for line in lines:
            point_match = re.match(self.PATTERNS['point'], line)
            if point_match:
                if current_point is not None:
                    current_point.content = '\n'.join(current_content).strip()
                    points.append(current_point)

                current_point = LegalPoint(
                    letter=point_match.group(1),
                    content=""
                )
                current_content = [line[point_match.end():]]
            elif current_point is not None:
                current_content.append(line)

        if current_point is not None:
            current_point.content = '\n'.join(current_content).strip()
            points.append(current_point)

        return points
```

### Step 5: Create Package Exports (0.5h)

Update `semantica/legal/__init__.py`:

```python
from .scraper.base import (
    LegalDocument,
    LegalChapter,
    LegalArticle,
    LegalClause,
    LegalPoint,
    BaseLegalScraper
)
from .scraper.tvpl import TVPLScraper
from .scraper.hierarchy_extractor import HierarchyExtractor

__all__ = [
    'LegalDocument',
    'LegalChapter',
    'LegalArticle',
    'LegalClause',
    'LegalPoint',
    'BaseLegalScraper',
    'TVPLScraper',
    'HierarchyExtractor'
]
```

## Todo List

- [x] Create package structure `semantica/legal/scraper/`
- [x] Implement `base.py` với data classes
- [x] Implement `tvpl.py` với Playwright fetcher
- [x] Implement `hierarchy_extractor.py` với regex patterns
- [x] Add retry logic và rate limiting
- [x] Test với Luật Doanh nghiệp 2020
- [x] Test với Nghị định 01/2021/NĐ-CP
- [x] Test với 10 văn bản pháp luật (619 điều, 2,656 khoản)
- [x] Handle edge cases (documents without chapters)

## Success Criteria

- [x] Scrape Luật Doanh nghiệp 2020 successfully
- [x] Extract all 10 Chương, 218 Điều
- [x] Parse Khoản và Điểm correctly
- [x] Metadata extracted (số hiệu, ngày ban hành, etc.)
- [x] Output JSON validated against schema

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Website blocks scraper | Medium | High | Rotate user agents, add delays |
| HTML structure changes | Medium | Medium | Abstract selectors, add fallbacks |
| Playwright install issues | Low | Medium | Document setup steps |
| Rate limiting | Medium | Low | Configurable delays |

## Security Considerations

- Respect robots.txt (check before scraping)
- Rate limit requests (1-2 req/sec max)
- Don't store credentials in code
- Sanitize extracted content before DB storage

## Next Steps

After Phase 00:
1. → Phase 01: Store scraped data in PostgreSQL
2. Output format matches Phase 01 database schema
3. Add CLI command: `semantica legal scrape <url>`

## Usage Example

```python
import asyncio
from semantica.legal import TVPLScraper

async def main():
    scraper = TVPLScraper()

    # Scrape Luật Doanh nghiệp 2020
    doc = await scraper.scrape(
        "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Doanh-nghiep-so-59-2020-QH14-427301.aspx"
    )

    print(f"Title: {doc.title}")
    print(f"Số hiệu: {doc.so_hieu}")
    print(f"Chapters: {len(doc.chapters)}")

    for chapter in doc.chapters:
        print(f"  Chương {chapter.number}: {chapter.title}")
        print(f"    Articles: {len(chapter.articles)}")

asyncio.run(main())
```
