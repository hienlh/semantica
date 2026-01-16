# Semantica - Hướng Dẫn Sử Dụng

**Date:** 2026-01-15
**Version:** 0.2.1
**License:** MIT

---

## Tổng Quan Dự Án

**Semantica** là một framework Python mã nguồn mở cho việc xây dựng **Semantic Layer** và **Knowledge Engineering**. Mục tiêu chính: biến đổi dữ liệu thô, không có cấu trúc thành knowledge graphs sẵn sàng cho AI.

### Vấn Đề Giải Quyết

| Dữ liệu thực tế | AI cần gì |
|---|---|
| PDFs, emails, logs (không cấu trúc) | Ontologies (quy tắc rõ ràng) |
| Formats không đồng nhất, trùng lặp | Entities đã validate |
| Data silos rời rạc | Relationships (kết nối ngữ nghĩa) |

### Kiến Trúc 3 Lớp

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT LAYER                                                 │
│  PDF, DOCX, HTML, JSON, CSV, DBs, APIs, Streams             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SEMANTIC LAYER (Core Intelligence)                          │
│  Entity Extraction → Relation Mapping → Ontology Generation │
│  Context Engineering → Quality Assurance → Deduplication    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT LAYER                                                │
│  Knowledge Graphs → Vector Embeddings → Validated Ontologies│
│  → GraphRAG → AI Agents → Multi-Agent Systems               │
└─────────────────────────────────────────────────────────────┘
```

---

## Cài Đặt

### Yêu Cầu
- Python 3.8+ (khuyến nghị 3.9+)
- pip (phiên bản mới nhất)

### Cài Đặt Từ PyPI

```bash
# Cài đặt cơ bản
pip install semantica

# Cài đặt với tất cả dependencies
pip install semantica[all]

# Từ GitHub (nếu PyPI có lỗi)
pip install git+https://github.com/Hawksight-AI/semantica.git@main

# Xác nhận cài đặt
python -c "from semantica.parse import DoclingParser; DoclingParser(); print('✓ Semantica ready')"
```

### Cài Đặt Từ Source (Dev)

```bash
git clone https://github.com/Hawksight-AI/semantica.git
cd semantica
pip install -e ".[all]"      # Tất cả dependencies
pip install -e ".[dev]"      # Dev dependencies
```

---

## Cấu Trúc Modules

| Module | Chức Năng |
|--------|-----------|
| `ingest/` | Nhập dữ liệu từ nhiều nguồn (files, web, DBs, APIs, streams) |
| `parse/` | Parse documents (PDF, DOCX, HTML) |
| `normalize/` | Chuẩn hóa text |
| `split/` | Chunking/splitting documents |
| `semantic_extract/` | NER, relation extraction, triplets |
| `kg/` | Xây dựng Knowledge Graphs |
| `embeddings/` | Tạo embeddings (FastEmbed default) |
| `vector_store/` | Lưu trữ vectors (FAISS, etc.) |
| `graph_store/` | Graph databases (Neo4j, FalkorDB, Neptune) |
| `triplet_store/` | RDF triplets (Blazegraph, Jena) |
| `ontology/` | Tự động tạo ontologies (6-stage LLM pipeline) |
| `context/` | Agent memory, hybrid retrieval, GraphRAG |
| `llms/` | LLM providers (Groq, OpenAI, HuggingFace, LiteLLM) |
| `reasoning/` | Rule-based inference (Rete, forward/backward chaining) |
| `conflicts/` | Phát hiện & giải quyết conflicts |
| `deduplication/` | Loại bỏ trùng lặp |
| `export/` | Export (JSON, CSV, OWL, RDF, GraphML) |
| `visualization/` | Trực quan hóa graphs |
| `pipeline/` | Pipeline orchestration |

---

## Hướng Dẫn Sử Dụng Chi Tiết

### 1. Data Ingestion (Nhập Dữ Liệu)

```python
from semantica.ingest import FileIngestor, WebIngestor, DBIngestor

# File ingestion (recursive)
file_ingestor = FileIngestor(recursive=True)
sources = file_ingestor.ingest("documents/")

# Web ingestion
web_ingestor = WebIngestor(max_depth=3)
sources.extend(web_ingestor.ingest("https://example.com"))

# Database ingestion
db_ingestor = DBIngestor(connection_string="postgresql://...")
sources.extend(db_ingestor.ingest(query="SELECT * FROM articles"))

