"""
Database manager for Vietnamese legal documents.

Handles SQLite database operations:
- Store Phase 00 scraper output
- Query articles by number
- Citation formatting
- KG node linking (Phase 04)
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from .models import (
    Base,
    LegalArticleModel,
    LegalChapterModel,
    LegalClauseModel,
    LegalDocumentModel,
    LegalPointModel,
    LegalSectionModel,
)
from .scraper.base import (
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
        article = db.get_article(doc_id, article_number=5)
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)  # Auto-create tables
        self.SessionLocal = sessionmaker(bind=self.engine)

    def store_document(self, doc: LegalDocument) -> str:
        """
        Store a LegalDocument from Phase 00 scraper.

        Args:
            doc: LegalDocument from scraper.base

        Returns:
            Document ID (UUID string)
        """
        with self.SessionLocal() as session:
            # Create document model
            doc_model = LegalDocumentModel(
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
            session.flush()  # Get the ID

            # Store chapters with nested content
            for pos, chapter in enumerate(doc.chapters):
                self._store_chapter(session, doc_model.id, chapter, pos)

            session.commit()
            return doc_model.id

    def _store_chapter(
        self, session: Session, doc_id: str, chapter: LegalChapter, position: int
    ) -> str:
        """Store a chapter and its nested content."""
        chapter_model = LegalChapterModel(
            document_id=doc_id,
            chapter_number=chapter.number,
            title=chapter.title,
            raw_text=chapter.raw_text,
            position=position,
        )
        session.add(chapter_model)
        session.flush()

        # Store sections within chapter
        for pos, section in enumerate(chapter.sections):
            self._store_section(session, doc_id, chapter_model.id, section, pos)

        # Store direct articles within chapter (no section)
        for pos, article in enumerate(chapter.articles):
            self._store_article(
                session, doc_id, chapter_model.id, None, article, pos
            )

        return chapter_model.id

    def _store_section(
        self,
        session: Session,
        doc_id: str,
        chapter_id: str,
        section: LegalSection,
        position: int,
    ) -> str:
        """Store a section and its articles."""
        section_model = LegalSectionModel(
            chapter_id=chapter_id,
            section_number=section.number,
            title=section.title,
            raw_text=section.raw_text,
            position=position,
        )
        session.add(section_model)
        session.flush()

        # Store articles within section
        for pos, article in enumerate(section.articles):
            self._store_article(
                session, doc_id, chapter_id, section_model.id, article, pos
            )

        return section_model.id

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
        article_model = LegalArticleModel(
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
        session.flush()

        # Store clauses within article
        for pos, clause in enumerate(article.clauses):
            self._store_clause(session, article_model.id, clause, pos)

        return article_model.id

    def _store_clause(
        self, session: Session, article_id: str, clause: LegalClause, position: int
    ) -> str:
        """Store a clause and its points."""
        clause_model = LegalClauseModel(
            article_id=article_id,
            clause_number=clause.number,
            content=clause.content,
            raw_text=clause.raw_text,
            position=position,
        )
        session.add(clause_model)
        session.flush()

        # Store points within clause
        for pos, point in enumerate(clause.points):
            self._store_point(session, clause_model.id, point, pos)

        return clause_model.id

    def _store_point(
        self, session: Session, clause_id: str, point: LegalPoint, position: int
    ) -> str:
        """Store a point."""
        point_model = LegalPointModel(
            clause_id=clause_id,
            point_letter=point.letter,
            content=point.content,
            raw_text=point.raw_text,
            position=position,
        )
        session.add(point_model)
        session.flush()
        return point_model.id

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

    def get_article(
        self, doc_id: str, article_number: int
    ) -> Optional[LegalArticleModel]:
        """Get article by document ID and article number with clauses loaded."""
        with self.SessionLocal() as session:
            stmt = (
                select(LegalArticleModel)
                .options(
                    joinedload(LegalArticleModel.clauses)
                    .joinedload(LegalClauseModel.points)
                )
                .where(
                    LegalArticleModel.document_id == doc_id,
                    LegalArticleModel.article_number == article_number,
                )
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_article_by_so_hieu(
        self, so_hieu: str, article_number: int
    ) -> Optional[LegalArticleModel]:
        """Get article by document số hiệu and article number with clauses loaded."""
        with self.SessionLocal() as session:
            stmt = (
                select(LegalArticleModel)
                .join(LegalDocumentModel)
                .options(
                    joinedload(LegalArticleModel.clauses)
                    .joinedload(LegalClauseModel.points)
                )
                .where(
                    LegalDocumentModel.so_hieu == so_hieu,
                    LegalArticleModel.article_number == article_number,
                )
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

    def get_clause(
        self, article_id: str, clause_number: int
    ) -> Optional[LegalClauseModel]:
        """Get clause by article ID and clause number with points loaded."""
        with self.SessionLocal() as session:
            stmt = (
                select(LegalClauseModel)
                .options(joinedload(LegalClauseModel.points))
                .where(
                    LegalClauseModel.article_id == article_id,
                    LegalClauseModel.clause_number == clause_number,
                )
            )
            result = session.scalar(stmt)
            if result:
                session.expunge(result)
            return result

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
            }

    def link_to_kg(self, element_id: str, kg_node_id: str, element_type: str) -> bool:
        """
        Link a DB element to a KG node (Phase 04).

        Args:
            element_id: UUID of the element
            kg_node_id: UUID of the KG node
            element_type: One of 'document', 'chapter', 'section', 'article', 'clause', 'point'

        Returns:
            True if successful
        """
        model_map = {
            "document": LegalDocumentModel,
            "chapter": LegalChapterModel,
            "section": LegalSectionModel,
            "article": LegalArticleModel,
            "clause": LegalClauseModel,
            "point": LegalPointModel,
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
