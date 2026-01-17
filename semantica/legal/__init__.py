"""
Legal Document Processing Module.

Provides tools for scraping, parsing, storing, and analyzing Vietnamese legal documents.
Supports hierarchical structure extraction (Chương > Mục > Điều > Khoản > Điểm).

Components:
- Scraper: Web scraping from thuvienphapluat.vn (Phase 00)
- Models: SQLAlchemy models for SQLite storage (Phase 01)
- Database: LegalDocumentDB for CRUD operations (Phase 01)
- Citation: Format legal citations (Phase 01)
"""

# Phase 00: Scraper
from .scraper.base import (
    BaseLegalScraper,
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
    LegalArticleModel,
    LegalChapterModel,
    LegalClauseModel,
    LegalCrossReferenceModel,
    LegalDocumentModel,
    LegalPointModel,
    LegalSectionModel,
)

__all__ = [
    # Phase 00: Scraper data classes
    "LegalDocument",
    "LegalChapter",
    "LegalSection",
    "LegalArticle",
    "LegalClause",
    "LegalPoint",
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
    "LegalCrossReferenceModel",
    # Phase 01: Database manager
    "LegalDocumentDB",
    "load_json_document",
    # Phase 01: Citation formatter
    "LegalCitationFormatter",
]
