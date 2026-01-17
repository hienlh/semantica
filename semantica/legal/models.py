"""
SQLAlchemy models for Vietnamese legal document storage.

Schema mirrors Phase 00 scraper output hierarchy:
Document > Chương > Mục > Điều > Khoản > Điểm

================================================================================
HIERARCHICAL ID FORMAT - HƯỚNG DẪN ĐỌC HIỂU
================================================================================

Mỗi ID được xây dựng theo cấu trúc phân cấp, dễ đọc và tự giải thích.

VIẾT TẮT (Vietnamese abbreviations):
    c  = Chương (Chapter)
    m  = Mục (Section)
    d  = Điều (Article)
    k  = Khoản (Clause)
    pl = Phụ lục (Appendix)
    mk = Mục/Khoản trong phụ lục (Appendix item)
    :  = phân cách cấp bậc
    .  = đánh dấu bản sao (duplicate)
    →  = tham chiếu chéo (cross-reference)
    #  = index của cross-reference

CẤU TRÚC ID:

    Level       | Format                    | Ví dụ
    ------------|---------------------------|----------------------------------
    Văn bản     | {so_hieu_normalized}      | 59-2020-QH14
    Chương      | {doc}:c{num}              | 59-2020-QH14:c1
    Mục         | {chap}:m{num}             | 59-2020-QH14:c1:m2
    Điều        | {doc}:d{num}              | 59-2020-QH14:d5
    Khoản       | {article}:k{num}          | 59-2020-QH14:d5:k1
    Điểm        | {clause}:{letter}         | 59-2020-QH14:d5:k1:a
    Phụ lục     | {doc}:pl{num}             | 89-2024-ND:pl1
    Mục trong PL| {pl}:mk{num}              | 89-2024-ND:pl1:mk3
    CrossRef    | {source}→{target}#{idx}   | 59-2020-QH14:d5→59-2020-QH14:d10#0

CÁCH ĐỌC ID:

    ID: "59-2020-QH14:d5:k1:a"
    ├── 59-2020-QH14  = Luật số 59/2020/QH14
    ├── :d5           = Điều 5
    ├── :k1           = Khoản 1
    └── :a            = Điểm a

    → Đọc: "Điểm a, Khoản 1, Điều 5, Luật 59/2020/QH14"

    ID: "89-2024-ND:pl1:mk3"
    ├── 89-2024-ND    = Nghị định số 89/2024/NĐ-CP
    ├── :pl1          = Phụ lục I
    └── :mk3          = Mục 3 trong phụ lục

    → Đọc: "Mục 3, Phụ lục I, Nghị định 89/2024/NĐ-CP"

XỬ LÝ TRÙNG LẶP (Duplicates):

    Một số văn bản có Phụ lục chứa các điều khoản trùng số.
    Sử dụng suffix ".N" để phân biệt:

    - 89-2024-ND:d5      = Điều 5 chính văn
    - 89-2024-ND:d5.2    = Điều 5 trong Phụ lục (lần xuất hiện thứ 2)

CROSS-REFERENCE:

    ID: "59-2020-QH14:d4→59-2020-QH14:d88#0"
    ├── 59-2020-QH14:d4   = Nguồn: Điều 4
    ├── →                  = tham chiếu đến
    ├── 59-2020-QH14:d88  = Đích: Điều 88
    └── #0                 = index (phân biệt nhiều ref cùng source→target)

    Nếu không resolve được đích:
    - 59-2020-QH14:d4→ext#0 = tham chiếu đến văn bản bên ngoài

ƯU ĐIỂM:
    1. Human-readable: Nhìn ID biết ngay vị trí trong văn bản
    2. Self-documenting: Không cần tra cứu thêm để hiểu
    3. Natural sort: Sắp xếp alphabet = sắp xếp theo thứ tự văn bản
    4. Easy query: WHERE id LIKE '59-2020-QH14:d5%' để lấy mọi khoản/điểm

================================================================================
"""

import re
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


# =============================================================================
# ID Generation Helpers
# =============================================================================


def normalize_so_hieu(so_hieu: str) -> str:
    """
    Normalize số hiệu for use as document ID.

    Examples:
        "59/2020/QH14" → "59-2020-QH14"
        "89/2024/NĐ-CP" → "89-2024-ND-CP"
    """
    # Replace / with -
    normalized = so_hieu.replace("/", "-")
    # Remove Vietnamese diacritics from common abbreviations
    normalized = normalized.replace("Đ", "D").replace("đ", "d")
    # Remove any other special characters except - and alphanumeric
    normalized = re.sub(r"[^a-zA-Z0-9\-]", "", normalized)
    return normalized


