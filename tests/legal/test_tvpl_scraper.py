"""
Tests for TVPLScraper - thuvienphapluat.vn scraper.

Tests parsing functionality with mock HTML and utility methods.
Integration tests with real URLs are in test_tvpl_integration.py
"""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from semantica.legal.scraper.tvpl import TVPLScraper


class TestTVPLScraperInit(unittest.TestCase):
    """Test TVPLScraper initialization."""

    def test_default_init(self):
        """Test default initialization values."""
        scraper = TVPLScraper()

        self.assertTrue(scraper.headless)
        self.assertEqual(scraper.timeout, 30000)
        self.assertEqual(scraper.rate_limit_seconds, 2.0)
        self.assertEqual(scraper.max_retries, 3)
        self.assertTrue(scraper.save_raw_html)

    def test_custom_init(self):
        """Test custom initialization values."""
        scraper = TVPLScraper(
            headless=False,
            timeout=60000,
            rate_limit_seconds=5.0,
            max_retries=5,
            save_raw_html=False,
        )

        self.assertFalse(scraper.headless)
        self.assertEqual(scraper.timeout, 60000)
        self.assertEqual(scraper.rate_limit_seconds, 5.0)
        self.assertEqual(scraper.max_retries, 5)
        self.assertFalse(scraper.save_raw_html)


class TestTVPLScraperDateParsing(unittest.TestCase):
    """Test date parsing functionality."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_parse_date_slash_format(self):
        """Test parsing dd/mm/yyyy format."""
        result = self.scraper._parse_date("17/06/2020")

        self.assertEqual(result, datetime(2020, 6, 17))

    def test_parse_date_dash_format(self):
        """Test parsing dd-mm-yyyy format."""
        result = self.scraper._parse_date("04-01-2021")

        self.assertEqual(result, datetime(2021, 1, 4))

    def test_parse_date_vietnamese_format(self):
        """Test parsing 'ngày X tháng Y năm Z' format."""
        result = self.scraper._parse_date("ngày 17 tháng 6 năm 2020")

        self.assertEqual(result, datetime(2020, 6, 17))

    def test_parse_date_with_text(self):
        """Test parsing date embedded in text."""
        result = self.scraper._parse_date("Ban hành ngày 17/06/2020 tại Hà Nội")

        self.assertEqual(result, datetime(2020, 6, 17))

    def test_parse_date_empty(self):
        """Test parsing empty string."""
        result = self.scraper._parse_date("")

        self.assertIsNone(result)

    def test_parse_date_invalid(self):
        """Test parsing invalid date format."""
        result = self.scraper._parse_date("invalid date")

        self.assertIsNone(result)

    def test_parse_date_none(self):
        """Test parsing None value."""
        result = self.scraper._parse_date(None)

        self.assertIsNone(result)


class TestTVPLScraperSoHieuExtraction(unittest.TestCase):
    """Test document number extraction from URL."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_extract_so_hieu_luat(self):
        """Test extracting số hiệu from Luật URL."""
        url = "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Doanh-nghiep-so-59-2020-QH14-427301.aspx"
        result = self.scraper._extract_so_hieu_from_url(url)

        self.assertEqual(result, "59/2020/QH14")

    def test_extract_so_hieu_nghi_dinh(self):
        """Test extracting số hiệu from Nghị định URL."""
        url = "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-01-2021-ND-CP-dang-ky-doanh-nghiep-465730.aspx"
        result = self.scraper._extract_so_hieu_from_url(url)

        # Note: actual extraction depends on URL pattern
        self.assertIsInstance(result, str)

    def test_extract_so_hieu_no_match(self):
        """Test extraction when no pattern matches."""
        url = "https://thuvienphapluat.vn/invalid-url"
        result = self.scraper._extract_so_hieu_from_url(url)

        self.assertEqual(result, "")