print(f"Đã nhập {len(sources)} nguồn")
```

**Supported formats:** PDF, DOCX, HTML, JSON, CSV, databases, RSS feeds, APIs, streams

### 2. Document Parsing

```python
from semantica.parse import DocumentParser, DoclingParser
from semantica.normalize import TextNormalizer
from semantica.split import TextSplitter

# Standard parsing
parser = DocumentParser()
parsed = parser.parse("document.pdf", format="auto")

# Enhanced parsing với Docling (tables, OCR)
docling_parser = DoclingParser(enable_ocr=True)
result = docling_parser.parse("complex_table.pdf")
print(f"Tables extracted: {len(result['tables'])}")

# Normalize
normalizer = TextNormalizer()
normalized = normalizer.normalize(parsed, clean_html=True)

# Split into chunks
splitter = TextSplitter(method="token", chunk_size=1000, chunk_overlap=200)
chunks = splitter.split(normalized)
```

### 3. Semantic Extraction (NER + Relations)

```python
from semantica.semantic_extract import NERExtractor, RelationExtractor

text = "Apple Inc., founded by Steve Jobs in 1976, acquired Beats Electronics for $3 billion."

# Extract entities
ner = NERExtractor(method="ml", model="en_core_web_sm")
entities = ner.extract(text)

# Extract relationships
rel_extractor = RelationExtractor(method="dependency", model="en_core_web_sm")
relationships = rel_extractor.extract(text, entities=entities)

print(f"Entities: {len(entities)}, Relationships: {len(relationships)}")
```

### 4. Knowledge Graph Construction

```python
from semantica.kg import GraphBuilder

# Build KG từ entities và relationships
builder = GraphBuilder()
kg = builder.build({"entities": entities, "relationships": relationships})

print(f"Nodes: {len(kg.get('entities', []))}")
print(f"Edges: {len(kg.get('relationships', []))}")
```

### 5. Embeddings & Vector Store

```python
from semantica.embeddings import EmbeddingGenerator
from semantica.vector_store import VectorStore

# Generate embeddings (FastEmbed default - nhanh hơn sentence-transformers)
emb_gen = EmbeddingGenerator(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384
)
embeddings = emb_gen.generate_embeddings(chunks, data_type="text")

# Store vectors
vector_store = VectorStore(backend="faiss", dimension=384)
vector_store.store_vectors(
    vectors=embeddings,
    metadata=[{"text": chunk} for chunk in chunks]
)

# Search
results = vector_store.search(query="supply chain", top_k=5)
```

### 6. Graph Store (Neo4j, FalkorDB, Neptune)

```python
from semantica.graph_store import GraphStore

# Neo4j
graph_store = GraphStore(
    backend="neo4j",
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
graph_store.add_nodes([
    {"id": "n1", "labels": ["Person"], "properties": {"name": "Alice"}}
])

# Amazon Neptune
neptune_store = GraphStore(
    backend="neptune",
    endpoint="your-cluster.us-east-1.neptune.amazonaws.com",
    port=8182,
    region="us-east-1",
    iam_auth=True
)
```

### 7. GraphRAG (Hybrid Vector + Graph Retrieval)

```python
from semantica.context import AgentContext
from semantica.llms import Groq
from semantica.vector_store import VectorStore
import os

# Initialize với hybrid retrieval
context = AgentContext(
    vector_store=VectorStore(backend="faiss"),
    knowledge_graph=kg,
    hybrid_alpha=0.75  # 75% KG, 25% Vector
)

# Configure LLM
llm = Groq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

# Query với multi-hop reasoning
result = context.query_with_reasoning(
    query="What IPs are associated with security alerts?",
    llm_provider=llm,
    max_results=10,
    max_hops=2
)

print(f"Response: {result['response']}")
print(f"Reasoning Path: {result['reasoning_path']}")
print(f"Confidence: {result['confidence']:.3f}")
```

**Kết quả benchmark:** 91% accuracy, cải thiện 30% so với vector-only RAG.

### 8. Ontology Generation

```python
from semantica.ontology import OntologyGenerator

# 6-stage LLM pipeline với HermiT/Pellet validation
generator = OntologyGenerator(llm_provider="openai", model="gpt-4")
ontology = generator.generate_from_documents(sources=["domain_docs/"])

print(f"Classes: {len(ontology.classes)}")
```

### 9. LLM Providers

```python
from semantica.llms import Groq, OpenAI, HuggingFaceLLM, LiteLLM

# Groq (fast inference)
groq = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))

