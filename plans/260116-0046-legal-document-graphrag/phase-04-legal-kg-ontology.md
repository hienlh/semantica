# Phase 04: Legal Knowledge Graph & Ontology

## Context Links

- [Research: Legal Ontology & KG](./research/researcher-02-legal-ontology-kg.md)
- [Phase 03: Entity Extraction](./phase-03-legal-entity-extraction.md)
- [Main Plan](./plan.md)

## Overview

Build legal knowledge graph from extracted entities and relationships. Uses ELI-inspired URIs for legislation identifiers, LKIF-style relationship types, and links KG nodes back to database articles via `kg_node_id`. Generates legal domain ontology using Semantica's OntologyGenerator.

## Key Insights (from Research)

- **ELI URIs**: `eli:vn:law:2014:20/article/5` format
- **LKIF relationships**: references, amends, supersedes, implements, defines
- **Node types**: LEGISLATION, ARTICLE, CLAUSE, PENALTY, PARTY
- **Provenance**: Store original citation text + confidence scores

## Requirements

### Functional

- FR-01: Build KG nodes from parsed documents (articles, clauses)
- FR-02: Build KG nodes from extracted entities (penalties, parties)
- FR-03: Create edges from cross-references (references, amends, supersedes)
- FR-04: Generate ELI-style URIs for Vietnamese legislation
- FR-05: Link KG nodes to database records via `kg_node_id`
- FR-06: Generate legal domain ontology with Vietnamese classes
- FR-07: Track provenance for all nodes and edges

### Non-Functional

- NFR-01: Support 100K+ nodes in graph
- NFR-02: Node lookup by URI <10ms
- NFR-03: Ontology validates with HermiT/Pellet
- NFR-04: Export to RDF/Turtle format

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Legal Knowledge Graph Builder                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐    ┌────────────────────┐    ┌──────────────────┐  │
│  │ Parsed Documents   │    │ Extracted Entities │    │ Cross-References │  │
│  │ (Phase 02)         │    │ (Phase 03)         │    │ (Phase 03)       │  │
│  └─────────┬──────────┘    └─────────┬──────────┘    └────────┬─────────┘  │
│            │                         │                         │            │
│            ↓                         ↓                         ↓            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        LegalKGBuilder                                │   │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐  │   │
│  │  │ URIGenerator      │  │ NodeBuilder       │  │ EdgeBuilder     │  │   │
│  │  │ - ELI format      │  │ - Article nodes   │  │ - references    │  │   │
│  │  │ - vn:law:2014:20  │  │ - Entity nodes    │  │ - amends        │  │   │
│  │  │ - /article/5      │  │ - Provenance      │  │ - supersedes    │  │   │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LegalProvenanceTracker                            │   │
│  │  - source_article_id (DB link)                                       │   │
│  │  - citation_text (original text)                                     │   │
│  │  - confidence                                                        │   │
│  │  - extraction_method                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Semantica KG Storage                              │   │
│  │  - GraphBuilder → knowledge_graph dict                               │   │
│  │  - GraphStore (Neo4j/FalkorDB optional)                              │   │
│  │  - VectorStore for embeddings                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LegalOntologyGenerator                            │   │
│  │  - Uses Semantica OntologyGenerator                                  │   │
│  │  - Vietnamese legal class hierarchy                                  │   │
│  │  - ELI-compatible properties                                         │   │
│  │  - Export to OWL/Turtle                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Related Code Files

- `/Users/hienlh/Projects/semantica/semantica/kg/__init__.py` - KG module
- `/Users/hienlh/Projects/semantica/semantica/kg/graph_builder.py` - GraphBuilder
- `/Users/hienlh/Projects/semantica/semantica/kg/provenance_tracker.py` - ProvenanceTracker
- `/Users/hienlh/Projects/semantica/semantica/ontology/__init__.py` - Ontology module
- `/Users/hienlh/Projects/semantica/semantica/ontology/ontology_generator.py` - OntologyGenerator

## Implementation Steps

### Step 1: Create URI Generator (1h)

Create `semantica/legal/uri_generator.py`:

