"""
Integration tests for TVPLScraper with real URLs.

These tests require network access and Playwright to be installed.
They are marked with @unittest.skipUnless to skip when dependencies are missing.

Run with: pytest tests/legal/test_tvpl_integration.py -v -s
"""

import asyncio
import os
import unittest

# Check if Playwright is available
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from semantica.legal import TVPLScraper


def run_async(coro):
    """Helper to run async functions in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright not installed")
@unittest.skipUnless(
    os.environ.get("RUN_INTEGRATION_TESTS", "").lower() == "true",
    "Set RUN_INTEGRATION_TESTS=true to run integration tests",
)
class TestTVPLScraperIntegration(unittest.TestCase):
    """Integration tests with real thuvienphapluat.vn URLs."""

    @classmethod
    def setUpClass(cls):
        """Set up scraper instance for all tests."""
        cls.scraper = TVPLScraper(
            headless=True,
            rate_limit_seconds=2.0,
            max_retries=2,
        )

    def test_scrape_luat_doanh_nghiep_2020(self):
        """Test scraping Luật Doanh nghiệp 2020 (59/2020/QH14)."""
        url = "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Doanh-nghiep-so-59-2020-QH14-427301.aspx"

        doc = run_async(self.scraper.scrape(url))

        # Verify basic metadata
        self.assertEqual(doc.url, url)
        self.assertIn("59/2020/QH14", doc.so_hieu)
        self.assertIn("Doanh nghiệp", doc.title)

        # Verify structure extraction
        self.assertGreater(len(doc.chapters), 0)
        self.assertGreater(doc.total_articles, 0)
        self.assertGreater(len(doc.raw_text), 10000)

        # Verify it's marked as complete
        self.assertTrue(doc.is_complete)

        # Log extraction stats for debugging
        print(f"\n=== Luật Doanh nghiệp 2020 ===")
        print(f"Title: {doc.title}")
        print(f"Số hiệu: {doc.so_hieu}")
        print(f"Chapters: {len(doc.chapters)}")
        print(f"Total articles: {doc.total_articles}")
        print(f"Raw text length: {len(doc.raw_text)}")

    def test_scrape_nghi_dinh_01_2021(self):
        """Test scraping Nghị định 01/2021/NĐ-CP."""
        url = "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-01-2021-ND-CP-dang-ky-doanh-nghiep-465730.aspx"

        doc = run_async(self.scraper.scrape(url))

        # Verify basic fields
        self.assertEqual(doc.url, url)
        self.assertIn("Nghị định", doc.title.lower() or doc.loai_van_ban.lower() or "nghị định")

        # Verify content extracted
        self.assertGreater(len(doc.raw_text), 1000)
        self.assertTrue(doc.is_complete or len(doc.scrape_errors) == 0)

        print(f"\n=== Nghị định 01/2021/NĐ-CP ===")
        print(f"Title: {doc.title}")
        print(f"Số hiệu: {doc.so_hieu}")
        print(f"Chapters: {len(doc.chapters)}")
        print(f"Total articles: {doc.total_articles}")

    def test_scrape_nghi_dinh_122_2021(self):
        """Test scraping Nghị định 122/2021/NĐ-CP."""
        url = "https://thuvienphapluat.vn/van-ban/Vi-pham-hanh-chinh/Nghi-dinh-122-2021-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-ke-hoach-va-dau-tu-495816.aspx"

        doc = run_async(self.scraper.scrape(url))

        # Verify basic fields
        self.assertEqual(doc.url, url)
        self.assertGreater(len(doc.raw_text), 1000)

        print(f"\n=== Nghị định 122/2021/NĐ-CP ===")
        print(f"Title: {doc.title}")
        print(f"Số hiệu: {doc.so_hieu}")
        print(f"Chapters: {len(doc.chapters)}")
        print(f"Total articles: {doc.total_articles}")


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright not installed")
class TestTVPLScraperQuickTest(unittest.TestCase):
    """Quick test to verify scraper works without full integration."""

    def test_playwright_available(self):
        """Test that Playwright is properly installed."""
        self.assertTrue(PLAYWRIGHT_AVAILABLE)

    def test_scraper_instantiation(self):
        """Test that scraper can be instantiated."""
        scraper = TVPLScraper()
        self.assertIsNotNone(scraper)
        self.assertEqual(len(scraper.CONTENT_SELECTORS), 5)

    def test_scraper_selectors_configured(self):
        """Test that scraper has proper selectors configured."""
        scraper = TVPLScraper()

        # Check content selectors
        self.assertIn("#ctl00_Content_ThongTinVB_divNoiDung", scraper.CONTENT_SELECTORS)

        # Check other selectors
        self.assertIn("title", scraper.SELECTORS)
        self.assertIn("metadata", scraper.SELECTORS)


class TestTVPLScraperMockIntegration(unittest.TestCase):
    """Mock integration tests that don't require network."""

    def setUp(self):
        self.scraper = TVPLScraper()

    def test_parse_sample_html(self):
        """Test parsing a sample HTML document."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Luật Test</title></head>
        <body>
            <h1 class="title">LUẬT DOANH NGHIỆP SỐ 59/2020/QH14</h1>
            <div class="thuoc-tinh">
                <div class="so-hieu">59/2020/QH14</div>
                <div class="loai-van-ban">Luật</div>
                <div class="co-quan-ban-hanh">Quốc hội</div>
                <div class="ngay-ban-hanh">17/06/2020</div>
            </div>
            <div id="ctl00_Content_ThongTinVB_divNoiDung">
                Chương I
                NHỮNG QUY ĐỊNH CHUNG

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

                Điều 3. Áp dụng Luật Doanh nghiệp và các luật có liên quan
                1. Việc thành lập, tổ chức quản lý, tổ chức lại, giải thể doanh nghiệp
                áp dụng theo quy định của Luật này và quy định khác của pháp luật có liên quan.
                2. Trường hợp luật khác có quy định đặc thù về việc thành lập, tổ chức
                quản lý, tổ chức lại, giải thể doanh nghiệp thì áp dụng quy định của luật đó.

                Chương II
                THÀNH LẬP DOANH NGHIỆP

                Điều 16. Quyền thành lập, góp vốn, mua cổ phần
                1. Tổ chức, cá nhân có quyền thành lập và quản lý doanh nghiệp tại
                Việt Nam theo quy định của Luật này.
                2. Tổ chức, cá nhân sau đây không có quyền thành lập và quản lý
                doanh nghiệp tại Việt Nam:
                a) Cơ quan nhà nước, đơn vị lực lượng vũ trang nhân dân;
                b) Cán bộ, công chức, viên chức;
                c) Sĩ quan, hạ sĩ quan, quân nhân chuyên nghiệp.
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/mock-test"

        doc = self.scraper.parse(sample_html, url)

        # Verify metadata
        self.assertEqual(doc.so_hieu, "59/2020/QH14")
        self.assertEqual(doc.loai_van_ban, "Luật")
        self.assertEqual(doc.co_quan_ban_hanh, "Quốc hội")
        self.assertIsNotNone(doc.ngay_ban_hanh)

        # Verify hierarchy
        self.assertEqual(len(doc.chapters), 2)
        self.assertEqual(doc.chapters[0].number, "I")
        self.assertEqual(doc.chapters[0].title, "NHỮNG QUY ĐỊNH CHUNG")
        self.assertEqual(len(doc.chapters[0].articles), 3)

        # Verify Chapter II
        self.assertEqual(doc.chapters[1].number, "II")
        self.assertEqual(len(doc.chapters[1].articles), 1)

        # Verify article with clauses and points
        dieu_16 = doc.chapters[1].articles[0]
        self.assertEqual(dieu_16.number, 16)
        self.assertEqual(len(dieu_16.clauses), 2)
        self.assertEqual(len(dieu_16.clauses[1].points), 3)

    def test_to_dict_serialization(self):
        """Test that parsed document can be serialized to dict."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Test Law</h1>
            <div id="ctl00_Content_ThongTinVB_divNoiDung">
                Điều 1. Test Article
                This is test content that is long enough to pass the minimum length check.
                Adding more content here to ensure we have sufficient text.
                Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
                Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
                Duis aute irure dolor in reprehenderit in voluptate velit esse.
                Cillum dolore eu fugiat nulla pariatur excepteur sint occaecat.
                More Vietnamese legal content to make this long enough.
                Additional content for testing purposes only.
            </div>
        </body>
        </html>
        """
        url = "https://thuvienphapluat.vn/mock"

        doc = self.scraper.parse(sample_html, url)
        result = doc.to_dict()

        # Verify serialization
        self.assertIsInstance(result, dict)
        self.assertEqual(result["url"], url)
        self.assertIn("chapters", result)
        self.assertIn("articles", result)
        self.assertIn("is_complete", result)

        # Verify JSON serializable
        import json

        json_str = json.dumps(result, ensure_ascii=False)
        self.assertIsInstance(json_str, str)


if __name__ == "__main__":
    unittest.main()