# OpenAI
openai = OpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"))

# HuggingFace (local models)
hf = HuggingFaceLLM(model_name="gpt2")

# LiteLLM (100+ LLMs unified interface)
litellm = LiteLLM(model="openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Generate
response = groq.generate("What is AI?")

# Structured output
structured = groq.generate_structured("Extract entities from: Apple Inc. was founded by Steve Jobs.")
```

### 10. Reasoning & Inference

```python
from semantica.reasoning import Reasoner

reasoner = Reasoner()

# Define rules và facts
rules = ["IF Parent(?a, ?b) AND Parent(?b, ?c) THEN Grandparent(?a, ?c)"]
facts = ["Parent(Alice, Bob)", "Parent(Bob, Charlie)"]

# Forward chaining inference
inferred = reasoner.infer_facts(facts, rules)
print(f"Inferred: {inferred}")  # ['Grandparent(Alice, Charlie)']
```

### 11. Quality Assurance

```python
from semantica.deduplication import DuplicateDetector
from semantica.conflicts import ConflictDetector

entities = kg.get("entities", [])

# Detect conflicts
conflicts = ConflictDetector().detect_conflicts(entities)

# Detect duplicates (Jaro-Winkler similarity)
duplicates = DuplicateDetector(similarity_threshold=0.85).detect_duplicates(entities)

print(f"Conflicts: {len(conflicts)} | Duplicates: {len(duplicates)}")
```

### 12. Export & Visualization

```python
from semantica.visualization import KGVisualizer
from semantica.export import GraphExporter

# Visualize
viz = KGVisualizer(layout="force")
fig = viz.visualize_network(kg, output="interactive")
fig.show()

# Export
exporter = GraphExporter()
exporter.export(kg, format="json", output_path="graph.json")
exporter.export(kg, format="graphml", output_path="graph.graphml")
exporter.export(kg, format="owl", output_path="ontology.owl")
```

---

## Pipeline Orchestration

```python
from semantica.pipeline import PipelineBuilder, ExecutionEngine

# Build custom pipeline
pipeline = PipelineBuilder() \
    .add_step("ingest", "custom", func=ingest_data) \
    .add_step("extract", "custom", func=extract_entities) \
    .add_step("build", "custom", func=build_graph) \
    .build()

# Execute với parallel processing
result = ExecutionEngine().execute_pipeline(pipeline, parallel=True)
```

---

## Quick Start - Complete Example

```python
from semantica.semantic_extract import NERExtractor, RelationExtractor
from semantica.kg import GraphBuilder
from semantica.context import AgentContext, ContextGraph
from semantica.vector_store import VectorStore

# 1. Extract entities và relationships
ner = NERExtractor(method="ml", model="en_core_web_sm")
rel = RelationExtractor(method="dependency", model="en_core_web_sm")

text = "Apple Inc. was founded by Steve Jobs in 1976."
entities = ner.extract(text)
relationships = rel.extract(text, entities=entities)

# 2. Build knowledge graph
builder = GraphBuilder()
kg = builder.build({"entities": entities, "relationships": relationships})

# 3. Setup GraphRAG
vector_store = VectorStore(backend="faiss", dimension=384)
context_graph = ContextGraph()
context_graph.build_from_entities_and_relationships(
    entities=kg.get('entities', []),
    relationships=kg.get('relationships', [])
)

# 4. Query
context = AgentContext(vector_store=vector_store, knowledge_graph=context_graph)
results = context.retrieve("Who founded Apple?", max_results=5)
print(f"Found {len(results)} results")
```

---

## Cookbook (Interactive Notebooks)

### Introduction (20 notebooks)
| # | Topic | File |
|---|-------|------|
| 01 | Welcome | `introduction/01_Welcome_to_Semantica.ipynb` |
| 02 | Data Ingestion | `introduction/02_Data_Ingestion.ipynb` |
| 03 | Document Parsing | `introduction/03_Document_Parsing.ipynb` |
| 05 | Entity Extraction | `introduction/05_Entity_Extraction.ipynb` |
| 06 | Relation Extraction | `introduction/06_Relation_Extraction.ipynb` |
| 07 | Building KGs | `introduction/07_Building_Knowledge_Graphs.ipynb` |
| 08 | First KG | `introduction/08_Your_First_Knowledge_Graph.ipynb` |
| 12 | Embeddings | `introduction/12_Embedding_Generation.ipynb` |
| 13 | Vector Store | `introduction/13_Vector_Store.ipynb` |
| 19 | Context Module | `introduction/19_Context_Module.ipynb` |

### Advanced (12 notebooks)
- Advanced Extraction, Graph Analytics, Visualization
- Reasoning & Inference, Temporal KGs
- Advanced Context Engineering, Semantic Layer Construction

### Use Cases (14 domain-specific notebooks)
| Domain | Notebooks |
|--------|-----------|
| **Advanced RAG** | GraphRAG Complete, RAG vs GraphRAG Comparison |
| **Biomedical** | Drug Discovery Pipeline, Genomic Variant Analysis |
| **Finance** | Financial Data Integration MCP, Fraud Detection |
| **Blockchain** | DeFi Protocol Intelligence, Transaction Network Analysis |
| **Cybersecurity** | Real-Time Anomaly Detection, Threat Intelligence Hybrid RAG |
| **Intelligence** | Criminal Network Analysis, Orchestrator Worker |
| **Energy** | Energy Market Analysis |
| **Supply Chain** | Supply Chain Data Integration |

---

## Environment Variables

```bash
# LLM Providers
export GROQ_API_KEY="your-groq-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Graph Databases
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

# AWS Neptune (optional)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

---

## Resources

| Resource | Link |
|----------|------|
| GitHub | https://github.com/Hawksight-AI/semantica |
| PyPI | https://pypi.org/project/semantica/ |
| Discord | https://discord.gg/pMHguUzG |
| Discussions | https://github.com/Hawksight-AI/semantica/discussions |

---

## Summary

**Semantica** là framework production-ready cho:
- **Knowledge Graph Construction** từ unstructured data
- **GraphRAG** với 91% accuracy (30% improvement)
- **Ontology Generation** tự động với LLM
- **Multi-hop Reasoning** với explanation traces
- **100+ LLM providers** qua unified interface
- **Enterprise QA** (conflicts, deduplication, provenance)

**Best practices:**
1. Bắt đầu với cookbook `08_Your_First_Knowledge_Graph.ipynb`
2. Sử dụng FastEmbed (default) cho performance tốt
3. GraphRAG cho complex queries cần reasoning
4. Neo4j/FalkorDB cho production graph storage
5. LiteLLM cho flexibility với multiple LLM providers

---

## Deep Dive: LLM Integration

### Supported Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| **Groq** | Llama 3.1, Mixtral | Fast inference, free tier |
| **OpenAI** | GPT-3.5, GPT-4, GPT-4o | High quality, production |
| **HuggingFace** | Any local model (GPT2, etc.) | Local inference, privacy |
| **LiteLLM** | 100+ providers | Unified interface |

### LLM Usage Examples

```python
from semantica.llms import Groq, OpenAI, HuggingFaceLLM, LiteLLM
import os

# 1. Groq (Fast, Free Tier)
groq = Groq(
    model="llama-3.1-8b-instant",  # or "llama-3.1-70b-versatile", "mixtral-8x7b-32768"
    api_key=os.getenv("GROQ_API_KEY")
)
response = groq.generate("Explain knowledge graphs")
structured = groq.generate_structured("Extract entities from: Apple Inc was founded in 1976")

# 2. OpenAI
openai = OpenAI(
    model="gpt-4",  # or "gpt-3.5-turbo", "gpt-4o"
    api_key=os.getenv("OPENAI_API_KEY")
)
response = openai.generate("What is semantic search?")

# 3. HuggingFace (Local)
hf = HuggingFaceLLM(model_name="gpt2")  # or any HF model
response = hf.generate("Hello, world!")

# 4. LiteLLM (100+ providers)
litellm = LiteLLM(
    model="anthropic/claude-sonnet-4-20250514",  # or "openai/gpt-4o", "groq/llama-3.1-8b-instant"
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
response = litellm.generate("Explain GraphRAG")
```

### API Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `is_available()` | Check if API key configured | `bool` |
| `generate(prompt)` | Generate text response | `str` |
| `generate_structured(prompt)` | Generate JSON output | `Dict` |

---

## Deep Dive: Knowledge Graph (kg/)

### Core Classes

| Class | Purpose |
|-------|---------|
| `GraphBuilder` | Xây dựng KG từ entities/relationships |
| `EntityResolver` | Loại bỏ duplicate entities |
| `GraphAnalyzer` | Phân tích graph (centrality, communities) |
| `GraphValidator` | Validate graph structure |
| `TemporalGraphQuery` | Query graphs theo thời gian |
| `TemporalPatternDetector` | Phát hiện patterns theo thời gian |
| `ProvenanceTracker` | Track nguồn gốc dữ liệu |
| `CentralityCalculator` | Tính centrality metrics |
| `CommunityDetector` | Phát hiện communities (Louvain, Leiden) |
| `ConnectivityAnalyzer` | Phân tích connectivity |

### Algorithms Implemented

**Graph Construction:**
- Entity-relationship graph building
- Fuzzy string matching (Jaro-Winkler, Levenshtein)
- Semantic similarity matching
- Temporal edge support (valid_from/valid_until)

**Graph Analysis:**
- **Centrality:** Degree, Betweenness, Closeness, Eigenvector (power iteration)
- **Community Detection:** Louvain, Leiden, K-clique
- **Connectivity:** DFS-based component detection, bridge detection
- **Path Finding:** BFS shortest path, all-pairs shortest paths

**Temporal Operations:**
- Time-point/range queries
- Temporal pattern detection (sequences, cycles, trends)
- Graph evolution analysis
- Version management (snapshots)

### Knowledge Graph Examples

```python
from semantica.kg import (
    GraphBuilder,
    GraphAnalyzer,
    CentralityCalculator,
    CommunityDetector,
    TemporalGraphQuery,
    EntityResolver
)

# 1. Build Knowledge Graph
builder = GraphBuilder(merge_entities=True)
kg = builder.build(sources=[{
    "entities": [
        {"id": "e1", "text": "Apple Inc", "type": "ORG"},
        {"id": "e2", "text": "Steve Jobs", "type": "PERSON"},
        {"id": "e3", "text": "1976", "type": "DATE"}
    ],
    "relationships": [
        {"source": "e2", "target": "e1", "type": "FOUNDED"},
        {"source": "e1", "target": "e3", "type": "FOUNDED_IN"}
    ]
}])

# 2. Analyze Graph
analyzer = GraphAnalyzer()
analysis = analyzer.analyze_graph(kg)
print(f"Nodes: {analysis['node_count']}, Edges: {analysis['edge_count']}")
print(f"Density: {analysis['density']}")

# 3. Calculate Centrality
centrality_calc = CentralityCalculator()
degree = centrality_calc.calculate_degree_centrality(kg)
betweenness = centrality_calc.calculate_betweenness_centrality(kg)
print(f"Most central node: {max(degree, key=degree.get)}")

# 4. Detect Communities
community_detector = CommunityDetector()
communities = community_detector.detect_louvain(kg)
print(f"Found {len(set(communities.values()))} communities")

# 5. Entity Resolution (deduplication)
resolver = EntityResolver()
resolved_kg = resolver.resolve(kg, similarity_threshold=0.85)

# 6. Temporal Queries
temporal = TemporalGraphQuery(kg)
snapshot = temporal.query_at_time("2024-01-01")  # Graph state at specific time
pattern_detector = TemporalPatternDetector(kg)
trends = pattern_detector.detect_trends()
```

---

## Deep Dive: GraphRAG & Context (context/)

### Core Classes

| Class | Purpose |
|-------|---------|
| `AgentContext` | High-level interface cho RAG/GraphRAG |
| `ContextGraph` | In-memory context graph |
| `ContextRetriever` | Hybrid retrieval (vector + graph) |
| `AgentMemory` | Persistent agent memory |
| `EntityLinker` | Link entities across sources |

### AgentContext API

**Configuration:**
```python
from semantica.context import AgentContext
from semantica.vector_store import VectorStore

context = AgentContext(
    vector_store=VectorStore(backend="faiss", dimension=384),
    knowledge_graph=kg,  # Optional: enables GraphRAG
    retention_days=30,   # Memory retention
    max_memories=10000,  # Max memory items
    use_graph_expansion=True,  # Enable graph traversal
    max_expansion_hops=2,      # Max hops for expansion
    hybrid_alpha=0.5     # Balance: 0=vector only, 1=graph only
)
```

**Main Methods:**

| Method | Description |
|--------|-------------|
| `store(content, ...)` | Store memory/documents |
| `retrieve(query, ...)` | Retrieve context (auto-detects RAG/GraphRAG) |
| `query_with_reasoning(query, llm_provider, ...)` | Multi-hop reasoning + LLM response |
| `forget(...)` | Delete memories |
| `conversation(conversation_id)` | Get conversation history |
| `build_graph(entities, relationships)` | Build context graph manually |
| `link(text, entities)` | Link entities |
| `save(path)` / `load(path)` | Persistence |

### GraphRAG Complete Example

```python
from semantica.context import AgentContext, ContextGraph
from semantica.vector_store import VectorStore
from semantica.semantic_extract import NERExtractor, RelationExtractor
from semantica.kg import GraphBuilder
from semantica.llms import Groq
import os

# Step 1: Extract Entities & Relationships
ner = NERExtractor(method="ml", model="en_core_web_sm")
rel = RelationExtractor(method="dependency", model="en_core_web_sm")

documents = [
    "Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.",
    "Steve Jobs was CEO of Apple from 1997 until his death in 2011.",
    "Tim Cook became CEO of Apple in August 2011.",
    "Apple released the iPhone in 2007, revolutionizing smartphones."
]

all_entities = []
all_relationships = []
for doc in documents:
    entities = ner.extract(doc)
    relationships = rel.extract(doc, entities=entities)
    all_entities.extend(entities)
    all_relationships.extend(relationships)

# Step 2: Build Knowledge Graph
builder = GraphBuilder(merge_entities=True)
kg = builder.build({
    "entities": all_entities,
    "relationships": all_relationships
})

# Step 3: Setup GraphRAG Context
vector_store = VectorStore(backend="faiss", dimension=384)
context_graph = ContextGraph()
context_graph.build_from_entities_and_relationships(
    entities=kg.get('entities', []),
    relationships=kg.get('relationships', [])
)

context = AgentContext(
    vector_store=vector_store,
    knowledge_graph=context_graph,
    hybrid_alpha=0.75  # 75% graph, 25% vector
)

# Store documents in memory
context.store(documents, extract_entities=True)

# Step 4: Simple Retrieval
results = context.retrieve("Who founded Apple?", max_results=5)
for r in results:
    print(f"Score: {r['score']:.3f} | {r['content'][:100]}...")

# Step 5: Multi-Hop Reasoning với LLM
llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))

result = context.query_with_reasoning(
    query="What happened to Apple's leadership after Steve Jobs?",
    llm_provider=llm,
    max_results=10,
    max_hops=2
)

print(f"\n=== GraphRAG Response ===")
print(f"Response: {result['response']}")
print(f"Confidence: {result['confidence']:.3f}")
print(f"Reasoning Path: {result['reasoning_path']}")

# Step 6: Save/Load for Persistence
context.save("./context_state")
# Later: context.load("./context_state")
```

### Retrieval Strategies

| Strategy | When to Use | hybrid_alpha |
|----------|-------------|--------------|
| **Vector Only** | Simple semantic search | `use_graph=False` |
| **Graph Only** | Relationship queries | `hybrid_alpha=1.0` |
| **Hybrid (Default)** | Complex queries | `0.5` (balanced) |
| **Graph-Heavy** | Multi-hop reasoning | `0.75` |

### Memory Management

```python
# Store
memory_id = context.store("User likes Python", conversation_id="conv1")

# Retrieve
results = context.retrieve("What does user like?", conversation_id="conv1")

# Get specific memory
memory = context.get_memory(memory_id)

# List memories
memories = context.list(conversation_id="conv1", limit=50)

# Forget
context.forget(memory_id=memory_id)  # Single
context.forget(conversation_id="conv1")  # All in conversation
context.forget(days_old=90)  # Older than 90 days

# Statistics
stats = context.stats()
health = context.health()
```

---

## Benchmark Results

| Metric | Vector-Only RAG | GraphRAG |
|--------|-----------------|----------|
| Accuracy | ~61% | **91%** |
| Multi-hop Reasoning | Poor | **Excellent** |
| Relationship Queries | Poor | **Excellent** |
| Simple Queries | Good | Good |

GraphRAG đạt **30% improvement** so với traditional RAG nhờ:
- Hybrid vector + graph retrieval
- Multi-hop graph traversal
- Entity linking across documents
- Reasoning traces cho explainability
