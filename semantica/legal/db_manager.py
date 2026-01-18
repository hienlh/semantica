"""
Database manager for Vietnamese legal documents.

Handles SQLite database operations:
- Store Phase 00 scraper output with hierarchical IDs
- Query articles by ID or number
- Citation formatting
- KG node linking (Phase 04)

ID Format:
- Document: "59-2020-QH14"
- Chương:   "59-2020-QH14:c1"
- Mục:      "59-2020-QH14:c1:m2"
- Điều:     "59-2020-QH14:d5"
- Khoản:    "59-2020-QH14:d5:k1"
- Điểm:     "59-2020-QH14:d5:k1:a"
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from .models import (
    Base,
    LegalAbbreviationModel,
    LegalAppendixItemModel,
    LegalAppendixModel,
    LegalArticleModel,
    LegalChapterModel,
    LegalClauseModel,
    LegalDocumentModel,
    LegalPointModel,
    LegalSectionModel,
    make_appendix_id,
    make_appendix_item_id,
    make_article_id,
    make_chapter_id,
    make_clause_id,
    make_document_id,
    make_point_id,
    make_section_id,
)
from .abbreviation_extractor import AbbreviationExtractor, AbbreviationMatch
from .scraper.base import (
    LegalAppendix,
    LegalAppendixItem,
    LegalArticle,
    LegalChapter,
    LegalClause,
    LegalDocument,
    LegalPoint,
    LegalSection,
)

DEFAULT_DB_PATH = "data/legal_docs.db"


class LegalDocumentDB:
    """
    SQLite database manager for legal document storage.

    Usage:
        db = LegalDocumentDB()
        doc_id = db.store_document(scraped_doc)
        article = db.get_article_by_id("59-2020-QH14:d5")
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize database connection."""
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._abbrev_extractor = AbbreviationExtractor()

    def store_document(self, doc: LegalDocument) -> str:
        """
        Store a LegalDocument from Phase 00 scraper.

        Returns:
            Document ID (e.g. "59-2020-QH14")
        """
        with self.SessionLocal() as session:
            # Generate document ID from số hiệu
            doc_id = make_document_id(doc.so_hieu)

            # Track seen element numbers for duplicate handling
            self._chapter_counts: dict[str, int] = {}  # chapter_number -> count
            self._section_counts: dict[str, int] = {}  # "chap:section" -> count
            self._article_counts: dict[int, int] = {}  # article_number -> count

            # Create document model
            doc_model = LegalDocumentModel(
                id=doc_id,
                so_hieu=doc.so_hieu,
                title=doc.title,
                loai_van_ban=doc.loai_van_ban,
                co_quan_ban_hanh=doc.co_quan_ban_hanh,
                nguoi_ky=doc.nguoi_ky,
                ngay_ban_hanh=doc.ngay_ban_hanh.date() if doc.ngay_ban_hanh else None,
                ngay_hieu_luc=doc.ngay_hieu_luc.date() if doc.ngay_hieu_luc else None,
                tinh_trang=doc.tinh_trang,
                raw_text=doc.raw_text,
                source_url=doc.url,
            )
            session.add(doc_model)

            # Store chapters with nested content
            for pos, chapter in enumerate(doc.chapters):
                self._store_chapter(session, doc_id, chapter, pos)

            # Store appendices
            for pos, appendix in enumerate(doc.appendices):
                self._store_appendix(session, doc_id, appendix, pos)

            # Extract and store abbreviations from document text
            if doc.raw_text:
                self._extract_and_store_abbreviations(session, doc.raw_text)

            session.commit()
            return doc_id

    def _store_chapter(
        self, session: Session, doc_id: str, chapter: LegalChapter, position: int
    ) -> str:
        """Store a chapter and its nested content."""
        # Track chapter occurrences for unique ID
        chap_key = str(chapter.number)
        count = self._chapter_counts.get(chap_key, 0) + 1
        self._chapter_counts[chap_key] = count

        # Generate unique chapter ID: "doc:c1" or "doc:c1.2" for duplicates
        base_id = make_chapter_id(doc_id, chapter.number)
        chapter_id = base_id if count == 1 else f"{base_id}.{count}"

        chapter_model = LegalChapterModel(
            id=chapter_id,
            document_id=doc_id,
            chapter_number=chapter.number,
            title=chapter.title,
            raw_text=chapter.raw_text,
            position=position,
        )
        session.add(chapter_model)

        # Store sections within chapter
        for pos, section in enumerate(chapter.sections):
            self._store_section(session, doc_id, chapter_id, section, pos)

        # Store direct articles within chapter (no section)
        for pos, article in enumerate(chapter.articles):
            self._store_article(session, doc_id, chapter_id, None, article, pos)

        return chapter_id

    def _store_section(
        self,
        session: Session,
        doc_id: str,
        chapter_id: str,
        section: LegalSection,
        position: int,
    ) -> str:
        """Store a section and its articles."""
        # Track section occurrences for unique ID
        sec_key = f"{chapter_id}:m{section.number}"
        count = self._section_counts.get(sec_key, 0) + 1
        self._section_counts[sec_key] = count

        # Generate unique section ID: "chap:m1" or "chap:m1.2" for duplicates
        base_id = f"{chapter_id}:m{section.number}"
        section_id = base_id if count == 1 else f"{base_id}.{count}"

        section_model = LegalSectionModel(
            id=section_id,
            chapter_id=chapter_id,
            section_number=section.number,
            title=section.title,
            raw_text=section.raw_text,
            position=position,
        )
        session.add(section_model)

        # Store articles within section
        for pos, article in enumerate(section.articles):
            self._store_article(session, doc_id, chapter_id, section_id, article, pos)

        return section_id

    def _store_article(
        self,
        session: Session,
        doc_id: str,
        chapter_id: Optional[str],
        section_id: Optional[str],
        article: LegalArticle,
        position: int,
    ) -> str:
        """Store an article and its clauses."""
        # Track article number occurrences for unique ID generation
        count = self._article_counts.get(article.number, 0) + 1
        self._article_counts[article.number] = count

        # Generate unique article ID: "doc:d5" or "doc:d5.2" for duplicates
        base_id = make_article_id(doc_id, article.number)
        article_id = base_id if count == 1 else f"{base_id}.{count}"

        article_model = LegalArticleModel(
            id=article_id,
            document_id=doc_id,
            chapter_id=chapter_id,
            section_id=section_id,
            article_number=article.number,
            title=article.title,
            content=article.content,
            raw_text=article.raw_text,
            position=position,
        )
        session.add(article_model)

        # Track clause counts for this article
        clause_counts: dict[int, int] = {}

        # Store clauses within article
        for pos, clause in enumerate(article.clauses):
            self._store_clause(session, article_id, clause, pos, clause_counts)

        return article_id

    def _store_clause(
        self,
        session: Session,
        article_id: str,
        clause: LegalClause,
        position: int,
        clause_counts: dict[int, int],
    ) -> str:
        """Store a clause and its points."""
        # Track clause occurrences for unique ID
        count = clause_counts.get(clause.number, 0) + 1
        clause_counts[clause.number] = count

        # Generate unique clause ID: "art:k1" or "art:k1.2" for duplicates
        base_id = make_clause_id(article_id, clause.number)
        clause_id = base_id if count == 1 else f"{base_id}.{count}"

        clause_model = LegalClauseModel(
            id=clause_id,
            article_id=article_id,
            clause_number=clause.number,
            content=clause.content,
            raw_text=clause.raw_text,
            position=position,
        )
        session.add(clause_model)

        # Track point counts for this clause
        point_counts: dict[str, int] = {}

        # Store points within clause
        for pos, point in enumerate(clause.points):
            self._store_point(session, clause_id, point, pos, point_counts)

        return clause_id

    def _store_point(
        self,
        session: Session,
        clause_id: str,
        point: LegalPoint,
        position: int,
        point_counts: dict[str, int],
    ) -> str:
        """Store a point."""
        # Track point occurrences for unique ID
        count = point_counts.get(point.letter, 0) + 1
        point_counts[point.letter] = count

        # Generate unique point ID: "clause:a" or "clause:a.2" for duplicates
        base_id = make_point_id(clause_id, point.letter)
        point_id = base_id if count == 1 else f"{base_id}.{count}"

        point_model = LegalPointModel(
            id=point_id,
            clause_id=clause_id,
            point_letter=point.letter,
            content=point.content,
            raw_text=point.raw_text,
            position=position,
        )
        session.add(point_model)
        return point_id

    def _store_appendix(
        self,
        session: Session,
        doc_id: str,
        appendix: LegalAppendix,
        position: int,
    ) -> str:
        """Store an appendix and its items."""
        # Generate appendix ID
        appendix_id = make_appendix_id(doc_id, appendix.number or str(position + 1))

        appendix_model = LegalAppendixModel(
            id=appendix_id,
            document_id=doc_id,
            appendix_number=appendix.number or str(position + 1),
            title=appendix.title,
            raw_text=appendix.raw_text,
            position=position,
        )
        session.add(appendix_model)

        # Track item counts for duplicates
        item_counts: dict[int, int] = {}

        # Store items within appendix
        for pos, item in enumerate(appendix.items):
            self._store_appendix_item(session, appendix_id, item, pos, item_counts)

        return appendix_id

    def _store_appendix_item(
        self,
        session: Session,
        appendix_id: str,
        item: LegalAppendixItem,
        position: int,
        item_counts: dict[int, int],
    ) -> str:
        """Store an appendix item."""
        # Track item occurrences for unique ID
        count = item_counts.get(item.number, 0) + 1
        item_counts[item.number] = count

        # Generate unique item ID: "appendix:mk1" or "appendix:mk1.2" for duplicates
        base_id = make_appendix_item_id(appendix_id, item.number)
        item_id = base_id if count == 1 else f"{base_id}.{count}"

        item_model = LegalAppendixItemModel(
            id=item_id,
            appendix_id=appendix_id,
            item_number=item.number,
            content=item.content,
            raw_text=item.raw_text,
            position=position,
        )
        session.add(item_model)
        return item_id

    def _extract_and_store_abbreviations(
        self, session: Session, text: str
    ) -> List[str]:
        """
        Extract abbreviations from text and store/update in database.

        Args:
            session: Database session
            text: Document text to analyze

        Returns:
            List of abbreviation IDs that were stored/updated
        """
        matches = self._abbrev_extractor.extract_from_text(text)
        stored_ids = []

        for match in matches:
            # Check if abbreviation already exists
            existing = session.get(LegalAbbreviationModel, match.abbreviation)

            if existing:
                # Update count (aggregate across documents)
                existing.corpus_count += match.count
                # Update context if new one is better (has more context)
                if match.sample_context and len(match.sample_context) > len(
                    existing.sample_context or ""
                ):
                    existing.sample_context = match.sample_context
                # Update full_form if new one has higher confidence
                if match.full_form and (
                    not existing.full_form or
                    match.full_form_confidence > existing.confidence
                ):
                    existing.full_form = match.full_form
            else:
                # Create new abbreviation record
                # full_form is auto-detected from text patterns
                abbrev_model = LegalAbbreviationModel(
                    id=match.abbreviation,
                    abbreviation=match.abbreviation,
                    full_form=match.full_form,  # Auto-detected from text
                    category=None,  # Set manually later
                    corpus_count=match.count,
                    confidence=match.confidence,
                    detection_reason=match.detection_reason,
                    sample_context=match.sample_context,
                )
                session.add(abbrev_model)

            stored_ids.append(match.abbreviation)

        return stored_ids

    def extract_abbreviations_from_all_documents(self) -> int:
        """
        Re-extract abbreviations from all stored documents.

        Collects text from articles, clauses, and points (since raw_text
        at document level may be empty).

        Use this to refresh abbreviation table after algorithm updates
        or when importing documents without abbreviation extraction.

        Returns:
            Number of abbreviations extracted
        """
        with self.SessionLocal() as session:
            # Clear existing abbreviations
            session.query(LegalAbbreviationModel).delete()

            # Collect text from all levels
            all_texts = []

            # Get document raw_text (if available)
            docs = session.query(LegalDocumentModel).all()
            for doc in docs:
                if doc.raw_text:
                    all_texts.append(doc.raw_text)

            # Get article content
            articles = session.query(LegalArticleModel).all()
            for art in articles:
                if art.content:
                    all_texts.append(art.content)
                if art.raw_text:
                    all_texts.append(art.raw_text)

            # Get clause content
            clauses = session.query(LegalClauseModel).all()
            for cl in clauses:
                if cl.content:
                    all_texts.append(cl.content)

            # Get point content
            points = session.query(LegalPointModel).all()
            for pt in points:
                if pt.content:
                    all_texts.append(pt.content)

            # Extract from all texts combined
            if all_texts:
                matches = self._abbrev_extractor.extract_from_texts(all_texts)
                for match in matches:
                    abbrev_model = LegalAbbreviationModel(
                        id=match.abbreviation,
                        abbreviation=match.abbreviation,
                        full_form=match.full_form,  # Auto-detected from text
                        category=None,  # Set manually later
                        corpus_count=match.count,
                        confidence=match.confidence,
                        detection_reason=match.detection_reason,
                        sample_context=match.sample_context,
                    )
                    session.add(abbrev_model)

                session.commit()
                return len(matches)

            return 0

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_document(self, doc_id: str) -> Optional[LegalDocumentModel]:
        """Get document by ID with all relationships loaded."""
        with self.SessionLocal() as session:
            stmt = (
                select(LegalDocumentModel)
                .options(
                    joinedload(LegalDocumentModel.chapters)
                    .joinedload(LegalChapterModel.articles)
                    .joinedload(LegalArticleModel.clauses)
                    .joinedload(LegalClauseModel.points)
                )
                .where(LegalDocumentModel.id == doc_id)
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_document_by_so_hieu(self, so_hieu: str) -> Optional[LegalDocumentModel]:
        """Get document by số hiệu (document number) with chapters loaded."""
        with self.SessionLocal() as session:
            stmt = (
                select(LegalDocumentModel)
                .options(joinedload(LegalDocumentModel.chapters))
                .where(LegalDocumentModel.so_hieu == so_hieu)
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_article_by_id(self, article_id: str) -> Optional[LegalArticleModel]:
        """
        Get article by hierarchical ID.

        Args:
            article_id: e.g. "59-2020-QH14:d5"
        """
        with self.SessionLocal() as session:
            stmt = (
                select(LegalArticleModel)
                .options(
                    joinedload(LegalArticleModel.clauses)
                    .joinedload(LegalClauseModel.points)
                )
                .where(LegalArticleModel.id == article_id)
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_article(
        self, doc_id: str, article_number: int
    ) -> Optional[LegalArticleModel]:
        """Get article by document ID and article number with clauses loaded."""
        article_id = make_article_id(doc_id, article_number)
        return self.get_article_by_id(article_id)

    def get_article_by_so_hieu(
        self, so_hieu: str, article_number: int
    ) -> Optional[LegalArticleModel]:
        """Get article by document số hiệu and article number."""
        doc_id = make_document_id(so_hieu)
        return self.get_article(doc_id, article_number)

    def get_clause_by_id(self, clause_id: str) -> Optional[LegalClauseModel]:
        """
        Get clause by hierarchical ID.

        Args:
            clause_id: e.g. "59-2020-QH14:d5:k1"
        """
        with self.SessionLocal() as session:
            stmt = (
                select(LegalClauseModel)
                .options(joinedload(LegalClauseModel.points))
                .where(LegalClauseModel.id == clause_id)
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_clause(
        self, article_id: str, clause_number: int
    ) -> Optional[LegalClauseModel]:
        """Get clause by article ID and clause number with points loaded."""
        clause_id = make_clause_id(article_id, clause_number)
        return self.get_clause_by_id(clause_id)

    def list_documents(self) -> List[LegalDocumentModel]:
        """List all documents (without relationships for performance)."""
        with self.SessionLocal() as session:
            stmt = select(LegalDocumentModel).order_by(LegalDocumentModel.created_at.desc())
            results = session.scalars(stmt).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def count_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.SessionLocal() as session:
            return {
                "documents": session.query(LegalDocumentModel).count(),
                "chapters": session.query(LegalChapterModel).count(),
                "sections": session.query(LegalSectionModel).count(),
                "articles": session.query(LegalArticleModel).count(),
                "clauses": session.query(LegalClauseModel).count(),
                "points": session.query(LegalPointModel).count(),
                "appendices": session.query(LegalAppendixModel).count(),
                "appendix_items": session.query(LegalAppendixItemModel).count(),
                "abbreviations": session.query(LegalAbbreviationModel).count(),
            }

    def link_to_kg(self, element_id: str, kg_node_id: str, element_type: str) -> bool:
        """
        Link a DB element to a KG node (Phase 04).

        Args:
            element_id: Hierarchical ID of the element
            kg_node_id: ID of the KG node
            element_type: One of 'document', 'chapter', 'section', 'article', 'clause', 'point'
        """
        model_map = {
            "document": LegalDocumentModel,
            "chapter": LegalChapterModel,
            "section": LegalSectionModel,
            "article": LegalArticleModel,
            "clause": LegalClauseModel,
            "point": LegalPointModel,
            "appendix": LegalAppendixModel,
            "appendix_item": LegalAppendixItemModel,
        }

        model_class = model_map.get(element_type)
        if not model_class:
            raise ValueError(f"Unknown element type: {element_type}")

        with self.SessionLocal() as session:
            element = session.get(model_class, element_id)
            if element:
                element.kg_node_id = kg_node_id
                session.commit()
                return True
            return False

    # =========================================================================
    # Abbreviation Query Methods
    # =========================================================================

    def get_abbreviation(self, abbrev: str) -> Optional[LegalAbbreviationModel]:
        """Get abbreviation by ID."""
        with self.SessionLocal() as session:
            result = session.get(LegalAbbreviationModel, abbrev)
            if result:
                session.expunge(result)
            return result

    def list_abbreviations(
        self, category: Optional[str] = None, min_count: int = 0
    ) -> List[LegalAbbreviationModel]:
        """
        List abbreviations with optional filters.

        Args:
            category: Filter by category (e.g., "corporate", "document_type")
            min_count: Minimum corpus count

        Returns:
            List of abbreviations sorted by count descending
        """
        with self.SessionLocal() as session:
            query = session.query(LegalAbbreviationModel)

            if category:
                query = query.filter(LegalAbbreviationModel.category == category)
            if min_count > 0:
                query = query.filter(LegalAbbreviationModel.corpus_count >= min_count)

            query = query.order_by(LegalAbbreviationModel.corpus_count.desc())
            results = query.all()

            for r in results:
                session.expunge(r)
            return results

    def get_abbreviation_full_form(self, abbrev: str) -> Optional[str]:
        """Get full form of an abbreviation."""
        result = self.get_abbreviation(abbrev)
        return result.full_form if result else None

    def update_abbreviation_full_form(
        self, abbrev: str, full_form: str, category: Optional[str] = None
    ) -> bool:
        """
        Update or set the full form of an abbreviation.

        Args:
            abbrev: Abbreviation to update
            full_form: Full form to set
            category: Optional category to set

        Returns:
            True if updated, False if abbreviation not found
        """
        with self.SessionLocal() as session:
            result = session.get(LegalAbbreviationModel, abbrev)
            if result:
                result.full_form = full_form
                if category:
                    result.category = category
                session.commit()
                return True
            return False

    def get_abbreviation_stats(self) -> Dict[str, Any]:
        """Get abbreviation statistics."""
        with self.SessionLocal() as session:
            total = session.query(LegalAbbreviationModel).count()
            with_full_form = (
                session.query(LegalAbbreviationModel)
                .filter(LegalAbbreviationModel.full_form.isnot(None))
                .count()
            )

            # Count by category
            by_category = {}
            categories = (
                session.query(LegalAbbreviationModel.category)
                .distinct()
                .all()
            )
            for (cat,) in categories:
                if cat:
                    count = (
                        session.query(LegalAbbreviationModel)
                        .filter(LegalAbbreviationModel.category == cat)
                        .count()
                    )
                    by_category[cat] = count

            return {
                "total": total,
                "with_full_form": with_full_form,
                "without_full_form": total - with_full_form,
                "by_category": by_category,
            }


# =============================================================================
# JSON Loading Helpers
# =============================================================================


def load_json_document(json_path: str) -> LegalDocument:
    """
    Load a LegalDocument from JSON file (Phase 00 output).

    Args:
        json_path: Path to JSON file

    Returns:
        LegalDocument instance
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parse dates
    ngay_ban_hanh = None
    ngay_hieu_luc = None
    if data.get("ngay_ban_hanh"):
        ngay_ban_hanh = datetime.fromisoformat(data["ngay_ban_hanh"])
    if data.get("ngay_hieu_luc"):
        ngay_hieu_luc = datetime.fromisoformat(data["ngay_hieu_luc"])

    # Build chapters
    chapters = []
    for ch_data in data.get("chapters", []):
        chapter = LegalChapter(
            number=ch_data["number"],
            title=ch_data.get("title", ""),
            raw_text=ch_data.get("raw_text", ""),
            sections=[_parse_section(s) for s in ch_data.get("sections", [])],
            articles=[_parse_article(a) for a in ch_data.get("articles", [])],
        )
        chapters.append(chapter)

    # Build standalone articles
    articles = [_parse_article(a) for a in data.get("articles", [])]

    # Build appendices
    appendices = [_parse_appendix(a) for a in data.get("appendices", [])]

    return LegalDocument(
        url=data.get("url", ""),
        so_hieu=data.get("so_hieu", ""),
        title=data.get("title", ""),
        loai_van_ban=data.get("loai_van_ban", ""),
        co_quan_ban_hanh=data.get("co_quan_ban_hanh", ""),
        nguoi_ky=data.get("nguoi_ky", ""),
        ngay_ban_hanh=ngay_ban_hanh,
        ngay_hieu_luc=ngay_hieu_luc,
        tinh_trang=data.get("tinh_trang", ""),
        chapters=chapters,
        articles=articles,
        appendices=appendices,
        raw_text=data.get("raw_text", ""),
        metadata=data.get("metadata", {}),
    )


