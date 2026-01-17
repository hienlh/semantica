"""
Legal Document Ingestor Module.

This module provides ingestion capabilities for Vietnamese legal documents
from thuvienphapluat.vn (TVPL), including web scraping, HTML parsing,
database storage, and cross-reference detection.

Supported Methods:
    - "scrape": Scrape legal documents from URLs
    - "parse": Parse existing HTML files to structured data
    - "import": Import JSON documents to database
    - "full": Full pipeline (scrape → parse → import)

Key Features:
    - Web scraping from thuvienphapluat.vn
    - Hierarchical structure extraction (Chương > Mục > Điều > Khoản > Điểm > Phụ lục)
    - SQLite database storage
    - Cross-reference detection between articles
    - Vietnamese legal ID generation

Main Classes:
    - LegalIngestor: Legal document ingestion handler
    - LegalData: Container for ingested legal document data

Example Usage:
    >>> from semantica.ingest import ingest_legal
    >>> # Scrape from URL
    >>> result = ingest_legal("https://thuvienphapluat.vn/...", method="scrape")
    >>> # Parse HTML files
    >>> result = ingest_legal("./docs/*.html", method="parse")
    >>> # Import to database
    >>> result = ingest_legal("./docs/json/*.json", method="import")
"""

import asyncio
import glob
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.logging import get_logger

logger = get_logger("legal_ingestor")


