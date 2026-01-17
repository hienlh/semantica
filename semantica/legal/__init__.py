"""
Legal Document Processing Module.

Provides tools for scraping, parsing, storing, and analyzing Vietnamese legal documents.
Supports hierarchical structure extraction (Chương > Mục > Điều > Khoản > Điểm).

Components:
- Scraper: Web scraping from thuvienphapluat.vn (Phase 00)
- Models: SQLAlchemy models for SQLite storage (Phase 01)
- Database: LegalDocumentDB for CRUD operations (Phase 01)
- Citation: Format legal citations (Phase 01)
- CrossRef: Cross-reference detection (Phase 03)
"""

# Phase 00: Scraper
from .scraper.base import (
    BaseLegalScraper,
    LegalAppendix,
    LegalAppendixItem,
    LegalArticle,
    LegalChapter,
    LegalClause,
    LegalDocument,
    LegalPoint,
    LegalSection,
)
from .scraper.hierarchy_extractor import HierarchyExtractor
from .scraper.tvpl import TVPLScraper

# Phase 01: Database
from .citation import LegalCitationFormatter
from .db_manager import LegalDocumentDB, load_json_document
from .models import (
    Base,
    LegalAppendixItemModel,
    LegalAppendixModel,
    LegalArticleModel,
    LegalChapterModel,
    LegalClauseModel,
    LegalCrossReferenceModel,
    LegalDocumentModel,
    LegalPointModel,
    LegalSectionModel,
    # ID generation helpers
    make_appendix_id,
    make_appendix_item_id,
    make_article_id,
    make_chapter_id,
    make_clause_id,
    make_crossref_id,
    make_document_id,
    make_point_id,
    make_section_id,
    normalize_so_hieu,
)

# Phase 03: CrossRef Detection
from .crossref_detector import CrossReference, CrossReferenceDetector, store_cross_references

__all__ = [
    # Phase 00: Scraper data classes
    "LegalDocument",
    "LegalChapter",
    "LegalSection",
    "LegalArticle",
    "LegalClause",
    "LegalPoint",
    "LegalAppendix",
    "LegalAppendixItem",
    "BaseLegalScraper",
    "TVPLScraper",
    "HierarchyExtractor",
    # Phase 01: Database models
    "Base",
    "LegalDocumentModel",
    "LegalChapterModel",
    "LegalSectionModel",
    "LegalArticleModel",
    "LegalClauseModel",
    "LegalPointModel",
    "LegalAppendixModel",
    "LegalAppendixItemModel",
    "LegalCrossReferenceModel",
    # Phase 01: ID generation helpers
    "normalize_so_hieu",
    "make_document_id",
    "make_chapter_id",
    "make_section_id",
    "make_article_id",
    "make_clause_id",
    "make_point_id",
    "make_appendix_id",
    "make_appendix_item_id",
    "make_crossref_id",
    # Phase 01: Database manager
    "LegalDocumentDB",
    "load_json_document",
    # Phase 01: Citation formatter
    "LegalCitationFormatter",
    # Phase 03: CrossRef Detection
    "CrossReferenceDetector",
    "CrossReference",
    "store_cross_references",
]