def _parse_section(data: Dict[str, Any]) -> LegalSection:
    """Parse section from dict."""
    return LegalSection(
        number=data["number"],
        title=data.get("title", ""),
        raw_text=data.get("raw_text", ""),
        articles=[_parse_article(a) for a in data.get("articles", [])],
    )


def _parse_article(data: Dict[str, Any]) -> LegalArticle:
    """Parse article from dict."""
    return LegalArticle(
        number=data["number"],
        title=data.get("title", ""),
        content=data.get("content", ""),
        raw_text=data.get("raw_text", ""),
        clauses=[_parse_clause(c) for c in data.get("clauses", [])],
    )


def _parse_clause(data: Dict[str, Any]) -> LegalClause:
    """Parse clause from dict."""
    return LegalClause(
        number=data["number"],
        content=data.get("content", ""),
        raw_text=data.get("raw_text", ""),
        points=[_parse_point(p) for p in data.get("points", [])],
    )


def _parse_point(data: Dict[str, Any]) -> LegalPoint:
    """Parse point from dict."""
    return LegalPoint(
        letter=data["letter"],
        content=data.get("content", ""),
        raw_text=data.get("raw_text", ""),
    )


def _parse_appendix(data: Dict[str, Any]) -> LegalAppendix:
    """Parse appendix from dict."""
    return LegalAppendix(
        number=data.get("number", ""),
        title=data.get("title", ""),
        raw_text=data.get("raw_text", ""),
        items=[_parse_appendix_item(i) for i in data.get("items", [])],
    )


def _parse_appendix_item(data: Dict[str, Any]) -> LegalAppendixItem:
    """Parse appendix item from dict."""
    return LegalAppendixItem(
        number=data["number"],
        content=data.get("content", ""),
        raw_text=data.get("raw_text", ""),
    )
