# Phase 01: Legal Document Database

## Context Links

- [Phase 00: Web Scraper](./phase-00-web-scraper.md) ← Input source
- [Research: VN Legal Structure](./research/researcher-01-vn-legal-structure.md)
- [Main Plan](./plan.md)

## Overview

Create PostgreSQL database schema for hierarchical Vietnamese legal document storage. Schema mirrors 6-level structure from Phase 00 scraper output: Document > Chapter > Section > Article > Clause > Point. Each level links to corresponding KG node via `kg_node_id`.

**Input:** `LegalDocument` from Phase 00 web scraper (`semantica.legal.scraper.base`)

## Key Insights (from Research)

- **Hierarchy**: Văn bản > Phần > Chương > Mục > Điều > Khoản > Điểm
- **Numbering**: Roman for chapters, Arabic for articles, letters for points
- **Storage**: Normalized tables + JSONB for full hierarchy
- **Independence**: Each Khoản (clause) forms complete sentence

## Requirements

### Functional

- FR-01: Store documents with metadata (title, type, issuing authority, effective date)
- FR-02: Store hierarchical structure (chapter → article → clause → point)
- FR-03: Link each structural element to KG node via `kg_node_id`
- FR-04: Support temporal versioning for amendments
- FR-05: Store raw text + parsed structure for each level
- FR-06: Query by article number, effective date, document type

### Non-Functional

- NFR-01: PostgreSQL 14+ with UUID support
- NFR-02: Indexes on document_id, article_number, effective_date
- NFR-03: JSONB column for flexible metadata storage
- NFR-04: Alembic migrations for schema versioning

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Phase 00 Web Scraper Output                         │
│  LegalDocument → LegalChapter → LegalSection → LegalArticle             │
│                                               → LegalClause → LegalPoint │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                              │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_documents                                                         │
│  ├── id (UUID PK)                                                        │
│  ├── so_hieu (VARCHAR) ← document number "59/2020/QH14"                 │
│  ├── title, loai_van_ban, co_quan_ban_hanh                              │
│  ├── ngay_ban_hanh, ngay_hieu_luc, tinh_trang                           │
│  ├── full_hierarchy (JSONB) ─────────────────────────────────────────────┼──→ Full parsed tree
│  ├── raw_text (TEXT)                                                     │
│  ├── kg_node_id (UUID) ──────────────────────────────────────────────────┼──→ Links to KG
│  └── source_url, created_at                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_chapters                                                          │
│  ├── id (UUID PK), document_id (FK)                                      │
│  ├── chapter_number (VARCHAR) ← Roman: "I", "II", "III"                  │
│  ├── title, raw_text                                                     │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_sections (Mục)                                                    │
│  ├── id (UUID PK), chapter_id (FK)                                       │
│  ├── section_number (INT), title, raw_text                              │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_articles                                                          │
│  ├── id (UUID PK), chapter_id (FK), section_id (FK, nullable)           │
│  ├── article_number (INT), title, content, raw_text                     │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_clauses                                                           │
│  ├── id (UUID PK), article_id (FK)                                       │
│  ├── clause_number (INT), content, raw_text                             │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_points                                                            │
│  ├── id (UUID PK), clause_id (FK)                                        │
│  ├── point_letter (VARCHAR) ← "a", "b", "đ"                             │
│  ├── content, raw_text                                                   │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  legal_cross_references (detected "theo Điều X Luật Y" links)            │
│  ├── id (UUID PK), source_article_id, target_article_id                 │
│  ├── reference_text, reference_type, confidence                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Phase 00 Input (Data Classes)
- `semantica/legal/scraper/base.py` - LegalDocument, LegalChapter, LegalSection, LegalArticle, LegalClause, LegalPoint

### Reference Implementation
- `semantica/kg/provenance_tracker.py` - Provenance pattern
- `semantica/ingest/db_ingestor.py` - DB ingestion pattern

## Implementation Steps

### Step 1: Create SQLAlchemy Models (2h)

Create `semantica/legal/models.py`:

```python
from sqlalchemy import Column, String, Text, Date, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class LegalDocumentModel(Base):
    """Maps to Phase 00: LegalDocument"""
    __tablename__ = 'legal_documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    so_hieu = Column(String(100), nullable=False, index=True)  # "59/2020/QH14"
    title = Column(String(500), nullable=False)
    loai_van_ban = Column(String(50))  # 'Luật', 'Nghị định', 'Thông tư'
    co_quan_ban_hanh = Column(String(200))
    nguoi_ky = Column(String(200))
    ngay_ban_hanh = Column(Date)
    ngay_hieu_luc = Column(Date)
    tinh_trang = Column(String(100))
    full_hierarchy = Column(JSON)  # Full parsed tree as JSONB
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    source_url = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapters = relationship("LegalChapterModel", back_populates="document", cascade="all, delete-orphan")
    articles = relationship("LegalArticleModel", back_populates="document", cascade="all, delete-orphan")

class LegalChapterModel(Base):
    """Maps to Phase 00: LegalChapter"""
    __tablename__ = 'legal_chapters'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('legal_documents.id'), nullable=False)
    chapter_number = Column(String(20), nullable=False)  # Roman: "I", "II", "III"
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    position = Column(Integer)

    document = relationship("LegalDocumentModel", back_populates="chapters")
    sections = relationship("LegalSectionModel", back_populates="chapter", cascade="all, delete-orphan")
    articles = relationship("LegalArticleModel", back_populates="chapter", cascade="all, delete-orphan")

class LegalSectionModel(Base):
    """Maps to Phase 00: LegalSection (Mục)"""
    __tablename__ = 'legal_sections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey('legal_chapters.id'), nullable=False)
    section_number = Column(Integer, nullable=False)
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    position = Column(Integer)

    chapter = relationship("LegalChapterModel", back_populates="sections")
    articles = relationship("LegalArticleModel", back_populates="section", cascade="all, delete-orphan")

class LegalArticleModel(Base):
    """Maps to Phase 00: LegalArticle"""
    __tablename__ = 'legal_articles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('legal_documents.id'))
    chapter_id = Column(UUID(as_uuid=True), ForeignKey('legal_chapters.id'), nullable=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey('legal_sections.id'), nullable=True)
    article_number = Column(Integer, nullable=False, index=True)
    title = Column(String(500))
    content = Column(Text)
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    position = Column(Integer)

    document = relationship("LegalDocumentModel", back_populates="articles")
    chapter = relationship("LegalChapterModel", back_populates="articles")
    section = relationship("LegalSectionModel", back_populates="articles")
    clauses = relationship("LegalClauseModel", back_populates="article", cascade="all, delete-orphan")

class LegalClauseModel(Base):
    """Maps to Phase 00: LegalClause"""
    __tablename__ = 'legal_clauses'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'), nullable=False)
    clause_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    position = Column(Integer)

    article = relationship("LegalArticleModel", back_populates="clauses")
    points = relationship("LegalPointModel", back_populates="clause", cascade="all, delete-orphan")

class LegalPointModel(Base):
    """Maps to Phase 00: LegalPoint"""
    __tablename__ = 'legal_points'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clause_id = Column(UUID(as_uuid=True), ForeignKey('legal_clauses.id'), nullable=False)
    point_letter = Column(String(5), nullable=False)  # "a", "b", "đ"
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True), index=True)
    position = Column(Integer)

    clause = relationship("LegalClauseModel", back_populates="points")

class LegalCrossReferenceModel(Base):
    """Store detected cross-references between articles"""
    __tablename__ = 'legal_cross_references'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'))
    target_article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'), nullable=True)
    target_document_id = Column(UUID(as_uuid=True), ForeignKey('legal_documents.id'), nullable=True)
    reference_text = Column(Text)  # "theo Điều 5 Luật 20/2014"
    reference_type = Column(String(50))  # 'references', 'amends', 'supersedes'
    confidence = Column(Float, default=1.0)
```

### Step 2: Create Alembic Migration (1h)

```bash
# Initialize alembic in semantica/legal/
alembic init alembic
# Create migration
alembic revision --autogenerate -m "create_legal_document_tables"
```

### Step 3: Create Database Manager (2h)

Create `semantica/legal/db_manager.py`:

```python
from typing import Optional, List
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from semantica.legal.scraper.base import LegalDocument as ScrapedDocument
from semantica.legal.models import (
    LegalDocumentModel, LegalChapterModel, LegalSectionModel,
    LegalArticleModel, LegalClauseModel, LegalPointModel
)

class LegalDocumentDB:
    """Database manager for legal document storage."""

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def store_from_scraper(self, scraped_doc: ScrapedDocument) -> UUID:
        """
        Store Phase 00 scraper output to database.

        Args:
            scraped_doc: LegalDocument from semantica.legal.scraper.base

        Returns:
            UUID of stored document
        """
        with self.Session() as session:
            # Create document
            doc = LegalDocumentModel(
                so_hieu=scraped_doc.so_hieu,
                title=scraped_doc.title,
                loai_van_ban=scraped_doc.loai_van_ban,
                co_quan_ban_hanh=scraped_doc.co_quan_ban_hanh,
                nguoi_ky=scraped_doc.nguoi_ky,
                ngay_ban_hanh=scraped_doc.ngay_ban_hanh,
                ngay_hieu_luc=scraped_doc.ngay_hieu_luc,
                tinh_trang=scraped_doc.tinh_trang,
                raw_text=scraped_doc.raw_text,
                source_url=scraped_doc.url,
                metadata=scraped_doc.metadata,
                full_hierarchy=scraped_doc.to_dict(),  # Store full JSON
            )
            session.add(doc)

            # Store chapters with nested content
            for pos, chapter in enumerate(scraped_doc.chapters):
                self._store_chapter(session, doc.id, chapter, pos)

            # Store standalone articles (no chapter)
            for pos, article in enumerate(scraped_doc.articles):
                self._store_article(session, doc.id, None, None, article, pos)

            session.commit()
            return doc.id

    def get_article_by_number(self, doc_id: UUID, article_num: int) -> Optional[LegalArticleModel]:
        """Retrieve specific article by number."""

    def get_clause_text(self, article_id: UUID, clause_num: int) -> Optional[str]:
        """Retrieve clause text for citation."""

    def link_to_kg(self, element_id: UUID, kg_node_id: UUID, element_type: str):
        """Link DB element to KG node."""

    def get_provenance(self, kg_node_id: UUID) -> dict:
        """Get original article/clause for KG node."""
```

### Step 4: Create Citation Formatter (1h)

Create `semantica/legal/citation.py`:

```python
class LegalCitationFormatter:
    """Format legal citations from DB records."""

    def format_citation(self, article: Article, clause: Clause = None, point: Point = None) -> str:
        """Format as 'Điều X, Khoản Y, Điểm Z - Luật ABC'"""

    def get_full_context(self, clause_id: UUID) -> Dict:
        """Get clause text with full hierarchical context."""
```

## Todo List

- [ ] Create SQLAlchemy models in `semantica/legal/models.py`
- [ ] Set up Alembic migrations
- [ ] Implement `LegalDocumentDB.store_from_scraper()` for Phase 00 integration
- [ ] Add indexes on so_hieu, article_number, kg_node_id
- [ ] Implement `LegalCitationFormatter`
- [ ] Write unit tests for CRUD operations
- [ ] Test import from Phase 00 scraped data (10 documents, 619 articles)

## Success Criteria

- [ ] All 7 tables created with proper FK relationships (documents, chapters, sections, articles, clauses, points, cross_references)
- [ ] `store_from_scraper()` successfully imports Phase 00 LegalDocument
- [ ] JSONB full_hierarchy stores complete parsed tree
- [ ] kg_node_id links work bidirectionally
- [ ] Citation formatter produces "Điều X, Khoản Y" format
- [ ] Query performance <100ms for article lookup

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema changes during dev | Medium | Medium | Use Alembic migrations |
| JSONB query performance | Low | Medium | Add GIN index on full_hierarchy |
| UUID generation conflicts | Very Low | High | Use uuid4() with proper seeding |

## Security Considerations

- Use parameterized queries (SQLAlchemy handles this)
- Validate document_type against allowed list
- Sanitize source_file paths

## Next Steps

After completing Phase 01:
1. Import Phase 00 scraped data into database
2. Proceed to Phase 03: Legal Entity Extraction (skip Phase 02 - already have parsed data)
3. kg_node_id will be set in Phase 04 during KG construction
