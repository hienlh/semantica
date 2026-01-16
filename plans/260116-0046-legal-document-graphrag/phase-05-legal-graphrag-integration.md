# Phase 05: Legal GraphRAG Integration

## Context Links

- [Phase 04: KG & Ontology](./phase-04-legal-kg-ontology.md)
- [Main Plan](./plan.md)

## Overview

Integrate legal knowledge graph with Semantica's AgentContext for provenance-aware GraphRAG retrieval. Queries return answers grounded in specific articles/clauses with proper legal citations. Implements hybrid retrieval (vector + graph) with legal-domain optimizations.

## Key Insights (from Research & Architecture)

- **AgentContext**: Semantica's high-level GraphRAG interface
- **Hybrid retrieval**: vector_store + knowledge_graph
- **Provenance**: ProvenanceTracker links KG nodes to source articles
- **Multi-hop reasoning**: Traverse graph to find related provisions

## Requirements

### Functional

- FR-01: Query legal knowledge with natural language
- FR-02: Return answers with article/clause citations
- FR-03: Traverse cross-references for complete context
- FR-04: Support penalty lookup queries ("phạt bao nhiêu nếu...")
- FR-05: Support definition queries ("X là gì theo luật...")
- FR-06: Provide reasoning trace showing graph traversal

### Non-Functional

- NFR-01: Response latency <2s for single query
- NFR-02: Citation accuracy 100% (every claim has source)
- NFR-03: Support batch queries for document analysis
- NFR-04: Graceful degradation if graph unavailable

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LegalGraphRAG Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Query ──→ ┌─────────────────────────────────────────────────────────┐ │
│                 │ QueryAnalyzer                                            │ │
│                 │ - Intent detection (penalty, definition, procedure)     │ │
│                 │ - Entity extraction from query                          │ │
│                 │ - Graph traversal strategy selection                    │ │
│                 └───────────────────────┬─────────────────────────────────┘ │
│                                         ↓                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Semantica AgentContext                               │ │
│  │                                                                         │ │
│  │  ┌─────────────────┐      ┌─────────────────┐      ┌────────────────┐  │ │
│  │  │ VectorStore     │      │ ContextGraph    │      │ AgentMemory    │  │ │
│  │  │ (FAISS/Qdrant)  │←────→│ (Legal KG)      │←────→│ (History)      │  │ │
│  │  └────────┬────────┘      └────────┬────────┘      └────────────────┘  │ │
│  │           │                        │                                    │ │
│  │           ↓                        ↓                                    │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │  │ ContextRetriever (hybrid_alpha=0.7 for legal domain)            │   │ │
│  │  │ - Vector similarity search                                       │   │ │
│  │  │ - Graph traversal (max_hops=2 for cross-references)             │   │ │
│  │  │ - Entity linking to KG nodes                                     │   │ │
│  │  └─────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                    │
│                                         ↓                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    LegalProvenanceEnricher                              │ │
│  │ - Fetch source article/clause from DB via kg_node_id                   │ │
│  │ - Format legal citation (Điều X, Khoản Y, Điểm Z - Luật ABC)           │ │
│  │ - Include original text excerpt                                         │ │
│  └───────────────────────┬────────────────────────────────────────────────┘ │
│                          ↓                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    LLM Response Generator                               │ │
│  │ - Groq/OpenAI/LiteLLM via Semantica llms module                        │ │
│  │ - Prompt with context + citations                                       │ │
│  │ - Structured output with sources                                        │ │
│  └───────────────────────┬────────────────────────────────────────────────┘ │
│                          ↓                                                   │
│  Output: {                                                                   │
│    response: "Theo quy định...",                                             │
│    citations: [{article: "Điều 5", law: "Luật 20/2014", text: "..."}],      │
│    reasoning_path: ["query" → "Article 5" → "Cross-ref Article 10"],       │
│    confidence: 0.95                                                          │
│  }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

