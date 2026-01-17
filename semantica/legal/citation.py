"""
Legal citation formatter for Vietnamese law.

Formats citations like: "Điều X, Khoản Y, Điểm Z - Luật ABC số 123/2020/QH14"
"""

from typing import Optional

from .models import (
    LegalArticleModel,
    LegalClauseModel,
    LegalDocumentModel,
    LegalPointModel,
)


class LegalCitationFormatter:
    """
    Format legal citations from database models.

    Usage:
        formatter = LegalCitationFormatter()
        citation = formatter.format_article(article, document)
        # "Điều 5, Luật Doanh nghiệp số 59/2020/QH14"
    """

    def format_document(self, doc: LegalDocumentModel) -> str:
        """Format document citation."""
        # Use title if available, otherwise construct from type + number
        if doc.title:
            return doc.title
        parts = []
        if doc.loai_van_ban:
            parts.append(doc.loai_van_ban)
        if doc.so_hieu:
            parts.append(f"số {doc.so_hieu}")
        return " ".join(parts) if parts else doc.so_hieu

    def format_article(
        self,
        article: LegalArticleModel,
        doc: Optional[LegalDocumentModel] = None,
    ) -> str:
        """
        Format article citation.

        Args:
            article: Article model
            doc: Optional document model for full citation

        Returns:
            Citation string like "Điều 5 - Luật số 59/2020/QH14"
        """
        citation = f"Điều {article.article_number}"
        if article.title:
            citation += f". {article.title}"
        if doc:
            citation += f" - {self.format_document(doc)}"
        return citation

    def format_clause(
        self,
        clause: LegalClauseModel,
        article: Optional[LegalArticleModel] = None,
        doc: Optional[LegalDocumentModel] = None,
    ) -> str:
        """
        Format clause citation.

        Returns:
            Citation like "Khoản 2, Điều 5 - Luật số 59/2020/QH14"
        """
        citation = f"Khoản {clause.clause_number}"
        if article:
            citation += f", Điều {article.article_number}"
        if doc:
            citation += f" - {self.format_document(doc)}"
        return citation

    def format_point(
        self,
        point: LegalPointModel,
        clause: Optional[LegalClauseModel] = None,
        article: Optional[LegalArticleModel] = None,
        doc: Optional[LegalDocumentModel] = None,
    ) -> str:
        """
        Format point citation.

        Returns:
            Citation like "Điểm a, Khoản 2, Điều 5 - Luật số 59/2020/QH14"
        """
        citation = f"Điểm {point.point_letter}"
        if clause:
            citation += f", Khoản {clause.clause_number}"
        if article:
            citation += f", Điều {article.article_number}"
        if doc:
            citation += f" - {self.format_document(doc)}"
        return citation

    def format_full(
        self,
        article_number: int,
        clause_number: Optional[int] = None,
        point_letter: Optional[str] = None,
        so_hieu: Optional[str] = None,
        loai_van_ban: Optional[str] = None,
    ) -> str:
        """
        Format citation from raw values.

        Args:
            article_number: Article number (Điều)
            clause_number: Optional clause number (Khoản)
            point_letter: Optional point letter (Điểm)
            so_hieu: Document number
            loai_van_ban: Document type

        Returns:
            Full citation string
        """
        parts = []

        if point_letter:
            parts.append(f"Điểm {point_letter}")
        if clause_number:
            parts.append(f"Khoản {clause_number}")
        parts.append(f"Điều {article_number}")

        citation = ", ".join(parts)

        if so_hieu:
            doc_part = loai_van_ban or ""
            if doc_part:
                doc_part += " "
            doc_part += f"số {so_hieu}"
            citation += f" - {doc_part}"

        return citation