```python
from typing import Optional
from urllib.parse import urljoin
import re

class LegalURIGenerator:
    """
    Generate ELI-style URIs for Vietnamese legal documents.

    Format: eli:vn:{type}:{year}:{number}/article/{num}/clause/{num}/point/{letter}
    Example: eli:vn:law:2014:20/article/5/clause/2/point/a
    """

    BASE_URI = "https://eli.gov.vn/"

    TYPE_MAP = {
        'law': 'law',
        'decree': 'decree',
        'decision': 'decision',
        'circular': 'circular',
    }

    def __init__(self, base_uri: Optional[str] = None):
        self.base_uri = base_uri or self.BASE_URI

    def generate_document_uri(
        self,
        document_number: str,
        document_type: str = 'law'
    ) -> str:
        """
        Generate URI for a legal document.

        Args:
            document_number: e.g., "20/2014/QH13"
            document_type: law, decree, decision, circular

        Returns:
            URI like "eli:vn:law:2014:20"
        """
        # Parse document number: "20/2014/QH13" -> year=2014, num=20
        match = re.match(r'(\d+)/(\d{4})/([A-Z0-9\-]+)', document_number)
        if match:
            num, year, authority = match.groups()
        else:
            # Fallback for non-standard formats
            parts = document_number.split('/')
            num = parts[0] if parts else 'unknown'
            year = parts[1] if len(parts) > 1 else '0000'

        type_code = self.TYPE_MAP.get(document_type, 'law')
        return f"eli:vn:{type_code}:{year}:{num}"

    def generate_article_uri(
        self,
        document_uri: str,
        article_number: int
    ) -> str:
        """Generate URI for an article."""
        return f"{document_uri}/article/{article_number}"

    def generate_clause_uri(
        self,
        article_uri: str,
        clause_number: int
    ) -> str:
        """Generate URI for a clause."""
        return f"{article_uri}/clause/{clause_number}"

    def generate_point_uri(
        self,
        clause_uri: str,
        point_letter: str
    ) -> str:
        """Generate URI for a point."""
        return f"{clause_uri}/point/{point_letter}"

    def generate_entity_uri(
        self,
        entity_type: str,
        entity_text: str,
        source_uri: str
    ) -> str:
        """
        Generate URI for an extracted entity.

        Args:
            entity_type: PENALTY, PARTY, etc.
            entity_text: Entity text content
            source_uri: Source article/clause URI

        Returns:
            URI like "eli:vn:law:2014:20/article/5/entity/penalty/1"
        """
        # Create hash-based identifier for entity
        entity_hash = abs(hash(entity_text)) % 10000
        return f"{source_uri}/entity/{entity_type.lower()}/{entity_hash}"

    def parse_uri(self, uri: str) -> dict:
        """Parse URI into components."""
        parts = uri.replace('eli:vn:', '').split('/')
        result = {'type': parts[0] if parts else None}

        if len(parts) > 1:
            result['year'] = parts[1]
        if len(parts) > 2:
            result['number'] = parts[2]

        # Parse article/clause/point
        for i, part in enumerate(parts):
            if part == 'article' and i + 1 < len(parts):
                result['article'] = int(parts[i + 1])
            elif part == 'clause' and i + 1 < len(parts):
                result['clause'] = int(parts[i + 1])
            elif part == 'point' and i + 1 < len(parts):
                result['point'] = parts[i + 1]

        return result
```

### Step 2: Create Legal KG Builder (2h)

Create `semantica/legal/kg_builder.py`:

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid

from semantica.kg import GraphBuilder, ProvenanceTracker
from semantica.utils.logging import get_logger

from .uri_generator import LegalURIGenerator
from .entity_types import LegalEntity, LegalEntityType, CrossReference

@dataclass
class KGNode:
    """Knowledge graph node."""
    id: str  # UUID
    uri: str  # ELI URI
    node_type: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    db_link_id: Optional[str] = None  # Link to database record

@dataclass
class KGEdge:
    """Knowledge graph edge."""
    id: str
    source_uri: str
    target_uri: str
    relationship: str  # references, amends, supersedes, contains, defines
    properties: Dict[str, Any] = field(default_factory=dict)