- `/Users/hienlh/Projects/semantica/semantica/context/__init__.py` - Context module
- `/Users/hienlh/Projects/semantica/semantica/context/agent_context.py` - AgentContext
- `/Users/hienlh/Projects/semantica/semantica/context/context_retriever.py` - ContextRetriever
- `/Users/hienlh/Projects/semantica/semantica/llms/__init__.py` - LLM providers
- `/Users/hienlh/Projects/semantica/semantica/kg/provenance_tracker.py` - ProvenanceTracker

## Implementation Steps

### Step 1: Create Query Analyzer (1h)

Create `semantica/legal/query_analyzer.py`:

```python
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re

class QueryIntent(Enum):
    """Legal query intent types."""
    PENALTY = "penalty"  # "phạt bao nhiêu nếu..."
    DEFINITION = "definition"  # "X là gì theo luật"
    PROCEDURE = "procedure"  # "thủ tục như thế nào"
    REQUIREMENT = "requirement"  # "điều kiện để..."
    REFERENCE = "reference"  # "Điều X quy định gì"
    GENERAL = "general"  # Other queries

@dataclass
class AnalyzedQuery:
    """Analyzed query with extracted information."""
    original_query: str
    intent: QueryIntent
    entities: List[str]
    article_refs: List[int]
    law_refs: List[str]
    keywords: List[str]
    traversal_depth: int  # Suggested max_hops

class LegalQueryAnalyzer:
    """Analyze legal queries to optimize retrieval."""

    INTENT_PATTERNS = {
        QueryIntent.PENALTY: [
            r'phạt\s+(bao\s+nhiêu|mấy|tiền)',
            r'hình\s+phạt',
            r'mức\s+phạt',
            r'bị\s+xử\s+phạt',
        ],
        QueryIntent.DEFINITION: [
            r'là\s+gì',
            r'định\s+nghĩa',
            r'được\s+hiểu\s+là',
            r'nghĩa\s+là',
        ],
        QueryIntent.PROCEDURE: [
            r'thủ\s+tục',
            r'quy\s+trình',
            r'các\s+bước',
            r'làm\s+thế\s+nào',
        ],
        QueryIntent.REQUIREMENT: [
            r'điều\s+kiện',
            r'yêu\s+cầu',
            r'cần\s+phải',
            r'phải\s+có',
        ],
        QueryIntent.REFERENCE: [
            r'Điều\s+\d+',
            r'quy\s+định\s+gì',
            r'nội\s+dung\s+của',
        ],
    }

    def analyze(self, query: str) -> AnalyzedQuery:
        """
        Analyze query to extract intent, entities, and traversal strategy.

        Args:
            query: Natural language query

        Returns:
            AnalyzedQuery with extracted information
        """
        # Detect intent
        intent = self._detect_intent(query)

        # Extract article references
        article_refs = self._extract_article_refs(query)

        # Extract law references
        law_refs = self._extract_law_refs(query)

        # Extract keywords
        keywords = self._extract_keywords(query)

        # Determine traversal depth based on intent
        traversal_depth = self._suggest_traversal_depth(intent, article_refs)

        return AnalyzedQuery(
            original_query=query,
            intent=intent,
            entities=[],  # Could use NER here
            article_refs=article_refs,
            law_refs=law_refs,
            keywords=keywords,
            traversal_depth=traversal_depth
        )

    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent from patterns."""
        query_lower = query.lower()
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE | re.UNICODE):
                    return intent
        return QueryIntent.GENERAL

    def _extract_article_refs(self, query: str) -> List[int]:
        """Extract article number references."""
        matches = re.findall(r'Điều\s+(\d+)', query, re.IGNORECASE)
        return [int(m) for m in matches]

    def _extract_law_refs(self, query: str) -> List[str]:
        """Extract law number references."""
        matches = re.findall(r'Luật\s+(?:số\s+)?(\d+/\d{4}/[A-Z0-9]+)', query, re.IGNORECASE)
        return matches

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords for search."""
        # Simple keyword extraction - could use underthesea
        stopwords = {'là', 'của', 'và', 'trong', 'theo', 'được', 'có', 'để', 'với'}
        words = query.split()
        return [w for w in words if w.lower() not in stopwords and len(w) > 2]

    def _suggest_traversal_depth(self, intent: QueryIntent, article_refs: List[int]) -> int:
        """Suggest graph traversal depth based on query characteristics."""
        if article_refs:
            return 1  # Direct reference, shallow traversal
        if intent == QueryIntent.PENALTY:
            return 2  # May need to follow cross-references
        if intent == QueryIntent.PROCEDURE:
            return 3  # Procedures often span multiple articles
        return 2  # Default
```