def make_document_id(so_hieu: str) -> str:
    """Generate document ID from số hiệu."""
    return normalize_so_hieu(so_hieu)


def make_chapter_id(doc_id: str, chapter_number: str | int) -> str:
    """
    Generate chapter ID.

    Args:
        doc_id: Document ID (normalized số hiệu)
        chapter_number: Roman numeral or integer (I, II, 1, 2)

    Returns:
        "{doc_id}:c{num}" e.g. "59-2020-QH14:c1"
    """
    # Convert Roman numerals to Arabic if needed
    num = _roman_to_int(str(chapter_number)) if isinstance(chapter_number, str) else chapter_number
    return f"{doc_id}:c{num}"


def make_section_id(doc_id: str, chapter_number: str | int, section_number: int) -> str:
    """
    Generate section (mục) ID.

    Returns:
        "{doc_id}:c{chap}:m{section}" e.g. "59-2020-QH14:c1:m2"
    """
    chap_num = _roman_to_int(str(chapter_number)) if isinstance(chapter_number, str) else chapter_number
    return f"{doc_id}:c{chap_num}:m{section_number}"


def make_article_id(doc_id: str, article_number: int) -> str:
    """
    Generate article (điều) ID.

    Returns:
        "{doc_id}:d{num}" e.g. "59-2020-QH14:d5"
    """
    return f"{doc_id}:d{article_number}"


def make_clause_id(article_id: str, clause_number: int) -> str:
    """
    Generate clause (khoản) ID.

    Returns:
        "{article_id}:k{num}" e.g. "59-2020-QH14:d5:k1"
    """
    return f"{article_id}:k{clause_number}"


def make_point_id(clause_id: str, point_letter: str) -> str:
    """
    Generate point (điểm) ID.

    Returns:
        "{clause_id}:{letter}" e.g. "59-2020-QH14:d5:k1:a"
    """
    return f"{clause_id}:{point_letter}"


def make_crossref_id(source_article_id: str, target_article_id: Optional[str], index: int) -> str:
    """
    Generate cross-reference ID.

    Args:
        source_article_id: Source article ID
        target_article_id: Target article ID (None for unresolved)
        index: Unique index for this reference (handles duplicates)

    Returns:
        "{source}→{target}#{index}" or "{source}→ext#{index}" for unresolved refs
    """
    if target_article_id:
        return f"{source_article_id}→{target_article_id}#{index}"
    return f"{source_article_id}→ext#{index}"


def make_appendix_id(doc_id: str, appendix_number: str | int) -> str:
    """
    Generate appendix (phụ lục) ID.

    Args:
        doc_id: Document ID (normalized số hiệu)
        appendix_number: Roman numeral or integer (I, II, 1, 2) or empty for single appendix

    Returns:
        "{doc_id}:pl{num}" e.g. "89-2024-ND:pl1"
    """
    if not appendix_number:
        return f"{doc_id}:pl1"
    num = _roman_to_int(str(appendix_number)) if isinstance(appendix_number, str) else appendix_number
    return f"{doc_id}:pl{num}"


def make_appendix_item_id(appendix_id: str, item_number: int) -> str:
    """
    Generate appendix item (mục trong phụ lục) ID.

    Returns:
        "{appendix_id}:mk{num}" e.g. "89-2024-ND:pl1:mk3"
    """
    return f"{appendix_id}:mk{item_number}"


