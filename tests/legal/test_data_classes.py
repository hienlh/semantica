"""
Tests for legal document data classes.

Tests serialization, properties, and enums for:
- LegalDocument
- LegalChapter
- LegalSection
- LegalArticle
- LegalClause
- LegalPoint
"""

import unittest
from datetime import datetime

from semantica.legal.scraper.base import (
    DocumentStatus,
    DocumentType,
    LegalArticle,
    LegalChapter,
    LegalClause,
    LegalDocument,
    LegalPoint,
    LegalSection,
)


class TestLegalPoint(unittest.TestCase):
    """Test LegalPoint data class."""

    def test_create_point(self):
        """Test creating a LegalPoint."""
        point = LegalPoint(
            letter="a",
            content="Giấy đề nghị đăng ký doanh nghiệp",
            raw_text="a) Giấy đề nghị đăng ký doanh nghiệp",
        )

        self.assertEqual(point.letter, "a")
        self.assertEqual(point.content, "Giấy đề nghị đăng ký doanh nghiệp")

    def test_point_to_dict(self):
        """Test LegalPoint serialization."""
        point = LegalPoint(letter="đ", content="Điểm đ nội dung")

        result = point.to_dict()

        self.assertEqual(result["letter"], "đ")
        self.assertEqual(result["content"], "Điểm đ nội dung")
        self.assertIn("raw_text", result)


class TestLegalClause(unittest.TestCase):
    """Test LegalClause data class."""

    def test_create_clause(self):
        """Test creating a LegalClause."""
        clause = LegalClause(
            number=1,
            content="Tự do kinh doanh ngành, nghề mà luật không cấm.",
        )

        self.assertEqual(clause.number, 1)
        self.assertEqual(clause.content, "Tự do kinh doanh ngành, nghề mà luật không cấm.")
        self.assertEqual(clause.points, [])

    def test_clause_with_points(self):
        """Test LegalClause with nested points."""
        points = [
            LegalPoint(letter="a", content="Điểm a"),
            LegalPoint(letter="b", content="Điểm b"),
        ]
        clause = LegalClause(number=1, content="Các trường hợp:", points=points)

        self.assertEqual(len(clause.points), 2)
        self.assertEqual(clause.points[0].letter, "a")

    def test_clause_to_dict(self):
        """Test LegalClause serialization with points."""
        clause = LegalClause(
            number=2,
            content="Khoản 2",
            points=[LegalPoint(letter="a", content="Điểm a")],
        )

        result = clause.to_dict()

        self.assertEqual(result["number"], 2)
        self.assertEqual(len(result["points"]), 1)
        self.assertEqual(result["points"][0]["letter"], "a")


class TestLegalArticle(unittest.TestCase):
    """Test LegalArticle data class."""

    def test_create_article(self):
        """Test creating a LegalArticle."""
        article = LegalArticle(
            number=1,
            title="Phạm vi điều chỉnh",
            content="Luật này quy định về việc thành lập...",
        )

        self.assertEqual(article.number, 1)
        self.assertEqual(article.title, "Phạm vi điều chỉnh")
        self.assertEqual(article.clauses, [])

    def test_article_with_clauses(self):
        """Test LegalArticle with nested clauses."""
        clauses = [
            LegalClause(number=1, content="Khoản 1"),
            LegalClause(number=2, content="Khoản 2"),
        ]
        article = LegalArticle(
            number=4,
            title="Quyền của doanh nghiệp",
            content="Full content",
            clauses=clauses,
        )

        self.assertEqual(len(article.clauses), 2)

    def test_article_to_dict(self):
        """Test LegalArticle serialization."""
        article = LegalArticle(
            number=10,
            title="Điều 10",
            content="Nội dung",
            clauses=[
                LegalClause(
                    number=1,
                    content="Khoản 1",
                    points=[LegalPoint(letter="a", content="Điểm a")],
                )
            ],
        )

        result = article.to_dict()

        self.assertEqual(result["number"], 10)
        self.assertEqual(result["title"], "Điều 10")
        self.assertEqual(len(result["clauses"]), 1)
        self.assertEqual(len(result["clauses"][0]["points"]), 1)