### Step 2: Create Provenance Enricher (1.5h)

Create `semantica/legal/provenance_enricher.py`:

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class LegalCitation:
    """Structured legal citation."""
    article_number: int
    clause_number: Optional[int] = None
    point_letter: Optional[str] = None
    document_title: str = ""
    document_number: str = ""
    text_excerpt: str = ""
    uri: str = ""

    def to_string(self) -> str:
        """Format as citation string."""
        parts = [f"Điều {self.article_number}"]
        if self.clause_number:
            parts.append(f"Khoản {self.clause_number}")
        if self.point_letter:
            parts.append(f"Điểm {self.point_letter}")
        if self.document_title:
            parts.append(f"- {self.document_title}")
        return ", ".join(parts)

class LegalProvenanceEnricher:
    """
    Enrich retrieval results with legal provenance (citations).

    Links KG nodes back to source articles in database and formats
    proper legal citations for response generation.
    """

    def __init__(self, db_manager, provenance_tracker):
        self.db = db_manager
        self.provenance = provenance_tracker

    def enrich(self, retrieved_contexts: List[Dict]) -> List[Dict]:
        """
        Enrich retrieved contexts with legal citations.

        Args:
            retrieved_contexts: List of retrieved context dicts from ContextRetriever

        Returns:
            Enriched contexts with 'citation' field
        """
        enriched = []
        for ctx in retrieved_contexts:
            enriched_ctx = dict(ctx)

            # Get KG node ID
            node_id = ctx.get('id') or ctx.get('node_id')
            if not node_id:
                enriched.append(enriched_ctx)
                continue

            # Fetch provenance
            prov = self.provenance.get_provenance(node_id) if self.provenance else None

            # Fetch database record
            db_record = self.db.get_by_kg_node_id(node_id) if self.db else None

            if db_record:
                citation = LegalCitation(
                    article_number=db_record.get('article_number', 0),
                    clause_number=db_record.get('clause_number'),
                    point_letter=db_record.get('point_letter'),
                    document_title=db_record.get('document_title', ''),
                    document_number=db_record.get('document_number', ''),
                    text_excerpt=db_record.get('text', '')[:500],
                    uri=ctx.get('uri', '')
                )
                enriched_ctx['citation'] = citation
                enriched_ctx['citation_string'] = citation.to_string()
                enriched_ctx['source_text'] = citation.text_excerpt

            if prov:
                enriched_ctx['provenance'] = {
                    'first_seen': prov.get('first_seen'),
                    'sources': prov.get('sources', []),
                    'confidence': prov.get('metadata', {}).get('confidence', 1.0)
                }

            enriched.append(enriched_ctx)

        return enriched

    def format_citations_for_llm(self, enriched_contexts: List[Dict]) -> str:
        """
        Format citations as context for LLM prompt.

        Returns string like:
        [1] Điều 5, Khoản 2 - Luật BHXH 2014: "Nội dung điều khoản..."
        [2] Điều 10 - Luật BHXH 2014: "Nội dung liên quan..."
        """
        formatted = []
        for i, ctx in enumerate(enriched_contexts, 1):
            citation = ctx.get('citation')
            if citation:
                formatted.append(
                    f"[{i}] {citation.to_string()}:\n\"{citation.text_excerpt}\""
                )
            else:
                text = ctx.get('text', ctx.get('content', ''))[:300]
                formatted.append(f"[{i}] {text}")

        return "\n\n".join(formatted)
```

### Step 3: Create Legal GraphRAG Context (2h)

Create `semantica/legal/graphrag.py`:

```python
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import os