class LegalKGBuilder:
    """
    Build legal knowledge graph from parsed documents and extracted entities.

    Example:
        >>> builder = LegalKGBuilder()
        >>> kg = builder.build_from_document(parsed_doc, entities, cross_refs)
        >>> builder.export_to_rdf("legal_kg.ttl")
    """

    # Legal relationship types (LKIF-inspired)
    RELATIONSHIP_TYPES = {
        'references': 'References another legal provision',
        'amends': 'Modifies or updates another provision',
        'supersedes': 'Replaces previous legislation',
        'implements': 'Implements higher-level legislation',
        'defines': 'Defines a legal concept',
        'contains': 'Hierarchical containment (document > chapter > article)',
        'establishes_penalty': 'Article establishes penalty',
        'applies_to': 'Law applies to entity/domain',
    }

    def __init__(
        self,
        base_uri: Optional[str] = None,
        track_provenance: bool = True
    ):
        self.logger = get_logger("legal_kg_builder")
        self.uri_generator = LegalURIGenerator(base_uri)
        self.track_provenance = track_provenance

        # Use Semantica's GraphBuilder and ProvenanceTracker
        self.graph_builder = GraphBuilder()
        self.provenance_tracker = ProvenanceTracker() if track_provenance else None

        # Internal storage
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []

    def build_from_document(
        self,
        parsed_doc: Dict,
        entities: List[LegalEntity],
        cross_refs: List[CrossReference],
        db_manager = None  # LegalDocumentDB for linking
    ) -> Dict:
        """
        Build knowledge graph from parsed document.

        Args:
            parsed_doc: Parsed document from LegalDocumentParser
            entities: Extracted entities from LegalNERExtractor
            cross_refs: Detected cross-references
            db_manager: Optional database manager for kg_node_id linking

        Returns:
            Knowledge graph dict compatible with Semantica
        """
        self.logger.info(f"Building KG for document: {parsed_doc.get('metadata', {}).get('title')}")

        # Generate document URI
        doc_number = parsed_doc.get('metadata', {}).get('document_number', 'unknown')
        doc_type = parsed_doc.get('metadata', {}).get('document_type', 'law')
        doc_uri = self.uri_generator.generate_document_uri(doc_number, doc_type)

        # Create document node
        doc_node = self._create_document_node(parsed_doc, doc_uri)
        self._add_node(doc_node)

        # Create structural nodes (chapters, articles, clauses, points)
        self._build_structure_nodes(parsed_doc, doc_uri, db_manager)

        # Create entity nodes
        self._build_entity_nodes(entities, doc_uri)

        # Create edges from cross-references
        self._build_crossref_edges(cross_refs, doc_uri)

        # Build Semantica-compatible graph
        return self._to_semantica_format()

    def _create_document_node(self, parsed_doc: Dict, doc_uri: str) -> KGNode:
        """Create node for document."""
        metadata = parsed_doc.get('metadata', {})
        return KGNode(
            id=str(uuid.uuid4()),
            uri=doc_uri,
            node_type='LEGISLATION',
            label=metadata.get('title', 'Unknown Document'),
            properties={
                'document_number': metadata.get('document_number'),
                'document_type': metadata.get('document_type'),
                'effective_date': metadata.get('effective_date'),
                'issuing_authority': metadata.get('issuing_authority'),
            },
            db_link_id=parsed_doc.get('id')
        )

    def _build_structure_nodes(
        self,
        parsed_doc: Dict,
        doc_uri: str,
        db_manager = None
    ):
        """Build nodes for chapters, articles, clauses, points."""
        for chapter in parsed_doc.get('chapters', []):
            chapter_uri = f"{doc_uri}/chapter/{chapter['number']}"
            chapter_node = KGNode(
                id=str(uuid.uuid4()),
                uri=chapter_uri,
                node_type='CHAPTER',
                label=f"Chương {chapter['number']}: {chapter.get('title', '')}",
                properties={'number': chapter['number'], 'title': chapter.get('title')},
            )
            self._add_node(chapter_node)
            self._add_edge(doc_uri, chapter_uri, 'contains')

            for article in chapter.get('articles', []):
                article_uri = self.uri_generator.generate_article_uri(doc_uri, article['number'])
                article_node = KGNode(
                    id=str(uuid.uuid4()),
                    uri=article_uri,
                    node_type='ARTICLE',
                    label=f"Điều {article['number']}: {article.get('title', '')}",
                    properties={
                        'number': article['number'],
                        'title': article.get('title'),
                        'full_text': article.get('full_text', '')[:500],  # Truncate for KG
                    },
                )
                self._add_node(article_node)
                self._add_edge(chapter_uri, article_uri, 'contains')

                # Link to database if available
                if db_manager and article.get('db_id'):
                    db_manager.link_to_kg(article['db_id'], article_node.id, 'article')

                # Clauses
                for clause in article.get('clauses', []):
                    clause_uri = self.uri_generator.generate_clause_uri(article_uri, clause['number'])
                    clause_node = KGNode(
                        id=str(uuid.uuid4()),
                        uri=clause_uri,
                        node_type='CLAUSE',
                        label=f"Khoản {clause['number']}",
                        properties={
                            'number': clause['number'],
                            'text': clause.get('text', '')[:300],
                        },
                    )
                    self._add_node(clause_node)
                    self._add_edge(article_uri, clause_uri, 'contains')

                    # Points
                    for point in clause.get('points', []):
                        point_uri = self.uri_generator.generate_point_uri(clause_uri, point['letter'])
                        point_node = KGNode(
                            id=str(uuid.uuid4()),
                            uri=point_uri,
                            node_type='POINT',
                            label=f"Điểm {point['letter']}",
                            properties={
                                'letter': point['letter'],
                                'text': point.get('text', '')[:200],
                            },
                        )
                        self._add_node(point_node)
                        self._add_edge(clause_uri, point_uri, 'contains')

    def _build_entity_nodes(self, entities: List[LegalEntity], doc_uri: str):
        """Build nodes for extracted entities."""
        for entity in entities:
            entity_uri = self.uri_generator.generate_entity_uri(
                entity.entity_type.value,
                entity.text,
                doc_uri
            )
            entity_node = KGNode(
                id=str(uuid.uuid4()),
                uri=entity_uri,
                node_type=entity.entity_type.value,
                label=entity.text[:100],
                properties={
                    'full_text': entity.text,
                    'confidence': entity.confidence,
                    'penalty_type': entity.penalty_type,
                    'penalty_value': entity.penalty_value,
                },
            )
            self._add_node(entity_node)

            # Track provenance
            if self.provenance_tracker:
                self.provenance_tracker.track_entity(
                    entity_node.id,
                    source=doc_uri,
                    metadata={
                        'start_pos': entity.start_pos,
                        'end_pos': entity.end_pos,
                        'extraction_method': 'pattern_ner',
                    }
                )

    def _build_crossref_edges(self, cross_refs: List[CrossReference], doc_uri: str):
        """Build edges from cross-references."""
        for ref in cross_refs:
            # Generate target URI
            target_law = ref.target_law_number
            if target_law:
                target_doc_uri = self.uri_generator.generate_document_uri(target_law)
            else:
                target_doc_uri = doc_uri  # Same document

            target_uri = self.uri_generator.generate_article_uri(
                target_doc_uri,
                ref.target_article_num
            )

            # Get source URI (from source article)
            source_uri = f"{doc_uri}/article/{ref.source_article_id.split('/')[-1]}" if '/' in ref.source_article_id else doc_uri

            edge = KGEdge(
                id=str(uuid.uuid4()),
                source_uri=source_uri,
                target_uri=target_uri,
                relationship=ref.reference_type,
                properties={
                    'reference_text': ref.reference_text,
                    'confidence': ref.confidence,
                }
            )
            self.edges.append(edge)

            # Track provenance
            if self.provenance_tracker:
                self.provenance_tracker.track_relationship(
                    edge.id,
                    source=source_uri,
                    metadata={
                        'reference_text': ref.reference_text,
                        'start_pos': ref.start_pos,
                        'end_pos': ref.end_pos,
                    }
                )

    def _add_node(self, node: KGNode):
        """Add node to graph."""
        self.nodes[node.uri] = node

    def _add_edge(self, source_uri: str, target_uri: str, relationship: str, properties: Dict = None):
        """Add edge to graph."""
        edge = KGEdge(
            id=str(uuid.uuid4()),
            source_uri=source_uri,
            target_uri=target_uri,
            relationship=relationship,
            properties=properties or {}
        )
        self.edges.append(edge)

    def _to_semantica_format(self) -> Dict:
        """Convert to Semantica-compatible knowledge graph format."""
        entities = []
        for node in self.nodes.values():
            entities.append({
                'id': node.id,
                'text': node.label,
                'label': node.node_type,
                'uri': node.uri,
                'properties': node.properties,
                'db_link_id': node.db_link_id,
            })

        relationships = []
        for edge in self.edges:
            source_node = self.nodes.get(edge.source_uri)
            target_node = self.nodes.get(edge.target_uri)
            relationships.append({
                'id': edge.id,
                'source': source_node.id if source_node else edge.source_uri,
                'target': target_node.id if target_node else edge.target_uri,
                'relationship': edge.relationship,
                'properties': edge.properties,
            })

        return {
            'entities': entities,
            'relationships': relationships,
            'metadata': {
                'node_count': len(entities),
                'edge_count': len(relationships),
                'relationship_types': list(set(e['relationship'] for e in relationships)),
            }
        }

    def get_provenance(self, node_id: str) -> Optional[Dict]:
        """Get provenance for a node."""
        if self.provenance_tracker:
            return self.provenance_tracker.get_provenance(node_id)
        return None