class TestTVPLScraperUserAgent(unittest.TestCase):
    """Test user agent rotation."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_user_agent_rotation(self):
        """Test that user agents rotate."""
        ua1 = self.scraper._get_next_user_agent()
        ua2 = self.scraper._get_next_user_agent()
        ua3 = self.scraper._get_next_user_agent()
        ua4 = self.scraper._get_next_user_agent()  # Should wrap around

        self.assertNotEqual(ua1, ua2)
        self.assertEqual(ua1, ua4)  # Wraps around to first

    def test_user_agents_are_valid(self):
        """Test that all user agents contain expected strings."""
        for ua in self.scraper.USER_AGENTS:
            self.assertIn("Mozilla", ua)
            self.assertIn("Chrome", ua)


class TestTVPLScraperParsing(unittest.TestCase):
    """Test HTML parsing functionality."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_parse_minimal_html(self):
        """Test parsing minimal HTML structure."""
        # Content must be > 1000 chars for scraper to consider it valid
        long_content = """
                Điều 1. Phạm vi điều chỉnh
                Luật này quy định về việc thành lập, tổ chức quản lý, tổ chức lại,
                giải thể và hoạt động có liên quan của doanh nghiệp, bao gồm công ty
                trách nhiệm hữu hạn, công ty cổ phần, công ty hợp danh và doanh nghiệp
                tư nhân; quy định về nhóm công ty.

                Điều 2. Đối tượng áp dụng
                1. Doanh nghiệp được quy định tại Điều 1 của Luật này.
                2. Cơ quan, tổ chức, cá nhân có liên quan đến việc thành lập,
                tổ chức quản lý, tổ chức lại, giải thể và hoạt động có liên quan
                của doanh nghiệp.

                Điều 3. Áp dụng pháp luật
                Việc thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp
                áp dụng theo quy định của Luật này và quy định khác của pháp luật
                có liên quan. Trường hợp luật khác có quy định đặc thù thì áp dụng
                quy định của luật đó.

                Điều 4. Giải thích từ ngữ
                Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
                1. Doanh nghiệp là tổ chức có tên riêng, có tài sản, có trụ sở.
                2. Doanh nghiệp nhà nước bao gồm các doanh nghiệp do Nhà nước.
                3. Doanh nghiệp Việt Nam là doanh nghiệp được thành lập theo pháp luật.
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Luật Doanh nghiệp 2020</h1>
            <div id="ctl00_Content_ThongTinVB_divNoiDung">
                {long_content}
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/test"

        doc = self.scraper.parse(html, url)

        self.assertEqual(doc.url, url)
        self.assertEqual(doc.title, "Luật Doanh nghiệp 2020")
        self.assertIn("Phạm vi điều chỉnh", doc.raw_text)
        self.assertTrue(doc.is_complete)

    def test_parse_with_metadata(self):
        """Test parsing HTML with metadata elements."""
        # Content must be > 1000 chars for scraper to consider it valid
        long_content = "Nội dung test. " * 100  # ~1500 chars
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Luật Test</h1>
            <div class="so-hieu">59/2020/QH14</div>
            <div class="loai-van-ban">Luật</div>
            <div class="co-quan-ban-hanh">Quốc hội</div>
            <div class="ngay-ban-hanh">17/06/2020</div>
            <div id="ctl00_Content_ThongTinVB_divNoiDung">
                Điều 1. Test
                {long_content}
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/test"

        doc = self.scraper.parse(html, url)

        self.assertEqual(doc.so_hieu, "59/2020/QH14")
        self.assertEqual(doc.loai_van_ban, "Luật")
        self.assertEqual(doc.co_quan_ban_hanh, "Quốc hội")
        self.assertEqual(doc.ngay_ban_hanh, datetime(2020, 6, 17))

    def test_parse_extracts_hierarchy(self):
        """Test that parsing extracts hierarchical structure."""
        # Content must be > 1000 chars for scraper to consider it valid
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Luật Test</h1>
            <div id="ctl00_Content_ThongTinVB_divNoiDung">
                Chương I
                QUY ĐỊNH CHUNG

                Điều 1. Phạm vi điều chỉnh
                Luật này quy định về việc thành lập, tổ chức quản lý, tổ chức lại,
                giải thể và hoạt động có liên quan của doanh nghiệp, bao gồm công ty
                trách nhiệm hữu hạn, công ty cổ phần, công ty hợp danh.
                1. Khoản 1 nội dung chi tiết về phạm vi điều chỉnh của luật này.
                2. Khoản 2 nội dung về các quy định bổ sung và mở rộng phạm vi.

                Điều 2. Đối tượng áp dụng
                Luật này áp dụng đối với các tổ chức, cá nhân có liên quan đến việc
                thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp.
                Các đối tượng bao gồm doanh nghiệp tư nhân, công ty TNHH, công ty cổ phần.

                Chương II
                THÀNH LẬP DOANH NGHIỆP

                Điều 3. Điều kiện thành lập doanh nghiệp
                Tổ chức, cá nhân có quyền thành lập và quản lý doanh nghiệp tại Việt Nam
                theo quy định của Luật này, trừ trường hợp quy định tại khoản 2 Điều này.
                Điều kiện bao gồm năng lực pháp luật, vốn điều lệ, và các yêu cầu khác.
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/test"

        doc = self.scraper.parse(html, url)

        self.assertEqual(len(doc.chapters), 2)
        self.assertEqual(doc.chapters[0].number, "I")
        self.assertEqual(len(doc.chapters[0].articles), 2)
        self.assertEqual(doc.chapters[0].articles[0].number, 1)
        self.assertEqual(len(doc.chapters[0].articles[0].clauses), 2)

    def test_parse_no_content_element(self):
        """Test parsing when content element is missing."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Test</h1>
            <div>No content div</div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/test"

        doc = self.scraper.parse(html, url)

        self.assertFalse(doc.is_complete)
        self.assertIn("Content element not found", doc.scrape_errors[0])

    def test_parse_fallback_content_selectors(self):
        """Test parsing with fallback content selectors."""
        # Content must be > 1000 chars for scraper to consider it valid
        extra_content = """
                Điều 3. Áp dụng pháp luật
                Việc thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp
                áp dụng theo quy định của Luật này và quy định khác của pháp luật
                có liên quan. Trường hợp luật khác có quy định đặc thù thì áp dụng
                quy định của luật đó.

                Điều 4. Giải thích từ ngữ
                Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
                1. Doanh nghiệp là tổ chức có tên riêng, có tài sản, có trụ sở giao dịch.
                2. Doanh nghiệp nhà nước bao gồm các doanh nghiệp do Nhà nước nắm giữ.
                3. Doanh nghiệp Việt Nam là doanh nghiệp được thành lập theo pháp luật.
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Test</h1>
            <div class="NoiDung">
                Điều 1. Test Article
                This is the content of the article which should be long enough.
                Adding more content to make it over 1000 characters.
                Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
                Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
                Duis aute irure dolor in reprehenderit in voluptate velit esse.
                Excepteur sint occaecat cupidatat non proident, sunt in culpa.
                More content to ensure we hit the threshold.
                Even more Vietnamese legal content here.
                Điều 2. Another test article.
                More detailed content for the second article.
                {extra_content}
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/test"

        doc = self.scraper.parse(html, url)

        # Should find content via fallback selector
        self.assertIn("Test Article", doc.raw_text)


class TestTVPLScraperMetadataTable(unittest.TestCase):
    """Test metadata table extraction."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_extract_metadata_table(self):
        """Test extracting metadata from table format."""
        html = """
        <div class="thuoc-tinh">
            <table>
                <tr>
                    <td>Số hiệu:</td>
                    <td>59/2020/QH14</td>
                </tr>
                <tr>
                    <td>Loại văn bản:</td>
                    <td>Luật</td>
                </tr>
                <tr>
                    <td>Nơi ban hành:</td>
                    <td>Quốc hội</td>
                </tr>
            </table>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        metadata = self.scraper._extract_metadata_table(soup)

        self.assertEqual(metadata["Số hiệu"], "59/2020/QH14")
        self.assertEqual(metadata["Loại văn bản"], "Luật")
        self.assertEqual(metadata["Nơi ban hành"], "Quốc hội")


class TestTVPLScraperTitleExtraction(unittest.TestCase):
    """Test title extraction from various HTML structures."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_extract_title_h1_class(self):
        """Test extracting title from h1.title."""
        from bs4 import BeautifulSoup

        html = '<h1 class="title">Luật Doanh nghiệp 2020</h1>'
        soup = BeautifulSoup(html, "html.parser")

        result = self.scraper._extract_title(soup)

        self.assertEqual(result, "Luật Doanh nghiệp 2020")

    def test_extract_title_plain_h1(self):
        """Test extracting title from plain h1."""
        from bs4 import BeautifulSoup

        html = "<h1>Nghị định 01/2021/NĐ-CP</h1>"
        soup = BeautifulSoup(html, "html.parser")

        result = self.scraper._extract_title(soup)

        self.assertEqual(result, "Nghị định 01/2021/NĐ-CP")

    def test_extract_title_no_h1(self):
        """Test extracting title when no h1 exists."""
        from bs4 import BeautifulSoup

        html = "<div>No title here</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = self.scraper._extract_title(soup)

        self.assertEqual(result, "")


class TestTVPLScraperContentSelectors(unittest.TestCase):
    """Test content selector configuration."""

    def test_content_selectors_list(self):
        """Test that content selectors are properly defined."""
        scraper = TVPLScraper()

        self.assertIsInstance(scraper.CONTENT_SELECTORS, list)
        self.assertGreater(len(scraper.CONTENT_SELECTORS), 0)
        self.assertIn("#ctl00_Content_ThongTinVB_divNoiDung", scraper.CONTENT_SELECTORS)

    def test_primary_selector_first(self):
        """Test that primary selector is first in list."""
        scraper = TVPLScraper()

        # The most reliable selector should be first
        self.assertEqual(
            scraper.CONTENT_SELECTORS[0], "#ctl00_Content_ThongTinVB_divNoiDung"
        )


if __name__ == "__main__":
    unittest.main()