from semantica.context import AgentContext, ContextGraph, ContextRetriever
from semantica.vector_store import VectorStore
from semantica.embeddings import EmbeddingGenerator
from semantica.llms import Groq, LiteLLM
from semantica.utils.logging import get_logger

from .query_analyzer import LegalQueryAnalyzer, AnalyzedQuery, QueryIntent
from .provenance_enricher import LegalProvenanceEnricher, LegalCitation

@dataclass
class LegalGraphRAGResponse:
    """Response from legal GraphRAG query."""
    response: str
    citations: List[LegalCitation]
    reasoning_path: List[str]
    confidence: float
    intent: QueryIntent
    metadata: Dict[str, Any]

class LegalGraphRAG:
    """
    Legal domain GraphRAG built on Semantica AgentContext.

    Provides provenance-aware retrieval with legal citations.

    Example:
        >>> rag = LegalGraphRAG(
        ...     kg=legal_kg,
        ...     db_manager=db,
        ...     llm_api_key=os.getenv("GROQ_API_KEY")
        ... )
        >>> result = rag.query("Phạt bao nhiêu nếu vi phạm Điều 5?")
        >>> print(result.response)
        >>> print(result.citations)
    """

    SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật Việt Nam.
Trả lời câu hỏi dựa trên các điều khoản pháp luật được cung cấp.
Luôn trích dẫn nguồn bằng số trong ngoặc vuông [1], [2], v.v.
Nếu không có đủ thông tin, hãy nói rõ điều đó.
Trả lời bằng tiếng Việt."""

    def __init__(
        self,
        kg: Dict,
        db_manager = None,
        provenance_tracker = None,
        llm_provider = None,
        llm_api_key: Optional[str] = None,
        llm_model: str = "llama-3.1-8b-instant",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        hybrid_alpha: float = 0.7,  # Higher weight to KG for legal domain
        vector_backend: str = "faiss"
    ):
        self.logger = get_logger("legal_graphrag")
        self.query_analyzer = LegalQueryAnalyzer()

        # Initialize embedding generator
        self.embedding_gen = EmbeddingGenerator(
            model_name=embedding_model,
            dimension=384
        )

        # Initialize vector store
        self.vector_store = VectorStore(
            backend=vector_backend,
            dimension=384
        )

        # Build context graph from KG
        self.context_graph = ContextGraph()
        self.context_graph.build_from_entities_and_relationships(
            entities=kg.get('entities', []),
            relationships=kg.get('relationships', [])
        )

        # Initialize AgentContext
        self.agent_context = AgentContext(
            vector_store=self.vector_store,
            knowledge_graph=self.context_graph,
            hybrid_alpha=hybrid_alpha,
            use_graph_expansion=True,
            max_expansion_hops=2
        )

        # Store documents in vector store
        self._index_kg_nodes(kg)

        # Initialize provenance enricher
        self.enricher = LegalProvenanceEnricher(
            db_manager=db_manager,
            provenance_tracker=provenance_tracker
        )

        # Initialize LLM
        if llm_provider:
            self.llm = llm_provider
        elif llm_api_key:
            self.llm = Groq(
                model=llm_model,
                api_key=llm_api_key
            )
        else:
            self.llm = None
            self.logger.warning("No LLM configured - will return raw context only")

    def _index_kg_nodes(self, kg: Dict):
        """Index KG nodes in vector store."""
        entities = kg.get('entities', [])
        if not entities:
            return

        texts = []
        metadata = []
        for entity in entities:
            # Combine label and properties for embedding
            text = entity.get('text', '') or entity.get('label', '')
            props = entity.get('properties', {})
            if props.get('full_text'):
                text += ' ' + props['full_text'][:500]

            texts.append(text)
            metadata.append({
                'id': entity.get('id'),
                'uri': entity.get('uri'),
                'label': entity.get('label'),
                'node_type': entity.get('label'),
            })

        # Generate embeddings
        embeddings = self.embedding_gen.generate_embeddings(texts)

        # Store in vector store
        self.vector_store.store_vectors(
            vectors=embeddings,
            metadata=metadata
        )

        self.logger.info(f"Indexed {len(texts)} KG nodes in vector store")

    def query(
        self,
        query: str,
        max_results: int = 10,
        include_reasoning: bool = True
    ) -> LegalGraphRAGResponse:
        """
        Query legal knowledge with natural language.

        Args:
            query: Natural language question
            max_results: Maximum contexts to retrieve
            include_reasoning: Include reasoning trace

        Returns:
            LegalGraphRAGResponse with answer and citations
        """
        # Analyze query
        analyzed = self.query_analyzer.analyze(query)
        self.logger.info(f"Query intent: {analyzed.intent}, depth: {analyzed.traversal_depth}")

        # Retrieve contexts
        retrieved = self.agent_context.retrieve(
            query=query,
            max_results=max_results,
            use_graph_expansion=True
        )

        # Enrich with provenance
        enriched = self.enricher.enrich(retrieved)

        # Build reasoning path
        reasoning_path = self._build_reasoning_path(enriched) if include_reasoning else []

        # Extract citations
        citations = [ctx.get('citation') for ctx in enriched if ctx.get('citation')]

        # Generate response with LLM
        if self.llm:
            response, confidence = self._generate_response(
                query=query,
                enriched_contexts=enriched,
                intent=analyzed.intent
            )
        else:
            response = self.enricher.format_citations_for_llm(enriched)
            confidence = 0.8

        return LegalGraphRAGResponse(
            response=response,
            citations=citations,
            reasoning_path=reasoning_path,
            confidence=confidence,
            intent=analyzed.intent,
            metadata={
                'query_analyzed': {
                    'intent': analyzed.intent.value,
                    'article_refs': analyzed.article_refs,
                    'law_refs': analyzed.law_refs,
                },
                'contexts_retrieved': len(enriched),
            }
        )

    def _generate_response(
        self,
        query: str,
        enriched_contexts: List[Dict],
        intent: QueryIntent
    ) -> tuple[str, float]:
        """Generate LLM response with citations."""
        # Format context for prompt
        context_text = self.enricher.format_citations_for_llm(enriched_contexts)

        # Build prompt based on intent
        intent_instruction = self._get_intent_instruction(intent)

        prompt = f"""{self.SYSTEM_PROMPT}