```

### Step 3: Create Legal Ontology Generator (2h)

Create `semantica/legal/ontology_generator.py`:

```python
from typing import Dict, List, Optional
from semantica.ontology import OntologyGenerator, OWLGenerator, NamespaceManager

class LegalOntologyGenerator:
    """
    Generate legal domain ontology from knowledge graph.

    Produces OWL ontology with:
    - Vietnamese legal class hierarchy
    - ELI-compatible properties
    - LKIF-style relationships
    """

    # Vietnamese legal class hierarchy
    CLASS_HIERARCHY = {
        'VanBanPhapLuat': {  # Legal Document
            'label': 'Văn bản pháp luật',
            'subclasses': {
                'Luat': {'label': 'Luật'},
                'NghiDinh': {'label': 'Nghị định'},
                'ThongTu': {'label': 'Thông tư'},
                'QuyetDinh': {'label': 'Quyết định'},
            }
        },
        'CauTrucVanBan': {  # Document Structure
            'label': 'Cấu trúc văn bản',
            'subclasses': {
                'Chuong': {'label': 'Chương'},
                'Muc': {'label': 'Mục'},
                'Dieu': {'label': 'Điều'},
                'Khoan': {'label': 'Khoản'},
                'Diem': {'label': 'Điểm'},
            }
        },
        'ThucThe': {  # Entity
            'label': 'Thực thể',
            'subclasses': {
                'CoQuan': {'label': 'Cơ quan'},
                'ToChuc': {'label': 'Tổ chức'},
                'CaNhan': {'label': 'Cá nhân'},
            }
        },
        'HinhPhat': {  # Penalty
            'label': 'Hình phạt',
            'subclasses': {
                'PhatTien': {'label': 'Phạt tiền'},
                'PhatTu': {'label': 'Phạt tù'},
                'CanhCao': {'label': 'Cảnh cáo'},
            }
        },
    }

    # Property definitions (LKIF-inspired)
    PROPERTIES = {
        'object_properties': {
            'references': {
                'domain': 'Dieu',
                'range': 'Dieu',
                'label': 'tham chiếu đến'
            },
            'amends': {
                'domain': 'VanBanPhapLuat',
                'range': 'VanBanPhapLuat',
                'label': 'sửa đổi'
            },
            'supersedes': {
                'domain': 'VanBanPhapLuat',
                'range': 'VanBanPhapLuat',
                'label': 'thay thế'
            },
            'contains': {
                'domain': 'CauTrucVanBan',
                'range': 'CauTrucVanBan',
                'label': 'bao gồm'
            },
            'appliesTo': {
                'domain': 'VanBanPhapLuat',
                'range': 'ThucThe',
                'label': 'áp dụng cho'
            },
            'establishesPenalty': {
                'domain': 'Dieu',
                'range': 'HinhPhat',
                'label': 'quy định hình phạt'
            },
        },
        'data_properties': {
            'documentNumber': {
                'domain': 'VanBanPhapLuat',
                'range': 'xsd:string',
                'label': 'số văn bản'
            },
            'effectiveDate': {
                'domain': 'VanBanPhapLuat',
                'range': 'xsd:date',
                'label': 'ngày có hiệu lực'
            },
            'articleNumber': {
                'domain': 'Dieu',
                'range': 'xsd:integer',
                'label': 'số điều'
            },
            'penaltyAmount': {
                'domain': 'PhatTien',
                'range': 'xsd:decimal',
                'label': 'mức phạt'
            },
            'imprisonmentDuration': {
                'domain': 'PhatTu',
                'range': 'xsd:duration',
                'label': 'thời gian tù'
            },
        }
    }

    def __init__(
        self,
        base_uri: str = "https://ontology.law.gov.vn/",
        llm_provider = None
    ):
        self.base_uri = base_uri
        self.namespace_manager = NamespaceManager(base_uri=base_uri)

        # Use Semantica's OntologyGenerator if LLM available
        if llm_provider:
            self.semantica_generator = OntologyGenerator(
                llm_provider=llm_provider,
                base_uri=base_uri
            )
        else:
            self.semantica_generator = None

        self.owl_generator = OWLGenerator(base_uri=base_uri)

    def generate_base_ontology(self) -> str:
        """
        Generate base legal ontology with predefined classes and properties.

        Returns:
            OWL/Turtle string
        """
        # Build class definitions
        classes = []
        for class_name, class_def in self.CLASS_HIERARCHY.items():
            classes.append({
                'name': class_name,
                'label': class_def['label'],
                'parent': None
            })
            for subclass_name, subclass_def in class_def.get('subclasses', {}).items():
                classes.append({
                    'name': subclass_name,
                    'label': subclass_def['label'],
                    'parent': class_name
                })

        # Build property definitions
        properties = []
        for prop_name, prop_def in self.PROPERTIES['object_properties'].items():
            properties.append({
                'name': prop_name,
                'type': 'ObjectProperty',
                'domain': prop_def['domain'],
                'range': prop_def['range'],
                'label': prop_def['label']
            })
        for prop_name, prop_def in self.PROPERTIES['data_properties'].items():
            properties.append({
                'name': prop_name,
                'type': 'DatatypeProperty',
                'domain': prop_def['domain'],
                'range': prop_def['range'],
                'label': prop_def['label']
            })

        # Generate OWL
        return self.owl_generator.generate(
            classes=classes,
            properties=properties,
            format='turtle'
        )

    def generate_from_kg(self, kg: Dict) -> str:
        """
        Generate ontology from knowledge graph using Semantica pipeline.

        Args:
            kg: Knowledge graph dict with entities and relationships

        Returns:
            OWL/Turtle string
        """
        if self.semantica_generator:
            return self.semantica_generator.generate_ontology(kg, format='turtle')
        else:
            # Fallback to base ontology + inferred classes
            return self.generate_base_ontology()

    def merge_with_eli(self, base_ontology: str) -> str:
        """Merge with ELI (European Legislation Identifier) ontology imports."""
        eli_import = """
@prefix eli: <http://data.europa.eu/eli/ontology#> .
@prefix : <{base_uri}> .

# Import ELI concepts
:VanBanPhapLuat rdfs:subClassOf eli:LegalResource .
:Dieu rdfs:subClassOf eli:LegalResourceSubdivision .
""".format(base_uri=self.base_uri)
        return eli_import + '\n' + base_ontology
