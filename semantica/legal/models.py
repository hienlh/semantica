"""
SQLAlchemy models for Vietnamese legal document storage.

Schema mirrors Phase 00 scraper output hierarchy:
Document > Chapter > Section > Article > Clause > Point

Each level can link to KG node via kg_node_id for Phase 04 integration.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class LegalDocumentModel(Base):
    """
    Legal document (Văn bản pháp luật).

    Maps to Phase 00: LegalDocument from scraper.base
    """

    __tablename__ = "legal_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    so_hieu = Column(String(100), nullable=False, index=True)  # "59/2020/QH14"
    title = Column(String(500), nullable=False)
    loai_van_ban = Column(String(50))  # 'Luật', 'Nghị định', 'Thông tư'
    co_quan_ban_hanh = Column(String(200))  # Issuing authority
    nguoi_ky = Column(String(200))  # Signatory
    ngay_ban_hanh = Column(Date)  # Issue date
    ngay_hieu_luc = Column(Date)  # Effective date
    tinh_trang = Column(String(100))  # Status
    raw_text = Column(Text)  # Full extracted text
    kg_node_id = Column(String(36), index=True)  # Link to KG (Phase 04)
    source_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chapters = relationship(
        "LegalChapterModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="LegalChapterModel.position",
    )

    __table_args__ = (Index("idx_doc_so_hieu", "so_hieu"),)


class LegalChapterModel(Base):
    """
    Chapter (Chương) within a legal document.

    Maps to Phase 00: LegalChapter
    """

    __tablename__ = "legal_chapters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(
        String(36), ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False
    )
    chapter_number = Column(String(20), nullable=False)  # Roman: "I", "II", "III"
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(String(36), index=True)
    position = Column(Integer, default=0)

    # Relationships
    document = relationship("LegalDocumentModel", back_populates="chapters")
    sections = relationship(
        "LegalSectionModel",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="LegalSectionModel.position",
    )
    articles = relationship(
        "LegalArticleModel",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="LegalArticleModel.position",
    )


class LegalSectionModel(Base):
    """
    Section (Mục) within a chapter.

    Maps to Phase 00: LegalSection
    """

    __tablename__ = "legal_sections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    chapter_id = Column(
        String(36), ForeignKey("legal_chapters.id", ondelete="CASCADE"), nullable=False
    )
    section_number = Column(Integer, nullable=False)
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(String(36), index=True)
    position = Column(Integer, default=0)

    # Relationships
    chapter = relationship("LegalChapterModel", back_populates="sections")
    articles = relationship(
        "LegalArticleModel",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="LegalArticleModel.position",
    )


class LegalArticleModel(Base):
    """
    Article (Điều) - primary legal unit.

    Maps to Phase 00: LegalArticle
    """

    __tablename__ = "legal_articles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(
        String(36), ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id = Column(
        String(36), ForeignKey("legal_chapters.id", ondelete="CASCADE"), nullable=True
    )
    section_id = Column(
        String(36), ForeignKey("legal_sections.id", ondelete="CASCADE"), nullable=True
    )
    article_number = Column(Integer, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    raw_text = Column(Text)
    kg_node_id = Column(String(36), index=True)
    position = Column(Integer, default=0)

    # Relationships
    document = relationship("LegalDocumentModel")
    chapter = relationship("LegalChapterModel", back_populates="articles")
    section = relationship("LegalSectionModel", back_populates="articles")
    clauses = relationship(
        "LegalClauseModel",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="LegalClauseModel.position",
    )

    __table_args__ = (
        Index("idx_article_number", "document_id", "article_number"),
        Index("idx_article_kg", "kg_node_id"),
    )


class LegalClauseModel(Base):
    """
    Clause (Khoản) within an article.

    Maps to Phase 00: LegalClause
    """

    __tablename__ = "legal_clauses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    article_id = Column(
        String(36), ForeignKey("legal_articles.id", ondelete="CASCADE"), nullable=False
    )
    clause_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(String(36), index=True)
    position = Column(Integer, default=0)

    # Relationships
    article = relationship("LegalArticleModel", back_populates="clauses")
    points = relationship(
        "LegalPointModel",
        back_populates="clause",
        cascade="all, delete-orphan",
        order_by="LegalPointModel.position",
    )


class LegalPointModel(Base):
    """
    Point (Điểm) within a clause.

    Maps to Phase 00: LegalPoint
    """

    __tablename__ = "legal_points"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clause_id = Column(
        String(36), ForeignKey("legal_clauses.id", ondelete="CASCADE"), nullable=False
    )
    point_letter = Column(String(5), nullable=False)  # "a", "b", "đ"
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(String(36), index=True)
    position = Column(Integer, default=0)

    # Relationships
    clause = relationship("LegalClauseModel", back_populates="points")


class LegalCrossReferenceModel(Base):
    """
    Cross-reference between articles (Phase 03).

    Stores detected "theo Điều X Luật Y" references.
    """

    __tablename__ = "legal_cross_references"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_article_id = Column(
        String(36), ForeignKey("legal_articles.id", ondelete="CASCADE")
    )
    target_article_id = Column(
        String(36), ForeignKey("legal_articles.id", ondelete="SET NULL"), nullable=True
    )
    target_document_so_hieu = Column(String(100), nullable=True)  # For external refs
    reference_text = Column(Text)  # "theo Điều 5 Luật 20/2014"
    reference_type = Column(String(50), default="references")  # references/amends/supersedes
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_article = relationship(
        "LegalArticleModel", foreign_keys=[source_article_id]
    )
    target_article = relationship(
        "LegalArticleModel", foreign_keys=[target_article_id]
    )
