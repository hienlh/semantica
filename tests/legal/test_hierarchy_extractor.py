"""
Tests for HierarchyExtractor - Vietnamese legal document structure parsing.

Tests regex patterns for:
- Chương (Chapter): I, II, III or 1, 2, 3
- Mục (Section): 1, 2, 3
- Điều (Article): 1, 2, 3
- Khoản (Clause): 1., 2., 3.
- Điểm (Point): a), b), c), đ)
"""

import unittest

from semantica.legal.scraper.hierarchy_extractor import HierarchyExtractor


class TestHierarchyExtractor(unittest.TestCase):
    """Test hierarchy extraction from Vietnamese legal text."""

    def setUp(self):
        self.extractor = HierarchyExtractor()

    # ========== Chapter Tests ==========

    def test_extract_chapter_roman_numeral(self):
        """Test extraction of chapter with Roman numeral."""
        text = """
Chương I
NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định về việc thành lập, tổ chức quản lý.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].number, "I")
        self.assertEqual(chapters[0].title, "NHỮNG QUY ĐỊNH CHUNG")
        self.assertEqual(len(chapters[0].articles), 1)
        self.assertEqual(chapters[0].articles[0].number, 1)

    def test_extract_chapter_arabic_numeral(self):
        """Test extraction of chapter with Arabic numeral."""
        text = """
Chương 1
QUY ĐỊNH CHUNG

Điều 1. Phạm vi
Nội dung điều 1.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].number, "1")

    def test_extract_multiple_chapters(self):
        """Test extraction of multiple chapters."""
        text = """
Chương I
NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Nội dung điều 1.

Chương II
THÀNH LẬP DOANH NGHIỆP

Điều 2. Quyền thành lập
Nội dung điều 2.

Điều 3. Nghĩa vụ
Nội dung điều 3.

Chương III
XỬ PHẠT

Điều 4. Mức phạt
Nội dung điều 4.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].number, "I")
        self.assertEqual(chapters[1].number, "II")
        self.assertEqual(chapters[2].number, "III")
        self.assertEqual(len(chapters[0].articles), 1)
        self.assertEqual(len(chapters[1].articles), 2)
        self.assertEqual(len(chapters[2].articles), 1)

    # ========== Section Tests ==========

    def test_extract_section_in_chapter(self):
        """Test extraction of sections within a chapter."""
        text = """
Chương III
CÔNG TY TRÁCH NHIỆM HỮU HẠN

Mục 1
CÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN

Điều 46. Công ty TNHH hai thành viên
Nội dung điều 46.

Mục 2
CÔNG TY TRÁCH NHIỆM HỮU HẠN MỘT THÀNH VIÊN

Điều 74. Công ty TNHH một thành viên
Nội dung điều 74.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(len(chapters[0].sections), 2)
        self.assertEqual(chapters[0].sections[0].number, 1)
        self.assertEqual(chapters[0].sections[1].number, 2)
        self.assertEqual(len(chapters[0].sections[0].articles), 1)
        self.assertEqual(len(chapters[0].sections[1].articles), 1)

    # ========== Article Tests ==========

    def test_extract_article_basic(self):
        """Test basic article extraction."""
        text = """
Điều 1. Phạm vi điều chỉnh
Luật này quy định về việc thành lập, tổ chức quản lý, tổ chức lại, giải thể và hoạt động có liên quan của doanh nghiệp.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].number, 1)
        self.assertEqual(articles[0].title, "Phạm vi điều chỉnh")
        self.assertIn("Luật này quy định", articles[0].content)

    def test_extract_article_uppercase(self):
        """Test article extraction with uppercase ĐIỀU."""
        text = """
ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH
Nội dung điều chỉnh.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].number, 1)

    def test_extract_article_no_title(self):
        """Test article extraction without explicit title on same line."""
        text = """
Điều 1.
Luật này quy định về doanh nghiệp.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].number, 1)
        # The regex captures until newline, so the next line becomes title
        # This is expected behavior based on the pattern
        self.assertIn("Luật này quy định", articles[0].raw_text)

    # ========== Clause Tests ==========

    def test_extract_clauses(self):
        """Test extraction of clauses (Khoản)."""
        text = """