```

### Step 4: Create Database-KG Linker (1h)

Create `semantica/legal/db_kg_linker.py`:

```python
from typing import Dict, Optional
from uuid import UUID

class DatabaseKGLinker:
    """Link database records to KG nodes bidirectionally."""

    def __init__(self, db_manager, kg_builder):
        self.db = db_manager
        self.kg = kg_builder

    def link_all(self, parsed_doc: Dict, kg: Dict):
        """
        Link all database records to corresponding KG nodes.

        Updates kg_node_id in database and db_link_id in KG nodes.
        """
        # Map URIs to KG node IDs
        uri_to_node_id = {
            e['uri']: e['id']
            for e in kg.get('entities', [])
            if e.get('uri')
        }

        # Link documents
        doc_id = parsed_doc.get('id')
        doc_uri = self._build_doc_uri(parsed_doc)
        if doc_uri in uri_to_node_id:
            self.db.link_to_kg(doc_id, uri_to_node_id[doc_uri], 'document')

        # Link articles
        for chapter in parsed_doc.get('chapters', []):
            for article in chapter.get('articles', []):
                if 'db_id' in article:
                    article_uri = self._build_article_uri(doc_uri, article['number'])
                    if article_uri in uri_to_node_id:
                        self.db.link_to_kg(
                            article['db_id'],
                            uri_to_node_id[article_uri],
                            'article'
                        )

    def get_source_citation(self, kg_node_id: UUID) -> Optional[Dict]:
        """
        Get source citation for a KG node.

        Returns:
            Dict with article text and citation string
        """
        record = self.db.get_by_kg_node_id(kg_node_id)
        if not record:
            return None

        return {
            'citation': self._format_citation(record),
            'text': record.get('text') or record.get('full_text'),
            'article_number': record.get('article_number'),
            'document_title': record.get('document_title'),
        }

    def _build_doc_uri(self, parsed_doc: Dict) -> str:
        """Build document URI."""
        from .uri_generator import LegalURIGenerator
        gen = LegalURIGenerator()
        return gen.generate_document_uri(
            parsed_doc.get('metadata', {}).get('document_number', ''),
            parsed_doc.get('metadata', {}).get('document_type', 'law')
        )

    def _build_article_uri(self, doc_uri: str, article_num: int) -> str:
        """Build article URI."""
        return f"{doc_uri}/article/{article_num}"

    def _format_citation(self, record: Dict) -> str:
        """Format legal citation string."""
        parts = []
        if record.get('article_number'):
            parts.append(f"Điều {record['article_number']}")
        if record.get('clause_number'):
            parts.append(f"Khoản {record['clause_number']}")
        if record.get('point_letter'):
            parts.append(f"Điểm {record['point_letter']}")
        if record.get('document_title'):
            parts.append(f"- {record['document_title']}")

        return ', '.join(parts)
