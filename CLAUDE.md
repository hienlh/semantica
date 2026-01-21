# CLAUDE.md

## Vietnamese Legal Document Pipeline

Pipeline for processing Vietnamese legal documents: scrape → parse → store → extract KG → visualize.

### Phase 00-01: Scrape & Import

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

### Phase 03.5: Extract Abbreviations

```python
from semantica.legal import LegalDocumentDB

db = LegalDocumentDB("data/legal_docs.db")
db.extract_abbreviations_from_all_documents()
```

### Phase 04: Knowledge Graph Pipeline

#### Quick Start with Script

```bash
# Basic run (extract KG from 5 articles)
python scripts/run_legal_pipeline.py --limit 5

# Full pipeline (KG + ontology + export + validation)
python scripts/run_legal_pipeline.py --full --limit 10

# Export to multiple formats
python scripts/run_legal_pipeline.py --full --export json neo4j rdf

# Skip visualization (if plotly not installed)
python scripts/run_legal_pipeline.py --full --no-viz

# Use different LLM provider
python scripts/run_legal_pipeline.py --provider gemini --model gemini-2.0-flash
```

#### Script Options

| Option | Default | Description |
|--------|---------|-------------|
| `--db` | data/legal_docs.db | SQLite database path |
| `--output` | data/kg_output | Output directory |
| `--limit` | None | Limit number of articles |
| `--document` | None | Filter by document ID |
| `--provider` | openai | LLM provider (openai, gemini) |
| `--model` | gpt-4o-mini | LLM model name |
| `--full` | False | Run full pipeline with all steps |
| `--export` | json | Export formats (json, neo4j, rdf) |
| `--no-viz` | False | Skip visualization |

#### Python API Usage

```python
from semantica.legal import VietnameseLegalPipeline

# Initialize pipeline
pipeline = VietnameseLegalPipeline(
    db_path="data/legal_docs.db",
    llm_provider="openai",  # or "gemini"
    llm_model="gpt-4o-mini",
)

# Option 1: Step by step
kg = pipeline.run(limit=10)
ontology = pipeline.generate_ontology(kg)
validation = pipeline.validate(kg)
pipeline.export(kg, "output.json", format="json")
pipeline.visualize(kg, "kg_network.html")

# Option 2: Full pipeline
result = pipeline.run_full(
    output_dir="data/kg_output",
    limit=10,
    export_formats=["json", "neo4j"],
    visualize=True,
)
# result contains: kg, ontology, validation, exports, visualizations
```

#### Pipeline Methods

| Method | Description |
|--------|-------------|
| `run(limit, document_id)` | Extract entities & relations, build KG |
| `generate_ontology(kg)` | Generate ontology from KG |
| `validate(kg)` | QA validation with GraphValidator |
| `export(kg, path, format)` | Export to JSON/Neo4j/RDF |
| `visualize(kg, path)` | Visualize KG network (requires plotly) |
| `visualize_ontology(ont, path)` | Visualize ontology hierarchy |
| `run_full(output_dir, ...)` | Run all steps in sequence |

#### Export Formats

- **json**: JSON/JSON-LD format → `legal_kg.json`
- **neo4j**: Cypher queries → `legal_kg.cypher`
- **rdf**: RDF/Turtle format → `legal_kg.ttl`

#### Output Files

```
data/kg_output/
├── legal_kg.json          # KG in JSON format
├── legal_kg.cypher        # Neo4j Cypher queries (if --export neo4j)
├── legal_kg.ttl           # RDF Turtle (if --export rdf)
├── kg_network.html        # Interactive KG visualization
└── ontology_hierarchy.html # Ontology hierarchy visualization
```

### Legal Module Structure

```
semantica/legal/
├── __init__.py              # Exports all components
├── scraper/                 # Phase 00: Web scraping
│   ├── base.py              # Base scraper & data classes
│   ├── tvpl.py              # thuvienphapluat.vn scraper
│   └── hierarchy_extractor.py
├── models.py                # Phase 01: SQLAlchemy models
├── db_manager.py            # Phase 01: LegalDocumentDB
├── citation.py              # Phase 01: Citation formatter
├── crossref_detector.py     # Phase 03: Cross-reference detection
├── abbreviation_extractor.py # Phase 03.5: Abbreviation extraction
├── entity_types.py          # Phase 04: Legal entity types (9 types)
├── relation_types.py        # Phase 04: Legal relation types (8 types)
└── kg_pipeline.py           # Phase 04: VietnameseLegalPipeline
```

### Entity Types (Phase 04)

| Type | Description | Examples |
|------|-------------|----------|
| ORGANIZATION | Companies, agencies | CTCP, TNHH, cơ quan |
| PERSON_ROLE | Positions, roles | Giám đốc, TGĐ, HĐQT |
| LEGAL_TERM | Legal terminology | vốn điều lệ, cổ phần |
| MONETARY | Money amounts | 10 triệu đồng |
| DURATION | Time periods | 30 ngày, 6 tháng |
| PERCENTAGE | Percentages | 51%, trên 50% |
| CONDITION | Conditions | nếu, trường hợp |
| ACTION | Legal actions | thành lập, giải thể |
| PENALTY | Penalties | phạt tiền, đình chỉ |

### Relation Types (Phase 04)

| Type | Description | Example |
|------|-------------|---------|
| REQUIRES | X requires Y | Đăng ký DN yêu cầu vốn |
| HAS_PENALTY | Violation X has penalty Y | Vi phạm bị phạt tiền |
| APPLIES_TO | Rule X applies to Y | Điều 5 áp dụng cho CTCP |
| CONDITION_FOR | X is condition for Y | Vốn là điều kiện thành lập |
| DEFINED_AS | X is defined as Y | TGĐ là Tổng giám đốc |
| REFERENCES | Article X references Y | Điều 5 tham chiếu Điều 10 |
| AMENDS | X amends Y | Nghị định sửa đổi Luật |
| CONTAINS | X contains Y | Chương chứa Điều |

### Database Schema

```
legal_documents    → Documents (Luật, Nghị định, Thông tư)
legal_chapters     → Chương
legal_sections     → Mục
legal_articles     → Điều (main content)
legal_clauses      → Khoản
legal_points       → Điểm
legal_cross_references → Cross-references between articles
legal_abbreviations    → Vietnamese legal abbreviations
```

### Dependencies

- **Required**: openai or google-generativeai (for LLM)
- **Optional**: plotly (for visualization)

```bash
pip install plotly  # For visualization
```