Điều 4. Quyền của doanh nghiệp
1. Tự do kinh doanh ngành, nghề mà luật không cấm.
2. Tự chủ kinh doanh và lựa chọn hình thức tổ chức kinh doanh.
3. Chủ động lựa chọn ngành, nghề, địa bàn.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles), 1)
        self.assertEqual(len(articles[0].clauses), 3)
        self.assertEqual(articles[0].clauses[0].number, 1)
        self.assertEqual(articles[0].clauses[1].number, 2)
        self.assertEqual(articles[0].clauses[2].number, 3)
        self.assertIn("Tự do kinh doanh", articles[0].clauses[0].content)

    def test_extract_multiline_clause(self):
        """Test extraction of multi-line clause content."""
        text = """
Điều 5. Nghĩa vụ của doanh nghiệp
1. Đáp ứng đủ điều kiện kinh doanh khi kinh doanh ngành, nghề đầu tư kinh doanh
có điều kiện; bảo đảm và duy trì đủ điều kiện đầu tư kinh doanh đó trong suốt
quá trình hoạt động kinh doanh.
2. Nghĩa vụ thứ hai.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles[0].clauses), 2)
        # Multi-line content should be preserved
        self.assertIn("điều kiện kinh doanh", articles[0].clauses[0].content)
        self.assertIn("duy trì đủ điều kiện", articles[0].clauses[0].content)

    # ========== Point Tests ==========

    def test_extract_points(self):
        """Test extraction of points (Điểm) within clauses."""
        text = """
Điều 17. Hồ sơ đăng ký doanh nghiệp
1. Hồ sơ đăng ký thành lập doanh nghiệp bao gồm:
a) Giấy đề nghị đăng ký doanh nghiệp;
b) Điều lệ công ty;
c) Danh sách thành viên;
d) Bản sao giấy tờ pháp lý của cá nhân.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(articles), 1)
        self.assertEqual(len(articles[0].clauses), 1)
        self.assertEqual(len(articles[0].clauses[0].points), 4)
        self.assertEqual(articles[0].clauses[0].points[0].letter, "a")
        self.assertEqual(articles[0].clauses[0].points[1].letter, "b")
        self.assertEqual(articles[0].clauses[0].points[2].letter, "c")
        self.assertEqual(articles[0].clauses[0].points[3].letter, "d")

    def test_extract_point_vietnamese_d(self):
        """Test extraction of point with Vietnamese đ letter."""
        text = """
Điều 10. Các trường hợp
1. Các trường hợp bao gồm:
a) Trường hợp A;
b) Trường hợp B;
c) Trường hợp C;
d) Trường hợp D;
đ) Trường hợp Đ;
e) Trường hợp E.
"""
        chapters, articles = self.extractor.extract(text)

        points = articles[0].clauses[0].points
        self.assertEqual(len(points), 6)
        self.assertEqual(points[4].letter, "đ")
        self.assertIn("Trường hợp Đ", points[4].content)

    # ========== Document without chapters ==========

    def test_extract_standalone_articles(self):
        """Test extraction when document has no chapters."""
        text = """
Điều 1. Phạm vi điều chỉnh
Nội dung điều 1.

Điều 2. Đối tượng áp dụng
Nội dung điều 2.

Điều 3. Hiệu lực thi hành
Nội dung điều 3.
"""
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 0)
        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[0].number, 1)
        self.assertEqual(articles[1].number, 2)
        self.assertEqual(articles[2].number, 3)

    # ========== Validation ==========

    def test_validate_structure(self):
        """Test structure validation and statistics."""
        text = """
Chương I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi
1. Khoản 1
a) Điểm a
b) Điểm b
2. Khoản 2

Điều 2. Đối tượng
Nội dung.

Chương II
THÀNH LẬP

Điều 3. Điều kiện
1. Điều kiện 1
"""
        stats = self.extractor.validate_structure(text)

        self.assertEqual(stats["chapters"], 2)
        self.assertEqual(stats["articles"], 3)
        self.assertEqual(stats["clauses"], 3)
        self.assertEqual(stats["points"], 2)
        self.assertTrue(stats["has_chapters"])

    # ========== Edge Cases ==========

    def test_empty_text(self):
        """Test handling of empty text."""
        chapters, articles = self.extractor.extract("")

        self.assertEqual(len(chapters), 0)
        self.assertEqual(len(articles), 0)

    def test_text_without_legal_structure(self):
        """Test handling of text without legal structure."""
        text = "This is just regular text without any legal document structure."
        chapters, articles = self.extractor.extract(text)

        self.assertEqual(len(chapters), 0)
        self.assertEqual(len(articles), 0)

    def test_clean_title(self):
        """Test title cleaning."""
        self.assertEqual(self.extractor._clean_title("  . : Title  "), "Title")
        self.assertEqual(self.extractor._clean_title(""), "")
        self.assertEqual(self.extractor._clean_title(None), "")


