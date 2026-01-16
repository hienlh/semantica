#!/usr/bin/env python3.11
"""
Quick test script for Legal Document Scraper.

Usage:
    python scripts/test_legal_scraper.py [URL]

Examples:
    python scripts/test_legal_scraper.py
    python scripts/test_legal_scraper.py "https://thuvienphapluat.vn/van-ban/..."

Output saved to: ./scraped_legal_docs/
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantica.legal import TVPLScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Default test URLs
DEFAULT_URLS = [
    "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Doanh-nghiep-so-59-2020-QH14-427301.aspx",
]

OUTPUT_DIR = Path("./scraped_legal_docs")


async def main():
    # Get URLs from args or use defaults
    urls = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_URLS

    print(f"\n{'='*60}")
    print("Legal Document Scraper - Test Run")
    print(f"{'='*60}")
    print(f"Output dir: {OUTPUT_DIR.absolute()}")
    print(f"URLs to scrape: {len(urls)}")
    print()

    # Initialize scraper
    scraper = TVPLScraper(
        headless=True,
        rate_limit_seconds=2.0,
        max_retries=2,
        save_raw_html=True,
        output_dir=OUTPUT_DIR,
    )

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Scraping: {url[:70]}...")

        try:
            doc = await scraper.scrape(url)

            # Save document
            scraper._save_document(doc)

            # Print summary
            print(f"  ✓ Title: {doc.title[:60]}..." if len(doc.title) > 60 else f"  ✓ Title: {doc.title}")
            print(f"  ✓ Số hiệu: {doc.so_hieu}")
            print(f"  ✓ Loại văn bản: {doc.loai_van_ban or 'N/A'}")
            print(f"  ✓ Chapters: {len(doc.chapters)}")
            print(f"  ✓ Total articles: {doc.total_articles}")
            print(f"  ✓ Raw text: {len(doc.raw_text):,} chars")
            print(f"  ✓ Complete: {doc.is_complete}")

            if doc.chapters:
                print(f"\n  Sample structure:")
                for ch in doc.chapters[:3]:
                    print(f"    Chương {ch.number}: {ch.title[:40]}...")
                    print(f"      Articles: {len(ch.articles)}, Sections: {len(ch.sections)}")

            if doc.scrape_errors:
                print(f"\n  ⚠ Warnings: {doc.scrape_errors}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n{'='*60}")
    print(f"Done! Files saved to: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}\n")

    # List output files
    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("*"))
        if files:
            print("Output files:")
            for f in sorted(files):
                size = f.stat().st_size / 1024
                print(f"  - {f.name} ({size:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