class TestLegalSection(unittest.TestCase):
    """Test LegalSection data class."""

    def test_create_section(self):
        """Test creating a LegalSection."""
        section = LegalSection(
            number=1,
            title="CÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN",
        )

        self.assertEqual(section.number, 1)
        self.assertEqual(section.articles, [])

    def test_section_with_articles(self):
        """Test LegalSection with nested articles."""
        articles = [
            LegalArticle(number=46, title="Điều 46", content="Content"),
            LegalArticle(number=47, title="Điều 47", content="Content"),
        ]
        section = LegalSection(
            number=1,
            title="MỤC 1",
            articles=articles,
        )

        self.assertEqual(len(section.articles), 2)

    def test_section_to_dict(self):
        """Test LegalSection serialization."""
        section = LegalSection(
            number=2,
            title="Mục 2",
            articles=[LegalArticle(number=74, title="Điều 74", content="Content")],
        )

        result = section.to_dict()

        self.assertEqual(result["number"], 2)
        self.assertEqual(len(result["articles"]), 1)


class TestLegalChapter(unittest.TestCase):
    """Test LegalChapter data class."""

    def test_create_chapter_roman(self):
        """Test creating a LegalChapter with Roman numeral."""
        chapter = LegalChapter(
            number="I",
            title="NHỮNG QUY ĐỊNH CHUNG",
        )

        self.assertEqual(chapter.number, "I")
        self.assertEqual(chapter.sections, [])
        self.assertEqual(chapter.articles, [])

    def test_create_chapter_arabic(self):
        """Test creating a LegalChapter with Arabic numeral."""
        chapter = LegalChapter(
            number="1",
            title="QUY ĐỊNH CHUNG",
        )

        self.assertEqual(chapter.number, "1")

    def test_chapter_with_sections(self):
        """Test LegalChapter with nested sections."""
        sections = [
            LegalSection(number=1, title="Mục 1"),
            LegalSection(number=2, title="Mục 2"),
        ]
        chapter = LegalChapter(
            number="III",
            title="CÔNG TY TRÁCH NHIỆM HỮU HẠN",
            sections=sections,
        )

        self.assertEqual(len(chapter.sections), 2)

    def test_chapter_with_direct_articles(self):
        """Test LegalChapter with direct articles (no sections)."""
        articles = [
            LegalArticle(number=1, title="Điều 1", content="Content"),
            LegalArticle(number=2, title="Điều 2", content="Content"),
        ]
        chapter = LegalChapter(
            number="I",
            title="QUY ĐỊNH CHUNG",
            articles=articles,
        )

        self.assertEqual(len(chapter.articles), 2)

    def test_chapter_to_dict(self):
        """Test LegalChapter serialization."""
        chapter = LegalChapter(
            number="II",
            title="THÀNH LẬP DOANH NGHIỆP",
            articles=[LegalArticle(number=16, title="Điều 16", content="Content")],
            sections=[LegalSection(number=1, title="Mục 1")],
        )

        result = chapter.to_dict()

        self.assertEqual(result["number"], "II")
        self.assertEqual(len(result["articles"]), 1)
        self.assertEqual(len(result["sections"]), 1)