{intent_instruction}

Thông tin pháp luật liên quan:
{context_text}

Câu hỏi: {query}

Trả lời (trích dẫn nguồn bằng [số]):"""

        # Generate response
        try:
            response = self.llm.generate(prompt)
            confidence = 0.9 if enriched_contexts else 0.5
            return response, confidence
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return f"Không thể tạo câu trả lời: {e}", 0.0

    def _get_intent_instruction(self, intent: QueryIntent) -> str:
        """Get intent-specific instruction for prompt."""
        instructions = {
            QueryIntent.PENALTY: "Tập trung vào mức phạt và hình thức xử phạt.",
            QueryIntent.DEFINITION: "Cung cấp định nghĩa rõ ràng theo quy định pháp luật.",
            QueryIntent.PROCEDURE: "Liệt kê các bước thủ tục theo thứ tự.",
            QueryIntent.REQUIREMENT: "Liệt kê các điều kiện/yêu cầu cụ thể.",
            QueryIntent.REFERENCE: "Giải thích nội dung điều khoản được hỏi.",
            QueryIntent.GENERAL: "Trả lời dựa trên các quy định pháp luật liên quan.",
        }
        return instructions.get(intent, instructions[QueryIntent.GENERAL])

    def _build_reasoning_path(self, enriched_contexts: List[Dict]) -> List[str]:
        """Build reasoning trace showing how answer was derived."""
        path = ["Query received"]

        for i, ctx in enumerate(enriched_contexts[:5], 1):
            citation = ctx.get('citation_string', 'Unknown source')
            node_type = ctx.get('node_type', 'Unknown')
            path.append(f"Retrieved [{i}]: {node_type} - {citation}")

            # Add cross-reference traversals
            if ctx.get('expanded_from'):
                path.append(f"  → Expanded via cross-reference from {ctx['expanded_from']}")

        path.append("Response generated with citations")
        return path

    def query_with_reasoning(
        self,
        query: str,
        max_results: int = 10,
        max_hops: int = 2
    ) -> Dict:
        """
        Query with full reasoning trace (wrapper for AgentContext.query_with_reasoning).
        """
        if not self.llm:
            raise ValueError("LLM required for query_with_reasoning")

        result = self.agent_context.query_with_reasoning(
            query=query,
            llm_provider=self.llm,
            max_results=max_results,
            max_hops=max_hops
        )

        # Enrich with legal-specific provenance
        if 'retrieved_contexts' in result:
            enriched = self.enricher.enrich(result['retrieved_contexts'])
            citations = [ctx.get('citation') for ctx in enriched if ctx.get('citation')]
            result['citations'] = citations
            result['citation_strings'] = [c.to_string() for c in citations if c]

        return result
```

### Step 4: Create Integration Pipeline (1h)

Create `semantica/legal/pipeline.py`:

```python
from typing import Dict, Optional, Union
from pathlib import Path

from semantica.pipeline import PipelineBuilder, ExecutionEngine
from semantica.utils.logging import get_logger

from .parser import LegalDocumentParser
from .db_manager import LegalDocumentDB
from .ner_extractor import LegalNERExtractor
from .kg_builder import LegalKGBuilder
from .graphrag import LegalGraphRAG

class LegalDocumentPipeline:
    """
    End-to-end pipeline for legal document processing.

    Ingests PDF/DOCX → Parses → Extracts entities → Builds KG → Enables GraphRAG

    Example:
        >>> pipeline = LegalDocumentPipeline(
        ...     db_connection="postgresql://...",
        ...     llm_api_key=os.getenv("GROQ_API_KEY")
        ... )
        >>> pipeline.ingest("path/to/law.pdf")
        >>> result = pipeline.query("Điều 5 quy định gì?")
    """

    def __init__(
        self,
        db_connection: str,
        llm_api_key: Optional[str] = None,
        use_docling: bool = True
    ):
        self.logger = get_logger("legal_pipeline")

        # Initialize components
        self.db = LegalDocumentDB(db_connection)
        self.parser = LegalDocumentParser(db_connection=db_connection, use_docling=use_docling)
        self.ner = LegalNERExtractor()
        self.kg_builder = LegalKGBuilder(track_provenance=True)
        self.llm_api_key = llm_api_key

        # GraphRAG initialized after ingestion
        self.graphrag: Optional[LegalGraphRAG] = None
        self.knowledge_graph: Optional[Dict] = None

    def ingest(self, file_path: Union[str, Path]) -> str:
        """
        Ingest and process a legal document.

        Args:
            file_path: Path to PDF or DOCX

        Returns:
            Document ID
        """
        file_path = Path(file_path)
        self.logger.info(f"Ingesting: {file_path.name}")

        # Step 1: Parse document
        parsed = self.parser.parse(file_path)
        doc_id = self.db.store_document(parsed)
        self.logger.info(f"Stored document: {doc_id}")

        # Step 2: Extract entities from all clauses
        all_entities = []
        all_crossrefs = []
        doc_number = parsed.get('metadata', {}).get('document_number')

        for chapter in parsed.get('chapters', []):
            for article in chapter.get('articles', []):
                for clause in article.get('clauses', []):
                    result = self.ner.extract(
                        text=clause.get('text', ''),
                        source_article_id=str(article.get('db_id', '')),
                        current_law_number=doc_number
                    )
                    all_entities.extend(result.entities)
                    all_crossrefs.extend(result.cross_references)

        self.logger.info(f"Extracted {len(all_entities)} entities, {len(all_crossrefs)} cross-refs")

        # Step 3: Build knowledge graph
        kg = self.kg_builder.build_from_document(
            parsed_doc=parsed,
            entities=all_entities,
            cross_refs=all_crossrefs,
            db_manager=self.db
        )
        self.knowledge_graph = kg
        self.logger.info(f"Built KG: {kg['metadata']['node_count']} nodes, {kg['metadata']['edge_count']} edges")

        # Step 4: Initialize GraphRAG
        self._init_graphrag()

        return str(doc_id)

    def _init_graphrag(self):
        """Initialize GraphRAG with current knowledge graph."""
        if not self.knowledge_graph:
            return

        self.graphrag = LegalGraphRAG(
            kg=self.knowledge_graph,
            db_manager=self.db,
            provenance_tracker=self.kg_builder.provenance_tracker,
            llm_api_key=self.llm_api_key
        )

    def query(self, query: str, **kwargs) -> Dict:
        """
        Query the legal knowledge base.

        Args:
            query: Natural language question

        Returns:
            LegalGraphRAGResponse as dict
        """
        if not self.graphrag:
            raise ValueError("No documents ingested yet. Call ingest() first.")

        result = self.graphrag.query(query, **kwargs)
        return {
            'response': result.response,
            'citations': [c.to_string() for c in result.citations if c],
            'reasoning_path': result.reasoning_path,
            'confidence': result.confidence,
            'intent': result.intent.value,
        }

    def get_article_text(self, article_number: int, document_id: Optional[str] = None) -> Optional[str]:
        """Get full text of a specific article."""
        record = self.db.get_article_by_number(document_id, article_number)
        return record.full_text if record else None
```

### Step 5: Create CLI Interface (0.5h)

Create `semantica/legal/cli.py`:

```python
import click
import os
from pathlib import Path

from .pipeline import LegalDocumentPipeline

@click.group()
def cli():
    """Legal Document GraphRAG CLI."""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--db', default='postgresql://localhost/legal_db', help='Database connection string')
def ingest(file_path, db):
    """Ingest a legal document."""
    pipeline = LegalDocumentPipeline(
        db_connection=db,
        llm_api_key=os.getenv('GROQ_API_KEY')
    )
    doc_id = pipeline.ingest(file_path)
    click.echo(f"Ingested document: {doc_id}")

@cli.command()
@click.argument('query')
@click.option('--db', default='postgresql://localhost/legal_db', help='Database connection string')
def query(query, db):
    """Query the legal knowledge base."""
    pipeline = LegalDocumentPipeline(
        db_connection=db,
        llm_api_key=os.getenv('GROQ_API_KEY')
    )
    # Would need to rebuild KG from DB in real implementation
    result = pipeline.query(query)
    click.echo(f"Response: {result['response']}")
    click.echo(f"Citations: {result['citations']}")

if __name__ == '__main__':
    cli()
```

## Todo List

- [ ] Create `semantica/legal/query_analyzer.py`
- [ ] Create `semantica/legal/provenance_enricher.py`
- [ ] Create `semantica/legal/graphrag.py`
- [ ] Create `semantica/legal/pipeline.py`
- [ ] Create `semantica/legal/cli.py`
- [ ] Integration test with full pipeline
- [ ] Test citation accuracy (100% target)
- [ ] Benchmark response latency (<2s)
- [ ] Test multi-hop reasoning with cross-references
- [ ] Create Jupyter notebook demo

## Success Criteria

- [ ] Query returns answers with proper "Điều X, Khoản Y" citations
- [ ] Cross-references traversed for complete context
- [ ] Penalty queries extract correct amounts
- [ ] Reasoning trace shows graph traversal
- [ ] Response latency <2s for typical queries
- [ ] All citations verifiable in source documents

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM hallucination | Medium | High | Strict citation requirement in prompt |
| Missing cross-references | Medium | Medium | Multi-hop traversal |
| Slow vector search | Low | Medium | FAISS indexing optimization |
| Citation formatting errors | Low | Low | Unit tests for formatter |

## Security Considerations

- Validate query input before LLM
- Rate limit API calls
- Sanitize citations in output
- Audit log for queries

## Next Steps

After completing Phase 05:
1. Create comprehensive test suite
2. Build Jupyter notebook demo
3. Documentation and API reference
4. Performance optimization
5. Deploy to staging environment
