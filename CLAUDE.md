# CLAUDE.md

## Legal Document Pipeline

```bash
# Scrape from URL
python -m semantica.cli legal scrape https://thuvienphapluat.vn/van-ban/...

# Scrape from URL list file
python -m semantica.cli legal scrape urls.txt -o scraped_legal_docs/

# Parse HTML to JSON
python -m semantica.cli legal parse scraped_legal_docs/*.html

# Import JSON to database
python -m semantica.cli legal import scraped_legal_docs/*.json -d data/legal_docs.db

# Full pipeline (scrape + import)
python -m semantica.cli legal full urls.txt -d data/legal_docs.db

# Re-parse HTML and import to fresh database
python -m semantica.cli legal reimport scraped_legal_docs/

# Show database stats
python -m semantica.cli legal stats -d data/legal_docs.db
```

## Post-Import: Extract Abbreviations

```python
from semantica.legal import LegalDocumentDB

db = LegalDocumentDB("data/legal_docs.db")
db.extract_abbreviations_from_all_documents()
```