class TestLegalDocument(unittest.TestCase):
    """Test LegalDocument data class."""

    def test_create_document_minimal(self):
        """Test creating a minimal LegalDocument."""
        doc = LegalDocument(
            url="https://thuvienphapluat.vn/test",
            so_hieu="59/2020/QH14",
            title="Luật Doanh nghiệp",
        )

        self.assertEqual(doc.so_hieu, "59/2020/QH14")
        self.assertEqual(doc.chapters, [])
        self.assertEqual(doc.articles, [])
        self.assertTrue(doc.is_complete)

    def test_create_document_full(self):
        """Test creating a full LegalDocument."""
        doc = LegalDocument(
            url="https://thuvienphapluat.vn/test",
            so_hieu="59/2020/QH14",
            title="Luật Doanh nghiệp 2020",
            loai_van_ban="Luật",
            co_quan_ban_hanh="Quốc hội",
            nguoi_ky="Nguyễn Thị Kim Ngân",
            ngay_ban_hanh=datetime(2020, 6, 17),
            ngay_hieu_luc=datetime(2021, 1, 1),
            tinh_trang="Còn hiệu lực",
        )

        self.assertEqual(doc.loai_van_ban, "Luật")
        self.assertEqual(doc.co_quan_ban_hanh, "Quốc hội")
        self.assertEqual(doc.ngay_ban_hanh, datetime(2020, 6, 17))

    def test_document_total_articles(self):
        """Test total_articles property calculation."""
        # Create nested structure
        chapter1_articles = [
            LegalArticle(number=1, title="Điều 1", content="Content"),
            LegalArticle(number=2, title="Điều 2", content="Content"),
        ]
        section_articles = [
            LegalArticle(number=46, title="Điều 46", content="Content"),
        ]
        chapter2_sections = [
            LegalSection(number=1, title="Mục 1", articles=section_articles),
        ]
        standalone_articles = [
            LegalArticle(number=200, title="Điều 200", content="Content"),
        ]

        doc = LegalDocument(
            url="test",
            so_hieu="test",
            title="Test",
            chapters=[
                LegalChapter(number="I", title="Chương I", articles=chapter1_articles),
                LegalChapter(number="II", title="Chương II", sections=chapter2_sections),
            ],
            articles=standalone_articles,
        )

        # 2 (chapter1) + 1 (section in chapter2) + 1 (standalone) = 4
        self.assertEqual(doc.total_articles, 4)

    def test_document_type_enum(self):
        """Test document_type_enum property."""
        doc = LegalDocument(
            url="test",
            so_hieu="test",
            title="Test",
            loai_van_ban="Luật",
        )
        self.assertEqual(doc.document_type_enum, DocumentType.LUAT)

        doc.loai_van_ban = "Nghị định"
        self.assertEqual(doc.document_type_enum, DocumentType.NGHI_DINH)

        doc.loai_van_ban = "Thông tư"
        self.assertEqual(doc.document_type_enum, DocumentType.THONG_TU)

        doc.loai_van_ban = "Unknown type"
        self.assertEqual(doc.document_type_enum, DocumentType.UNKNOWN)

    def test_document_to_dict(self):
        """Test LegalDocument serialization."""
        doc = LegalDocument(
            url="https://thuvienphapluat.vn/test",
            so_hieu="01/2021/NĐ-CP",
            title="Nghị định về đăng ký doanh nghiệp",
            loai_van_ban="Nghị định",
            ngay_ban_hanh=datetime(2021, 1, 4),
            chapters=[
                LegalChapter(
                    number="I",
                    title="QUY ĐỊNH CHUNG",
                    articles=[
                        LegalArticle(number=1, title="Điều 1", content="Content")
                    ],
                )
            ],
            metadata={"extra_field": "value"},
            scrape_errors=["Warning 1"],
            is_complete=True,
        )

        result = doc.to_dict()

        self.assertEqual(result["so_hieu"], "01/2021/NĐ-CP")
        self.assertEqual(result["ngay_ban_hanh"], "2021-01-04T00:00:00")
        self.assertEqual(len(result["chapters"]), 1)
        self.assertEqual(result["metadata"]["extra_field"], "value")
        self.assertEqual(result["scrape_errors"], ["Warning 1"])
        self.assertTrue(result["is_complete"])

    def test_document_to_dict_none_dates(self):
        """Test serialization with None dates."""
        doc = LegalDocument(
            url="test",
            so_hieu="test",
            title="Test",
        )

        result = doc.to_dict()

        self.assertIsNone(result["ngay_ban_hanh"])
        self.assertIsNone(result["ngay_hieu_luc"])


class TestEnums(unittest.TestCase):
    """Test enum classes."""

    def test_document_status_values(self):
        """Test DocumentStatus enum values."""
        self.assertEqual(DocumentStatus.CON_HIEU_LUC.value, "Còn hiệu lực")
        self.assertEqual(DocumentStatus.HET_HIEU_LUC.value, "Hết hiệu lực")
        self.assertEqual(DocumentStatus.CHUA_CO_HIEU_LUC.value, "Chưa có hiệu lực")

    def test_document_type_values(self):
        """Test DocumentType enum values."""
        self.assertEqual(DocumentType.LUAT.value, "Luật")
        self.assertEqual(DocumentType.NGHI_DINH.value, "Nghị định")
        self.assertEqual(DocumentType.THONG_TU.value, "Thông tư")
        self.assertEqual(DocumentType.QUYET_DINH.value, "Quyết định")


if __name__ == "__main__":
    unittest.main()
