# Phase 01: Legal Document Database

## Context Links

- [Research: VN Legal Structure](./research/researcher-01-vn-legal-structure.md)
- [Main Plan](./plan.md)

## Overview

Create PostgreSQL database schema for hierarchical Vietnamese legal document storage. Schema mirrors 5-level structure: Document > Chapter > Section > Article > Clause > Point. Each level links to corresponding KG node via `kg_node_id`.

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
│                         PostgreSQL Database                              │
├─────────────────────────────────────────────────────────────────────────┤
│  documents                                                               │
│  ├── id (UUID PK)                                                        │
│  ├── title, type, issuing_authority, effective_date, document_number    │
│  ├── full_hierarchy (JSONB) ─────────────────────────────────────────────┼──→ Full parsed tree
│  ├── kg_node_id (UUID) ──────────────────────────────────────────────────┼──→ Links to KG
│  └── source_file, created_at                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  chapters                                                                │
│  ├── id (UUID PK), document_id (FK), chapter_number, title              │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  sections (Mục - optional layer)                                         │
│  ├── id (UUID PK), chapter_id (FK), section_number, title               │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  articles                                                                │
│  ├── id (UUID PK), chapter_id/section_id (FK), article_number, title    │
│  ├── full_text, kg_node_id (UUID), position                              │
├─────────────────────────────────────────────────────────────────────────┤
│  clauses                                                                 │
│  ├── id (UUID PK), article_id (FK), clause_number, text                 │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  points                                                                  │
│  ├── id (UUID PK), clause_id (FK), point_letter, text                   │
│  ├── kg_node_id (UUID), position                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  cross_references (stores detected "theo Điều X Luật Y" links)           │
│  ├── id (UUID PK), source_article_id, target_article_id                 │
│  ├── reference_text, reference_type, confidence                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

- `/Users/hienlh/Projects/semantica/semantica/kg/provenance_tracker.py` - Provenance pattern
- `/Users/hienlh/Projects/semantica/semantica/ingest/db_ingestor.py` - DB ingestion
- `/Users/hienlh/Projects/semantica/semantica/graph_store/graph_store.py` - Graph store interface

## Implementation Steps

### Step 1: Create SQLAlchemy Models (2h)

Create `semantica/legal/models.py`:

```python
from sqlalchemy import Column, String, Text, Date, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import uuid

Base = declarative_base()

class LegalDocument(Base):
    __tablename__ = 'legal_documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    document_type = Column(String(50))  # 'law', 'decree', 'decision', 'circular'
    document_number = Column(String(100))  # e.g., "20/2014/QH13"
    issuing_authority = Column(String(200))
    effective_date = Column(Date)
    full_hierarchy = Column(JSON)  # Full parsed tree as JSONB
    kg_node_id = Column(UUID(as_uuid=True))  # Link to KG
    source_file = Column(Text)

    chapters = relationship("Chapter", back_populates="document", cascade="all, delete-orphan")

class Chapter(Base):
    __tablename__ = 'legal_chapters'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('legal_documents.id'))
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(500))
    kg_node_id = Column(UUID(as_uuid=True))
    position = Column(Integer)

    document = relationship("LegalDocument", back_populates="chapters")
    articles = relationship("Article", back_populates="chapter", cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = 'legal_articles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey('legal_chapters.id'))
    article_number = Column(Integer, nullable=False)
    title = Column(String(500))
    full_text = Column(Text)
    kg_node_id = Column(UUID(as_uuid=True))
    position = Column(Integer)

    chapter = relationship("Chapter", back_populates="articles")
    clauses = relationship("Clause", back_populates="article", cascade="all, delete-orphan")

class Clause(Base):
    __tablename__ = 'legal_clauses'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'))
    clause_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    kg_node_id = Column(UUID(as_uuid=True))
    position = Column(Integer)

    article = relationship("Article", back_populates="clauses")
    points = relationship("Point", back_populates="clause", cascade="all, delete-orphan")

class Point(Base):
    __tablename__ = 'legal_points'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clause_id = Column(UUID(as_uuid=True), ForeignKey('legal_clauses.id'))
    point_letter = Column(String(1), nullable=False)
    text = Column(Text, nullable=False)
    kg_node_id = Column(UUID(as_uuid=True))
    position = Column(Integer)

    clause = relationship("Clause", back_populates="points")

class CrossReference(Base):
    __tablename__ = 'legal_cross_references'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'))
    target_article_id = Column(UUID(as_uuid=True), ForeignKey('legal_articles.id'), nullable=True)
    target_document_id = Column(UUID(as_uuid=True), ForeignKey('legal_documents.id'), nullable=True)
    reference_text = Column(Text)  # Original text: "theo Điều 5 Luật 20/2014"
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
class LegalDocumentDB:
    """Database manager for legal document storage."""

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def store_document(self, parsed_doc: Dict) -> UUID:
        """Store parsed legal document with hierarchy."""

    def get_article_by_number(self, doc_id: UUID, article_num: int) -> Article:
        """Retrieve specific article."""

    def get_clause_text(self, article_id: UUID, clause_num: int) -> str:
        """Retrieve clause text for citation."""

    def link_to_kg(self, element_id: UUID, kg_node_id: UUID, element_type: str):
        """Link DB element to KG node."""

    def get_provenance(self, kg_node_id: UUID) -> Dict:
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
- [ ] Implement `LegalDocumentDB` class
- [ ] Add indexes on document_id, article_number, effective_date
- [ ] Implement `LegalCitationFormatter`
- [ ] Write unit tests for CRUD operations
- [ ] Test with sample Vietnamese law document

## Success Criteria

- [ ] All tables created with proper FK relationships
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
1. Proceed to Phase 02: Legal Document Parser
2. Parser will populate these tables from PDF/DOCX
3. kg_node_id will be set in Phase 04 during KG construction
