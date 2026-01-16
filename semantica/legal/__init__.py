"""
Legal Document Processing Module.

Provides tools for scraping, parsing, and analyzing Vietnamese legal documents.
Supports hierarchical structure extraction (Chương > Mục > Điều > Khoản > Điểm).
"""

from .scraper.base import (
    LegalDocument,
    LegalChapter,
    LegalSection,
    LegalArticle,
    LegalClause,
    LegalPoint,
    BaseLegalScraper,
)
from .scraper.tvpl import TVPLScraper
from .scraper.hierarchy_extractor import HierarchyExtractor

__all__ = [
    "LegalDocument",
    "LegalChapter",
    "LegalSection",
    "LegalArticle",
    "LegalClause",
    "LegalPoint",
    "BaseLegalScraper",
    "TVPLScraper",
    "HierarchyExtractor",
]
