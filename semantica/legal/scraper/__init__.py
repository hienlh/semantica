"""Legal document scraper subpackage."""

from .base import (
    LegalDocument,
    LegalChapter,
    LegalSection,
    LegalArticle,
    LegalClause,
    LegalPoint,
    BaseLegalScraper,
)
from .tvpl import TVPLScraper
from .hierarchy_extractor import HierarchyExtractor

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