```

## Todo List

- [ ] Create `semantica/legal/uri_generator.py`
- [ ] Create `semantica/legal/kg_builder.py`
- [ ] Create `semantica/legal/ontology_generator.py`
- [ ] Create `semantica/legal/db_kg_linker.py`
- [ ] Test KG construction with sample document
- [ ] Validate ontology with HermiT/Pellet
- [ ] Export to RDF/Turtle format
- [ ] Test bidirectional DB-KG linking
- [ ] Integrate with Semantica's GraphStore

## Success Criteria

- [ ] ELI-style URIs generated correctly
- [ ] KG nodes link to DB records via kg_node_id
- [ ] Cross-reference edges created with provenance
- [ ] Ontology exports valid OWL/Turtle
- [ ] Provenance retrievable for all nodes

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| URI collision | Low | Medium | Include hash in entity URIs |
| Large graph performance | Medium | Medium | Batch processing, indexes |
| Ontology validation fails | Low | High | Pre-validate class hierarchy |
| DB-KG sync issues | Medium | Medium | Transaction-based linking |

## Security Considerations

- Validate URIs before graph insertion
- Sanitize property values
- Access control for provenance data

## Next Steps

After completing Phase 04:
1. Proceed to Phase 05: Legal GraphRAG Integration
2. Use KG with AgentContext for retrieval
3. Provenance enables article citations in responses