def _roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer. Returns input as int if already numeric."""
    roman = roman.strip().upper()
    if roman.isdigit():
        return int(roman)

    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for char in reversed(roman):
        curr = values.get(char, 0)
        if curr < prev:
            result -= curr
        else:
            result += curr
        prev = curr
    return result if result > 0 else 1


# =============================================================================
# SQLAlchemy Models
# =============================================================================


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class LegalDocumentModel(Base):
    """
    Legal document (Văn bản pháp luật).

    ID Format: normalized số hiệu → "59-2020-QH14"
    """

    __tablename__ = "legal_documents"

    id = Column(String(100), primary_key=True)  # normalized so_hieu
    so_hieu = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    loai_van_ban = Column(String(50))  # 'Luật', 'Nghị định', 'Thông tư'
    co_quan_ban_hanh = Column(String(200))
    nguoi_ky = Column(String(200))
    ngay_ban_hanh = Column(Date)
    ngay_hieu_luc = Column(Date)
    tinh_trang = Column(String(100))
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)  # Link to KG (Phase 04)
    source_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chapters = relationship(
        "LegalChapterModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="LegalChapterModel.position",
    )


class LegalChapterModel(Base):
    """
    Chapter (Chương) within a legal document.

    ID Format: "{doc_id}:c{num}" → "59-2020-QH14:c1"
    """

    __tablename__ = "legal_chapters"

    id = Column(String(120), primary_key=True)  # doc:c{num}
    document_id = Column(
        String(100), ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False
    )
    chapter_number = Column(String(20), nullable=False)  # Original: "I", "II"
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
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

    ID Format: "{doc_id}:c{chap}:m{num}" → "59-2020-QH14:c1:m2"
    """

    __tablename__ = "legal_sections"

    id = Column(String(130), primary_key=True)  # doc:c{chap}:m{num}
    chapter_id = Column(
        String(120), ForeignKey("legal_chapters.id", ondelete="CASCADE"), nullable=False
    )
    section_number = Column(Integer, nullable=False)
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
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

    ID Format: "{doc_id}:d{num}" → "59-2020-QH14:d5"
    """

    __tablename__ = "legal_articles"

    id = Column(String(120), primary_key=True)  # doc:d{num}
    document_id = Column(
        String(100), ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id = Column(
        String(120), ForeignKey("legal_chapters.id", ondelete="CASCADE"), nullable=True
    )
    section_id = Column(
        String(130), ForeignKey("legal_sections.id", ondelete="CASCADE"), nullable=True
    )
    article_number = Column(Integer, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
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
        Index("idx_article_doc_num", "document_id", "article_number"),
        Index("idx_article_kg", "kg_node_id"),
    )


class LegalClauseModel(Base):
    """
    Clause (Khoản) within an article.

    ID Format: "{article_id}:k{num}" → "59-2020-QH14:d5:k1"
    """

    __tablename__ = "legal_clauses"

    id = Column(String(130), primary_key=True)  # article:k{num}
    article_id = Column(
        String(120), ForeignKey("legal_articles.id", ondelete="CASCADE"), nullable=False
    )
    clause_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
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

    ID Format: "{clause_id}:{letter}" → "59-2020-QH14:d5:k1:a"
    """

    __tablename__ = "legal_points"

    id = Column(String(140), primary_key=True)  # clause:{letter}
    clause_id = Column(
        String(130), ForeignKey("legal_clauses.id", ondelete="CASCADE"), nullable=False
    )
    point_letter = Column(String(5), nullable=False)  # "a", "b", "đ"
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
    position = Column(Integer, default=0)

    # Relationships
    clause = relationship("LegalClauseModel", back_populates="points")


class LegalCrossReferenceModel(Base):
    """
    Cross-reference between articles (Phase 03).

    ID Format: "{source}→{target}" → "59-2020-QH14:d5:k1→59-2020-QH14:d10"
    """

    __tablename__ = "legal_cross_references"

    id = Column(String(300), primary_key=True)  # source→target
    source_article_id = Column(
        String(120), ForeignKey("legal_articles.id", ondelete="CASCADE")
    )
    target_article_id = Column(
        String(120), ForeignKey("legal_articles.id", ondelete="SET NULL"), nullable=True
    )
    target_document_so_hieu = Column(String(100), nullable=True)  # For external refs
    reference_text = Column(Text)  # "theo Điều 5 Luật 20/2014"
    reference_type = Column(String(50), default="references")
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_article = relationship(
        "LegalArticleModel", foreign_keys=[source_article_id]
    )
    target_article = relationship(
        "LegalArticleModel", foreign_keys=[target_article_id]
    )


class LegalAppendixModel(Base):
    """
    Appendix (Phụ lục) within a legal document.

    ID Format: "{doc_id}:pl{num}" → "89-2024-ND:pl1"
    """

    __tablename__ = "legal_appendices"

    id = Column(String(120), primary_key=True)  # doc:pl{num}
    document_id = Column(
        String(100), ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False
    )
    appendix_number = Column(String(20), nullable=False)  # Original: "I", "II", "1"
    title = Column(String(500))
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
    position = Column(Integer, default=0)

    # Relationships
    document = relationship("LegalDocumentModel")
    items = relationship(
        "LegalAppendixItemModel",
        back_populates="appendix",
        cascade="all, delete-orphan",
        order_by="LegalAppendixItemModel.position",
    )


class LegalAppendixItemModel(Base):
    """
    Item (Mục) within an appendix.

    ID Format: "{appendix_id}:mk{num}" → "89-2024-ND:pl1:mk3"
    """

    __tablename__ = "legal_appendix_items"

    id = Column(String(140), primary_key=True)  # appendix:mk{num}
    appendix_id = Column(
        String(120), ForeignKey("legal_appendices.id", ondelete="CASCADE"), nullable=False
    )
    item_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    raw_text = Column(Text)
    kg_node_id = Column(String(100), index=True)
    position = Column(Integer, default=0)

    # Relationships
    appendix = relationship("LegalAppendixModel", back_populates="items")