@dataclass
class LegalData:
    """Container for ingested legal document data."""

    so_hieu: str  # Document number (e.g., "59/2020/QH14")
    title: str
    loai_van_ban: Optional[str] = None  # Document type
    co_quan_ban_hanh: Optional[str] = None  # Issuing authority
    ngay_ban_hanh: Optional[str] = None  # Issue date
    ngay_hieu_luc: Optional[str] = None  # Effective date
    tinh_trang: Optional[str] = None  # Status
    chapters: int = 0
    articles: int = 0
    clauses: int = 0
    points: int = 0
    appendices: int = 0
    cross_references: int = 0
    source_url: Optional[str] = None
    html_path: Optional[str] = None
    json_path: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LegalIngestor:
    """
    Legal document ingestion handler.

    Provides methods for scraping, parsing, and importing Vietnamese legal
    documents from thuvienphapluat.vn (TVPL).

    Args:
        output_dir: Directory for storing scraped files
        db_path: Path to SQLite database
        headless: Run browser in headless mode
        rate_limit_seconds: Delay between requests
        save_raw_html: Save raw HTML files

    Example:
        >>> ingestor = LegalIngestor(output_dir="./legal_docs")
        >>> doc = await ingestor.scrape("https://thuvienphapluat.vn/...")
        >>> ingestor.import_to_db(["./legal_docs/json/doc.json"])
    """

    def __init__(
        self,
        output_dir: str = "scraped_legal_docs",
        db_path: str = "data/legal_docs.db",
        headless: bool = True,
        rate_limit_seconds: float = 2.0,
        save_raw_html: bool = True,
        **kwargs,
    ):
        self.output_dir = Path(output_dir)
        self.db_path = db_path
        self.headless = headless
        self.rate_limit_seconds = rate_limit_seconds
        self.save_raw_html = save_raw_html
        self.kwargs = kwargs

        # Lazy load legal module components
        self._scraper = None
        self._db = None
        self._detector = None

    @property
    def scraper(self):
        """Lazy load TVPLScraper."""
        if self._scraper is None:
            from ..legal import TVPLScraper

            self._scraper = TVPLScraper(
                headless=self.headless,
                rate_limit_seconds=self.rate_limit_seconds,
                save_raw_html=self.save_raw_html,
                output_dir=self.output_dir,
            )
        return self._scraper

    @property
    def db(self):
        """Lazy load LegalDocumentDB."""
        if self._db is None:
            from ..legal import LegalDocumentDB

            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._db = LegalDocumentDB(self.db_path)
        return self._db

    @property
    def detector(self):
        """Lazy load CrossReferenceDetector."""
        if self._detector is None:
            from ..legal import CrossReferenceDetector

            self._detector = CrossReferenceDetector()
        return self._detector

    async def scrape(self, url: str, **kwargs) -> LegalData:
        """
        Scrape a legal document from URL.

        Args:
            url: TVPL document URL
            **kwargs: Additional options for scraper

        Returns:
            LegalData with scraped document info
        """
        logger.info(f"Scraping: {url}")

        doc = await self.scraper.scrape(url)
        self.scraper._save_document(doc)

        # Get file paths (same logic as TVPLScraper._save_document)
        filename = doc.so_hieu.replace("/", "-") if doc.so_hieu else "unknown"
        html_path = str(self.output_dir / f"{filename}.html")
        json_path = str(self.output_dir / f"{filename}.json")

        return LegalData(
            so_hieu=doc.so_hieu,
            title=doc.title,
            loai_van_ban=doc.loai_van_ban,
            co_quan_ban_hanh=doc.co_quan_ban_hanh,
            ngay_ban_hanh=doc.ngay_ban_hanh,
            ngay_hieu_luc=doc.ngay_hieu_luc,
            tinh_trang=doc.tinh_trang,
            chapters=len(doc.chapters),
            articles=doc.total_articles,
            appendices=len(doc.appendices),
            source_url=url,
            html_path=html_path,
            json_path=json_path,
            raw_data=doc.to_dict(),
        )

    def scrape_sync(self, url: str, **kwargs) -> LegalData:
        """Synchronous wrapper for scrape."""
        return asyncio.run(self.scrape(url, **kwargs))

    async def scrape_urls(self, urls: List[str], **kwargs) -> List[LegalData]:
        """
        Scrape multiple legal documents from URLs.

        Args:
            urls: List of TVPL document URLs
            **kwargs: Additional options for scraper

        Returns:
            List of LegalData for scraped documents
        """
        results = []
        for url in urls:
            try:
                data = await self.scrape(url, **kwargs)
                results.append(data)
                logger.info(f"Scraped: {data.so_hieu}")
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
        return results

    def scrape_urls_sync(self, urls: List[str], **kwargs) -> List[LegalData]:
        """Synchronous wrapper for scrape_urls."""
        return asyncio.run(self.scrape_urls(urls, **kwargs))

    def scrape_from_file(self, url_file: str, **kwargs) -> List[LegalData]:
        """
        Scrape documents from URLs in a file.

        Args:
            url_file: Path to file containing URLs (one per line)
            **kwargs: Additional options for scraper

        Returns:
            List of LegalData for scraped documents
        """
        with open(url_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        logger.info(f"Found {len(urls)} URLs in {url_file}")
        return self.scrape_urls_sync(urls, **kwargs)

    def parse(self, html_file: str, **kwargs) -> LegalData:
        """
        Parse an HTML file to structured legal document.

        Args:
            html_file: Path to HTML file
            **kwargs: Additional options

        Returns:
            LegalData with parsed document info
        """
        logger.info(f"Parsing: {html_file}")

        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        doc = self.scraper.parse(html, html_file)

        # Save as JSON
        json_dir = self.output_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        base = Path(html_file).stem
        json_path = json_dir / f"{base}.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)

        return LegalData(
            so_hieu=doc.so_hieu,
            title=doc.title,
            loai_van_ban=doc.loai_van_ban,
            co_quan_ban_hanh=doc.co_quan_ban_hanh,
            ngay_ban_hanh=doc.ngay_ban_hanh,
            ngay_hieu_luc=doc.ngay_hieu_luc,
            tinh_trang=doc.tinh_trang,
            chapters=len(doc.chapters),
            articles=doc.total_articles,
            appendices=len(doc.appendices),
            html_path=html_file,
            json_path=str(json_path),
            raw_data=doc.to_dict(),
        )

    def parse_html_files(self, html_files: List[str], **kwargs) -> List[LegalData]:
        """
        Parse multiple HTML files.

        Args:
            html_files: List of HTML file paths (supports glob patterns)
            **kwargs: Additional options

        Returns:
            List of LegalData for parsed documents
        """
        # Expand glob patterns
        expanded_files = []
        for pattern in html_files:
            expanded_files.extend(glob.glob(pattern))

        results = []
        for html_file in sorted(set(expanded_files)):
            try:
                data = self.parse(html_file, **kwargs)
                results.append(data)
                logger.info(f"Parsed: {data.so_hieu}")
            except Exception as e:
                logger.error(f"Failed to parse {html_file}: {e}")

        return results

    def import_to_db(
        self, json_files: List[str], fresh: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """
        Import JSON files to database.

        Args:
            json_files: List of JSON file paths (supports glob patterns)
            fresh: If True, recreate database
            **kwargs: Additional options

        Returns:
            Dict with import statistics
        """
        from ..legal import load_json_document, store_cross_references

        # Expand glob patterns
        expanded_files = []
        for pattern in json_files:
            expanded_files.extend(glob.glob(pattern))

        # Handle fresh database
        if fresh and os.path.exists(self.db_path):
            os.remove(self.db_path)
            self._db = None  # Reset lazy loaded DB
            logger.info(f"Removed old database: {self.db_path}")

        logger.info(f"Importing {len(expanded_files)} documents to: {self.db_path}")

        imported = 0
        for json_file in sorted(set(expanded_files)):
            try:
                doc = load_json_document(json_file)
                self.db.store_document(doc)
                logger.info(f"Imported: {doc.so_hieu}")
                imported += 1
            except Exception as e:
                logger.error(f"Failed to import {json_file}: {e}")

        # Detect and store cross-references
        logger.info("Detecting cross-references...")
        docs = self.db.list_documents()
        all_refs = []

        for doc in docs:
            refs = self.detector.detect_in_document(self.db, doc.id)
            all_refs.extend(refs)

        stored = store_cross_references(self.db, all_refs)
        logger.info(f"Stored {stored} cross-references")

        # Get stats
        stats = self.db.count_stats()
        stats["imported"] = imported
        stats["cross_references"] = stored

        return stats

    def full_pipeline(
        self,
        source: Union[str, List[str]],
        fresh: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Full pipeline: scrape/parse → import to database.

        Args:
            source: URL file path, HTML file pattern, or list of URLs
            fresh: If True, recreate database
            **kwargs: Additional options

        Returns:
            Dict with pipeline statistics
        """
        # Determine source type
        if isinstance(source, str):
            if source.endswith(".txt"):
                # URL file
                logger.info("Running full pipeline from URL file")
                scraped = self.scrape_from_file(source, **kwargs)
                json_files = [d.json_path for d in scraped if d.json_path]
            elif source.endswith(".html") or "*" in source:
                # HTML file(s)
                logger.info("Running pipeline from HTML files")
                parsed = self.parse_html_files([source], **kwargs)
                json_files = [d.json_path for d in parsed if d.json_path]
            else:
                # Single URL
                logger.info("Running pipeline from single URL")
                data = self.scrape_sync(source, **kwargs)
                json_files = [data.json_path] if data.json_path else []
        else:
            # List of URLs
            logger.info("Running pipeline from URL list")
            scraped = self.scrape_urls_sync(source, **kwargs)
            json_files = [d.json_path for d in scraped if d.json_path]

        if not json_files:
            logger.warning("No JSON files to import")
            return {"imported": 0}

        return self.import_to_db(json_files, fresh=fresh, **kwargs)

    def reimport_all(self, data_dir: str, fresh: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Re-parse all HTML and import to fresh database.

        Args:
            data_dir: Directory containing HTML files
            fresh: If True, recreate database
            **kwargs: Additional options

        Returns:
            Dict with reimport statistics
        """
        html_pattern = os.path.join(data_dir, "*.html")
        html_files = glob.glob(html_pattern)

        if not html_files:
            logger.warning(f"No HTML files found in: {data_dir}")
            return {"imported": 0}

        logger.info(f"Re-parsing {len(html_files)} HTML files")
        parsed = self.parse_html_files(html_files, **kwargs)
        json_files = [d.json_path for d in parsed if d.json_path]

        return self.import_to_db(json_files, fresh=fresh, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get current database statistics."""
        return self.db.count_stats()