class TestHierarchyExtractorRealWorld(unittest.TestCase):
    """Test with real-world Vietnamese legal text samples."""

    def setUp(self):
        self.extractor = HierarchyExtractor()

    def test_luat_doanh_nghiep_sample(self):
        """Test with sample from Luật Doanh nghiệp 2020."""
        text = """
Chương I
NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định về việc thành lập, tổ chức quản lý, tổ chức lại, giải thể và hoạt động có liên quan của doanh nghiệp, bao gồm công ty trách nhiệm hữu hạn, công ty cổ phần, công ty hợp danh và doanh nghiệp tư nhân; quy định về nhóm công ty.

Điều 2. Đối tượng áp dụng
1. Doanh nghiệp được quy định tại Điều 1 của Luật này.
2. Cơ quan, tổ chức, cá nhân có liên quan đến việc thành lập, tổ chức quản lý, tổ chức lại, giải thể và hoạt động có liên quan của doanh nghiệp.

Điều 3. Áp dụng Luật Doanh nghiệp và các luật có liên quan
1. Việc thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp áp dụng theo quy định của Luật này và quy định khác của pháp luật có liên quan.
2. Trường hợp luật khác có quy định đặc thù về việc thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp thì áp dụng quy định của luật đó.

Điều 4. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Doanh nghiệp là tổ chức có tên riêng, có tài sản, có trụ sở giao dịch, được thành lập hoặc đăng ký thành lập theo quy định của pháp luật nhằm mục đích kinh doanh.
2. Doanh nghiệp nhà nước bao gồm các doanh nghiệp do Nhà nước nắm giữ trên 50% vốn điều lệ, tổng số cổ phần có quyền biểu quyết theo quy định tại Điều 88 của Luật này.
3. Doanh nghiệp Việt Nam là doanh nghiệp được thành lập hoặc đăng ký thành lập theo pháp luật Việt Nam và có trụ sở chính tại Việt Nam.

Chương II
THÀNH LẬP DOANH NGHIỆP

Điều 16. Quyền thành lập, góp vốn, mua cổ phần, mua phần vốn góp và quản lý doanh nghiệp
1. Tổ chức, cá nhân có quyền thành lập và quản lý doanh nghiệp tại Việt Nam theo quy định của Luật này, trừ trường hợp quy định tại khoản 2 Điều này.
2. Tổ chức, cá nhân sau đây không có quyền thành lập và quản lý doanh nghiệp tại Việt Nam:
a) Cơ quan nhà nước, đơn vị lực lượng vũ trang nhân dân sử dụng tài sản nhà nước để thành lập doanh nghiệp kinh doanh thu lợi riêng cho cơ quan, đơn vị mình;
b) Cán bộ, công chức, viên chức theo quy định của Luật Cán bộ, công chức và Luật Viên chức;
c) Sĩ quan, hạ sĩ quan, quân nhân chuyên nghiệp, công nhân, viên chức quốc phòng trong các cơ quan, đơn vị thuộc Quân đội nhân dân Việt Nam;
d) Sĩ quan, hạ sĩ quan chuyên nghiệp trong các cơ quan, đơn vị thuộc Công an nhân dân Việt Nam;
đ) Cán bộ lãnh đạo, quản lý nghiệp vụ trong doanh nghiệp nhà nước theo quy định tại điểm a khoản 1 Điều 88 của Luật này;
e) Người chưa thành niên; người bị hạn chế năng lực hành vi dân sự; người bị mất năng lực hành vi dân sự; người có khó khăn trong nhận thức, làm chủ hành vi; tổ chức không có tư cách pháp nhân;
g) Người đang bị truy cứu trách nhiệm hình sự, bị tạm giam, đang chấp hành hình phạt tù, đang chấp hành biện pháp xử lý hành chính tại cơ sở cai nghiện bắt buộc, cơ sở giáo dục bắt buộc hoặc đang bị Tòa án cấm đảm nhiệm chức vụ, cấm hành nghề hoặc làm công việc nhất định.
"""
        chapters, articles = self.extractor.extract(text)

        # Verify chapters
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "NHỮNG QUY ĐỊNH CHUNG")
        self.assertEqual(chapters[1].title, "THÀNH LẬP DOANH NGHIỆP")

        # Verify articles in Chapter I
        self.assertEqual(len(chapters[0].articles), 4)
        self.assertEqual(chapters[0].articles[0].number, 1)
        self.assertEqual(chapters[0].articles[0].title, "Phạm vi điều chỉnh")

        # Verify clauses in Điều 2
        dieu_2 = chapters[0].articles[1]
        self.assertEqual(len(dieu_2.clauses), 2)

        # Verify clauses in Điều 4
        dieu_4 = chapters[0].articles[3]
        self.assertEqual(len(dieu_4.clauses), 3)

        # Verify articles in Chapter II
        self.assertEqual(len(chapters[1].articles), 1)
        dieu_16 = chapters[1].articles[0]
        self.assertEqual(dieu_16.number, 16)

        # Verify clauses and points in Điều 16
        self.assertEqual(len(dieu_16.clauses), 2)
        self.assertEqual(len(dieu_16.clauses[1].points), 7)  # a, b, c, d, đ, e, g
        self.assertEqual(dieu_16.clauses[1].points[4].letter, "đ")


if __name__ == "__main__":
    unittest.main()
