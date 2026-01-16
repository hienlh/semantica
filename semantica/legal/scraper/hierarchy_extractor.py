"""
Hierarchy extractor for Vietnamese legal documents.

Extracts hierarchical structure using regex patterns:
- Chương (Chapter): "Chương I", "Chương 1"
- Mục (Section): "Mục 1", "MỤC 1"
- Điều (Article): "Điều 1", "ĐIỀU 1"
- Khoản (Clause): "1.", "2."
- Điểm (Point): "a)", "b)", "đ)"
"""

import re
from typing import List, Optional, Tuple

from .base import LegalArticle, LegalChapter, LegalClause, LegalPoint, LegalSection


class HierarchyExtractor:
    """Extract hierarchical structure from Vietnamese legal text."""

    # Regex patterns for Vietnamese legal structure
    PATTERNS = {
        # Chapter: "Chương I", "Chương 1", "CHƯƠNG I"
        "chapter": re.compile(
            r"(?:^|\n)\s*(?:CHƯƠNG|Chương)\s+([IVXLC]+|\d+)[\.:\s]*\n*([^\n]*)",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Section: "Mục 1", "MỤC 1"
        "section": re.compile(
            r"(?:^|\n)\s*(?:MỤC|Mục)\s+(\d+)[\.:\s]*\n*([^\n]*)",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Article: "Điều 1", "ĐIỀU 1", "Điều 1."
        "article": re.compile(
            r"(?:^|\n)\s*(?:ĐIỀU|Điều)\s+(\d+)[\.:\s]*([^\n]*)",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Clause: "1. ", "2. " or just "1." at line start (content may be on next line)
        "clause": re.compile(r"^\s*(\d+)\.\s*(.*)", re.MULTILINE),
        # Point: "a) ", "b) ", "đ) " or just "a)" at line start
        "point": re.compile(r"^\s*([a-zđ])\)\s*(.*)", re.MULTILINE),
    }

    def extract(
        self, text: str
    ) -> Tuple[List[LegalChapter], List[LegalArticle]]:
        """
        Extract chapters and articles from legal text.

        Args:
            text: Full text content of the legal document

        Returns:
            Tuple of (chapters, standalone_articles)
            - chapters: List of LegalChapter with nested structure
            - standalone_articles: Articles not in any chapter
        """
        chapters: List[LegalChapter] = []
        standalone_articles: List[LegalArticle] = []

        # Find all chapters
        chapter_matches = list(self.PATTERNS["chapter"].finditer(text))

        if chapter_matches:
            for i, match in enumerate(chapter_matches):
                # Determine chapter content boundaries
                start = match.end()
                end = (
                    chapter_matches[i + 1].start()
                    if i + 1 < len(chapter_matches)
                    else len(text)
                )
                chapter_text = text[start:end]

                # Extract chapter title (may span multiple lines until first article)
                title = self._clean_title(match.group(2))

                # Create chapter with nested content
                chapter = LegalChapter(
                    number=match.group(1).strip(),
                    title=title,
                    raw_text=match.group(0) + chapter_text,
                )

                # Extract sections and articles within chapter
                chapter.sections, chapter.articles = self._extract_sections_and_articles(
                    chapter_text
                )
                chapters.append(chapter)
        else:
            # No chapters found, extract articles directly
            standalone_articles = self._extract_articles(text)

        return chapters, standalone_articles

    def _extract_sections_and_articles(
        self, text: str
    ) -> Tuple[List[LegalSection], List[LegalArticle]]:
        """
        Extract sections and direct articles from chapter text.

        Returns:
            Tuple of (sections, direct_articles)
        """
        sections: List[LegalSection] = []
        direct_articles: List[LegalArticle] = []

        section_matches = list(self.PATTERNS["section"].finditer(text))

        if section_matches:
            # Track content before first section for direct articles
            pre_section_text = text[: section_matches[0].start()]
            if pre_section_text.strip():
                direct_articles = self._extract_articles(pre_section_text)

            for i, match in enumerate(section_matches):
                start = match.end()
                end = (
                    section_matches[i + 1].start()
                    if i + 1 < len(section_matches)
                    else len(text)
                )
                section_text = text[start:end]

                section = LegalSection(
                    number=int(match.group(1)),
                    title=self._clean_title(match.group(2)),
                    articles=self._extract_articles(section_text),
                    raw_text=match.group(0) + section_text,
                )
                sections.append(section)
        else:
            # No sections, all articles are direct
            direct_articles = self._extract_articles(text)

        return sections, direct_articles

    def _extract_articles(self, text: str) -> List[LegalArticle]:
        """Extract articles (Điều) from text segment."""
        articles: List[LegalArticle] = []
        article_matches = list(self.PATTERNS["article"].finditer(text))

        for i, match in enumerate(article_matches):
            start = match.end()
            end = (
                article_matches[i + 1].start()
                if i + 1 < len(article_matches)
                else len(text)
            )
            article_text = text[start:end].strip()

            article = LegalArticle(
                number=int(match.group(1)),
                title=self._clean_title(match.group(2)),
                content=article_text,
                clauses=self._extract_clauses(article_text),
                raw_text=match.group(0) + article_text,
            )
            articles.append(article)

        return articles

    def _extract_clauses(self, text: str) -> List[LegalClause]:
        """
        Extract clauses (Khoản) from article text.

        Handles multi-line clause content and nested points.
        Also handles cases where content is on the next line after number.
        """
        clauses: List[LegalClause] = []
        lines = text.split("\n")
        current_clause: Optional[LegalClause] = None
        current_content: List[str] = []

        for line in lines:
            clause_match = self.PATTERNS["clause"].match(line)

            if clause_match:
                # Save previous clause
                if current_clause is not None:
                    content = "\n".join(current_content).strip()
                    current_clause.content = content
                    current_clause.raw_text = f"{current_clause.number}. {content}"
                    current_clause.points = self._extract_points(content)
                    clauses.append(current_clause)

                # Start new clause
                current_clause = LegalClause(
                    number=int(clause_match.group(1)),
                    content="",
                )
                # Content might be empty if on next line
                first_content = clause_match.group(2).strip()
                current_content = [first_content] if first_content else []
            elif current_clause is not None:
                # Add line to current clause content
                stripped = line.strip()
                if stripped:
                    current_content.append(stripped)

        # Save last clause
        if current_clause is not None:
            content = "\n".join(current_content).strip()
            current_clause.content = content
            current_clause.raw_text = f"{current_clause.number}. {content}"
            current_clause.points = self._extract_points(content)
            clauses.append(current_clause)

        return clauses

    def _extract_points(self, text: str) -> List[LegalPoint]:
        """
        Extract points (Điểm) from clause text.

        Handles Vietnamese letters including đ.
        Also handles cases where content is on the next line after letter.
        """
        points: List[LegalPoint] = []
        lines = text.split("\n")
        current_point: Optional[LegalPoint] = None
        current_content: List[str] = []

        for line in lines:
            point_match = self.PATTERNS["point"].match(line)

            if point_match:
                if current_point is not None:
                    content = "\n".join(current_content).strip()
                    current_point.content = content
                    current_point.raw_text = f"{current_point.letter}) {content}"
                    points.append(current_point)

                current_point = LegalPoint(
                    letter=point_match.group(1),
                    content="",
                )
                # Content might be empty if on next line
                first_content = point_match.group(2).strip()
                current_content = [first_content] if first_content else []
            elif current_point is not None:
                stripped = line.strip()
                if stripped:
                    current_content.append(stripped)

        if current_point is not None:
            content = "\n".join(current_content).strip()
            current_point.content = content
            current_point.raw_text = f"{current_point.letter}) {content}"
            points.append(current_point)

        return points

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title text."""
        if not title:
            return ""
        # Remove extra whitespace
        title = " ".join(title.split())
        # Remove leading punctuation
        title = title.lstrip(".:- ")
        return title.strip()

    def validate_structure(self, text: str) -> dict:
        """
        Validate extracted structure and return statistics.

        Returns:
            Dictionary with counts and potential issues
        """
        chapters, articles = self.extract(text)

        total_articles = len(articles)
        total_clauses = 0
        total_points = 0

        for chapter in chapters:
            total_articles += len(chapter.articles)
            for section in chapter.sections:
                total_articles += len(section.articles)
                for article in section.articles:
                    total_clauses += len(article.clauses)
                    for clause in article.clauses:
                        total_points += len(clause.points)

            for article in chapter.articles:
                total_clauses += len(article.clauses)
                for clause in article.clauses:
                    total_points += len(clause.points)

        for article in articles:
            total_clauses += len(article.clauses)
            for clause in article.clauses:
                total_points += len(clause.points)

        return {
            "chapters": len(chapters),
            "sections": sum(len(c.sections) for c in chapters),
            "articles": total_articles,
            "clauses": total_clauses,
            "points": total_points,
            "has_chapters": len(chapters) > 0,
            "standalone_articles": len(articles),
        }
