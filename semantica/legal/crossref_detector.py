"""
Cross-reference detector for Vietnamese legal documents.

Detects patterns like:
- "theo Điều X Luật số Y"
- "căn cứ Điều X"
- "quy định tại Điều X, Khoản Y"

Simplified implementation for Phase 03 (YAGNI - skip full NER).
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from .models import LegalCrossReferenceModel, make_crossref_id


@dataclass
class CrossReference:
    """Detected cross-reference in legal text."""

    source_article_id: str
    target_article_num: int
    target_clause_num: Optional[int]
    target_point_letter: Optional[str]
    target_so_hieu: Optional[str]  # Target document number
    reference_text: str
    reference_type: str  # 'references', 'amends', 'supersedes'
    confidence: float
    start_pos: int
    end_pos: int


class CrossReferenceDetector:
    """
    Detect cross-references in Vietnamese legal text.

    Usage:
        detector = CrossReferenceDetector()
        refs = detector.detect(
            text="Theo Điều 5, Khoản 2 Luật số 59/2020/QH14...",
            source_article_id="uuid-123",
            current_so_hieu="01/2021/ND"
        )
    """

    # Reference patterns with named groups
    # Ordered by specificity (most specific first)
    PATTERNS = [
        # Full reference: "theo Điều X, Khoản Y, Điểm Z Luật số ABC"
        (
            r"(?:theo|căn\s+cứ|quy\s+định\s+(?:tại)?|áp\s+dụng)\s+"
            r"Điều\s+(?P<article>\d+)"
            r"(?:[,\s]+Khoản\s+(?P<clause>\d+))?"
            r"(?:[,\s]+Điểm\s+(?P<point>[a-zđ]))?"
            r"(?:\s+(?:Luật|Nghị\s+định|Thông\s+tư)\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Za-z0-9-]+))?",
            "references",
            0.95,
        ),
        # Amendment: "được sửa đổi bởi Điều X"
        (
            r"(?:được\s+)?(?:sửa\s+đổi|bổ\s+sung)\s+(?:bởi|theo|tại)\s+"
            r"Điều\s+(?P<article>\d+)"
            r"(?:\s+(?:Luật|Nghị\s+định)\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Za-z0-9-]+))?",
            "amends",
            0.90,
        ),
        # Supersedes: "thay thế Điều X"
        (
            r"thay\s+thế\s+(?:cho\s+)?"
            r"Điều\s+(?P<article>\d+)"
            r"(?:\s+(?:Luật|Nghị\s+định)\s+(?:số\s+)?(?P<law>\d+/\d{4}/[A-Za-z0-9-]+))?",
            "supersedes",
            0.90,
        ),
        # Simple reference in context: "tại Điều X" or "của Điều X"
        (
            r"(?:tại|của|theo)\s+Điều\s+(?P<article>\d+)"
            r"(?:[,\s]+Khoản\s+(?P<clause>\d+))?",
            "references",
            0.75,
        ),
    ]

    def detect(
        self,
        text: str,
        source_article_id: str,
        current_so_hieu: Optional[str] = None,
    ) -> List[CrossReference]:
        """
        Detect cross-references in text.

        Args:
            text: Article or clause text to analyze
            source_article_id: UUID of source article
            current_so_hieu: Current document's số hiệu (for context)

        Returns:
            List of detected CrossReference objects
        """
        references = []
        seen_spans = set()

        for pattern, ref_type, base_confidence in self.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
                start, end = match.start(), match.end()

                # Skip overlapping matches
                if any(
                    start < s_end and end > s_start for s_start, s_end in seen_spans
                ):
                    continue

                seen_spans.add((start, end))
                groups = match.groupdict()

                # Extract article number
                article_num = int(groups.get("article") or 0)
                if not article_num:
                    continue

                # Extract optional clause/point
                clause_num = int(groups["clause"]) if groups.get("clause") else None
                point_letter = groups.get("point")

                # Target document (use explicit or current)
                target_so_hieu = groups.get("law") or None

                # Adjust confidence based on specificity
                confidence = base_confidence
                if target_so_hieu:
                    confidence = min(confidence + 0.05, 1.0)
                if clause_num:
                    confidence = min(confidence + 0.02, 1.0)

                ref = CrossReference(
                    source_article_id=source_article_id,
                    target_article_num=article_num,
                    target_clause_num=clause_num,
                    target_point_letter=point_letter,
                    target_so_hieu=target_so_hieu,
                    reference_text=match.group(0).strip(),
                    reference_type=ref_type,
                    confidence=confidence,
                    start_pos=start,
                    end_pos=end,
                )
                references.append(ref)

        return sorted(references, key=lambda r: r.start_pos)

    def detect_in_document(
        self,
        db,  # LegalDocumentDB
        doc_id: str,
    ) -> List[CrossReference]:
        """
        Detect all cross-references in a document's articles.

        Args:
            db: LegalDocumentDB instance
            doc_id: Document ID to process

        Returns:
            List of all detected cross-references
        """
        from sqlalchemy import select

        from .models import LegalArticleModel, LegalDocumentModel

        all_refs = []

        with db.SessionLocal() as session:
            # Get document
            doc = session.get(LegalDocumentModel, doc_id)
            if not doc:
                return []

            # Get all articles
            stmt = select(LegalArticleModel).where(
                LegalArticleModel.document_id == doc_id
            )
            articles = session.scalars(stmt).all()

            for article in articles:
                # Detect in article content
                if article.content:
                    refs = self.detect(
                        text=article.content,
                        source_article_id=article.id,
                        current_so_hieu=doc.so_hieu,
                    )
                    all_refs.extend(refs)

        return all_refs


def store_cross_references(
    db,  # LegalDocumentDB
    references: List[CrossReference],
) -> int:
    """
    Store detected cross-references in database.

    Args:
        db: LegalDocumentDB instance
        references: List of CrossReference to store

    Returns:
        Number of references stored
    """
    from sqlalchemy import select

    from .models import LegalArticleModel, LegalCrossReferenceModel, LegalDocumentModel

    stored = 0

    with db.SessionLocal() as session:
        ref_index = 0  # Global index for unique IDs

        for ref in references:
            # Try to resolve target article
            target_article_id = None

            if ref.target_so_hieu:
                # Find target in another document
                stmt = (
                    select(LegalArticleModel)
                    .join(LegalDocumentModel)
                    .where(
                        LegalDocumentModel.so_hieu == ref.target_so_hieu,
                        LegalArticleModel.article_number == ref.target_article_num,
                    )
                )
                target = session.scalar(stmt)
                if target:
                    target_article_id = target.id
            else:
                # Find target in same document
                source = session.get(LegalArticleModel, ref.source_article_id)
                if source:
                    stmt = select(LegalArticleModel).where(
                        LegalArticleModel.document_id == source.document_id,
                        LegalArticleModel.article_number == ref.target_article_num,
                    )
                    target = session.scalar(stmt)
                    if target:
                        target_article_id = target.id

            # Generate hierarchical ID with unique index
            crossref_id = make_crossref_id(
                ref.source_article_id, target_article_id, ref_index
            )
            ref_index += 1

            # Create cross-reference record
            crossref = LegalCrossReferenceModel(
                id=crossref_id,
                source_article_id=ref.source_article_id,
                target_article_id=target_article_id,
                target_document_so_hieu=ref.target_so_hieu,
                reference_text=ref.reference_text,
                reference_type=ref.reference_type,
                confidence=ref.confidence,
            )
            session.add(crossref)
            stored += 1

        session.commit()

    return stored
