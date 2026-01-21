"""
Legal Knowledge Graph Builder for Vietnamese legal documents.

Builds a knowledge graph from extracted entities and relations,
with entity resolution, conflict detection, and temporal support.

Designed for Vietnamese legal documents with support for:
- Entity deduplication and merging
- Confidence-based conflict resolution
- Temporal validity tracking
- Integration with SQLite storage
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..utils.logging import get_logger

from .entity_types import LegalEntityType
from .ner_extractor import LegalEntity
from .relation_extractor import LegalRelation
from .relation_types import LegalRelationType


@dataclass
class KGNode:
    """Knowledge graph node representing a legal entity."""

    id: str  # Unique node ID
    text: str  # Entity text
    entity_type: LegalEntityType
    confidence: float
    sources: List[str] = field(default_factory=list)  # Source IDs (e.g., article IDs)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Temporal validity
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    def __hash__(self):
        return hash(self.id)


@dataclass
class KGEdge:
    """Knowledge graph edge representing a relation."""

    id: str  # Unique edge ID
    source_id: str  # Source node ID
    target_id: str  # Target node ID
    relation_type: LegalRelationType
    confidence: float
    sources: List[str] = field(default_factory=list)
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Temporal validity
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    def __hash__(self):
        return hash(self.id)


@dataclass
class LegalKnowledgeGraph:
    """Legal knowledge graph container."""

    nodes: Dict[str, KGNode] = field(default_factory=dict)
    edges: Dict[str, KGEdge] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: KGNode) -> None:
        """Add or update a node."""
        if node.id in self.nodes:
            # Merge with existing node
            existing = self.nodes[node.id]
            existing.sources.extend(node.sources)
            existing.confidence = max(existing.confidence, node.confidence)
            if node.metadata:
                existing.metadata.update(node.metadata)
        else:
            self.nodes[node.id] = node

    def add_edge(self, edge: KGEdge) -> None:
        """Add or update an edge."""
        if edge.id in self.edges:
            # Merge with existing edge
            existing = self.edges[edge.id]
            existing.sources.extend(edge.sources)
            existing.confidence = max(existing.confidence, edge.confidence)
            if edge.metadata:
                existing.metadata.update(edge.metadata)
        else:
            self.edges[edge.id] = edge

    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_edges_from(self, source_id: str) -> List[KGEdge]:
        """Get all edges from a source node."""
        return [e for e in self.edges.values() if e.source_id == source_id]

    def get_edges_to(self, target_id: str) -> List[KGEdge]:
        """Get all edges to a target node."""
        return [e for e in self.edges.values() if e.target_id == target_id]

    def get_neighbors(self, node_id: str) -> List[KGNode]:
        """Get all neighbor nodes."""
        neighbor_ids: Set[str] = set()
        for edge in self.edges.values():
            if edge.source_id == node_id:
                neighbor_ids.add(edge.target_id)
            elif edge.target_id == node_id:
                neighbor_ids.add(edge.source_id)
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary format."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "text": n.text,
                    "type": n.entity_type.value,
                    "confidence": n.confidence,
                    "sources": n.sources,
                    "metadata": n.metadata,
                    "valid_from": n.valid_from.isoformat() if n.valid_from else None,
                    "valid_until": n.valid_until.isoformat() if n.valid_until else None,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.relation_type.value,
                    "confidence": e.confidence,
                    "sources": e.sources,
                    "context": e.context,
                    "metadata": e.metadata,
                }
                for e in self.edges.values()
            ],
            "metadata": self.metadata,
        }


class LegalKGBuilder:
    """
    Build knowledge graph from legal entities and relations.

    Features:
    - Entity deduplication using text similarity
    - Confidence-based conflict resolution
    - Temporal edge support
    - Integration with Semantica GraphBuilder

    Example:
        >>> builder = LegalKGBuilder()
        >>> kg = builder.build(entities=entities, relations=relations)
        >>> print(f"Nodes: {len(kg.nodes)}, Edges: {len(kg.edges)}")
    """

    def __init__(
        self,
        merge_entities: bool = True,
        similarity_threshold: float = 0.85,
        resolve_conflicts: bool = True,
        enable_temporal: bool = False,
    ):
        """
        Initialize the Legal KG Builder.

        Args:
            merge_entities: Merge similar entities
            similarity_threshold: Minimum similarity for merging (0-1)
            resolve_conflicts: Resolve conflicting relations
            enable_temporal: Enable temporal edge tracking
        """
        self.logger = get_logger("legal_kg_builder")
        self.merge_entities = merge_entities
        self.similarity_threshold = similarity_threshold
        self.resolve_conflicts = resolve_conflicts
        self.enable_temporal = enable_temporal

    def build(
        self,
        entities: List[LegalEntity],
        relations: List[LegalRelation],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LegalKnowledgeGraph:
        """
        Build knowledge graph from entities and relations.

        Args:
            entities: Extracted legal entities
            relations: Extracted legal relations
            metadata: Optional graph metadata

        Returns:
            LegalKnowledgeGraph instance
        """
        kg = LegalKnowledgeGraph(metadata=metadata or {})

        # Step 1: Create nodes from entities
        entity_to_node: Dict[str, str] = {}  # entity text -> node ID
        for entity in entities:
            node_id = self._get_or_create_node(kg, entity, entity_to_node)
            entity_to_node[entity.text] = node_id

        # Step 2: Merge similar entities if enabled
        if self.merge_entities:
            entity_to_node = self._merge_similar_entities(kg, entity_to_node)

        # Step 3: Create edges from relations
        for relation in relations:
            self._create_edge(kg, relation, entity_to_node)

        # Step 4: Resolve conflicts if enabled
        if self.resolve_conflicts:
            self._resolve_conflicts(kg)

        # Update metadata
        kg.metadata["num_nodes"] = len(kg.nodes)
        kg.metadata["num_edges"] = len(kg.edges)
        kg.metadata["entity_resolution_applied"] = self.merge_entities
        kg.metadata["conflict_resolution_applied"] = self.resolve_conflicts
        kg.metadata["built_at"] = datetime.now().isoformat()

        return kg

    def _get_or_create_node(
        self,
        kg: LegalKnowledgeGraph,
        entity: LegalEntity,
        entity_to_node: Dict[str, str],
    ) -> str:
        """Get existing node ID or create new node."""
        # Check if entity already has a node
        if entity.text in entity_to_node:
            node_id = entity_to_node[entity.text]
            node = kg.get_node(node_id)
            if node:
                # Add source to existing node
                if entity.source_id not in node.sources:
                    node.sources.append(entity.source_id)
                return node_id

        # Create new node
        node_id = self._generate_node_id(entity)
        node = KGNode(
            id=node_id,
            text=entity.text,
            entity_type=entity.entity_type,
            confidence=entity.confidence,
            sources=[entity.source_id],
            metadata=entity.metadata.copy(),
        )
        kg.add_node(node)
        return node_id

    def _generate_node_id(self, entity: LegalEntity) -> str:
        """Generate a unique node ID."""
        # Use normalized text + entity type for ID
        normalized = entity.text.lower().replace(" ", "_")
        return f"{entity.entity_type.value}:{normalized}"

    def _merge_similar_entities(
        self,
        kg: LegalKnowledgeGraph,
        entity_to_node: Dict[str, str],
    ) -> Dict[str, str]:
        """Merge similar entities using text similarity."""
        nodes = list(kg.nodes.values())
        merged_mapping: Dict[str, str] = {}  # old node ID -> merged node ID

        # Group nodes by type
        nodes_by_type: Dict[LegalEntityType, List[KGNode]] = {}
        for node in nodes:
            if node.entity_type not in nodes_by_type:
                nodes_by_type[node.entity_type] = []
            nodes_by_type[node.entity_type].append(node)

        # Merge within each type
        for entity_type, type_nodes in nodes_by_type.items():
            for i, node1 in enumerate(type_nodes):
                if node1.id in merged_mapping:
                    continue

                for node2 in type_nodes[i + 1 :]:
                    if node2.id in merged_mapping:
                        continue

                    similarity = self._text_similarity(node1.text, node2.text)
                    if similarity >= self.similarity_threshold:
                        # Merge node2 into node1
                        self._merge_nodes(node1, node2)
                        merged_mapping[node2.id] = node1.id

        # Remove merged nodes
        for old_id in merged_mapping:
            if old_id in kg.nodes:
                del kg.nodes[old_id]

        # Update entity_to_node mapping
        updated_mapping: Dict[str, str] = {}
        for text, node_id in entity_to_node.items():
            final_id = node_id
            while final_id in merged_mapping:
                final_id = merged_mapping[final_id]
            updated_mapping[text] = final_id

        return updated_mapping

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using Jaccard coefficient."""
        # Normalize
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()

        # Exact match
        if t1 == t2:
            return 1.0

        # Substring match
        if t1 in t2 or t2 in t1:
            return 0.9

        # Character-level Jaccard
        set1 = set(t1)
        set2 = set(t2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _merge_nodes(self, target: KGNode, source: KGNode) -> None:
        """Merge source node into target node."""
        target.sources.extend(source.sources)
        target.confidence = max(target.confidence, source.confidence)
        target.metadata.update(source.metadata)

    def _create_edge(
        self,
        kg: LegalKnowledgeGraph,
        relation: LegalRelation,
        entity_to_node: Dict[str, str],
    ) -> Optional[str]:
        """Create edge from relation."""
        # Find node IDs
        source_id = entity_to_node.get(relation.subject.text)
        target_id = entity_to_node.get(relation.object.text)

        if not source_id or not target_id:
            # Create nodes if they don't exist
            if not source_id:
                source_id = self._get_or_create_node(
                    kg, relation.subject, entity_to_node
                )
                entity_to_node[relation.subject.text] = source_id
            if not target_id:
                target_id = self._get_or_create_node(
                    kg, relation.object, entity_to_node
                )
                entity_to_node[relation.object.text] = target_id

        # Generate edge ID
        edge_id = f"{source_id}--{relation.predicate.value}-->{target_id}"

        edge = KGEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation.predicate,
            confidence=relation.confidence,
            sources=[relation.source_id],
            context=relation.context,
            metadata=relation.metadata.copy(),
        )

        kg.add_edge(edge)
        return edge_id

    def _resolve_conflicts(self, kg: LegalKnowledgeGraph) -> None:
        """Resolve conflicting edges using confidence-based strategy."""
        # Group edges by (source, target) pair
        edge_groups: Dict[Tuple[str, str], List[KGEdge]] = {}
        for edge in kg.edges.values():
            key = (edge.source_id, edge.target_id)
            if key not in edge_groups:
                edge_groups[key] = []
            edge_groups[key].append(edge)

        # Check for conflicting relation types
        edges_to_remove: Set[str] = set()
        for (source_id, target_id), edges in edge_groups.items():
            if len(edges) <= 1:
                continue

            # Group by relation type
            by_type: Dict[LegalRelationType, List[KGEdge]] = {}
            for edge in edges:
                if edge.relation_type not in by_type:
                    by_type[edge.relation_type] = []
                by_type[edge.relation_type].append(edge)

            # Keep highest confidence edge per relation type
            for rel_type, type_edges in by_type.items():
                if len(type_edges) > 1:
                    type_edges.sort(key=lambda e: e.confidence, reverse=True)
                    # Keep the first (highest confidence), remove others
                    for edge in type_edges[1:]:
                        edges_to_remove.add(edge.id)

        # Remove lower confidence duplicates
        for edge_id in edges_to_remove:
            if edge_id in kg.edges:
                del kg.edges[edge_id]

    def add_temporal_edge(
        self,
        kg: LegalKnowledgeGraph,
        source_id: str,
        target_id: str,
        relation_type: LegalRelationType,
        valid_from: datetime,
        valid_until: Optional[datetime] = None,
        confidence: float = 1.0,
        source: str = "",
    ) -> Optional[str]:
        """
        Add a temporal edge to the knowledge graph.

        Args:
            kg: Knowledge graph to add edge to
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Type of relation
            valid_from: Start of validity period
            valid_until: End of validity period (None for ongoing)
            confidence: Edge confidence
            source: Source ID for provenance

        Returns:
            Edge ID or None if nodes don't exist
        """
        if source_id not in kg.nodes or target_id not in kg.nodes:
            return None

        edge_id = (
            f"{source_id}--{relation_type.value}-->{target_id}"
            f"@{valid_from.isoformat()}"
        )

        edge = KGEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            sources=[source] if source else [],
            valid_from=valid_from,
            valid_until=valid_until,
            metadata={"is_temporal": True},
        )

        kg.add_edge(edge)
        return edge_id

    def export_to_rdf(
        self,
        kg: LegalKnowledgeGraph,
        base_uri: str = "https://semantica.dev/legal/",
    ) -> str:
        """
        Export knowledge graph to RDF/Turtle format.

        Args:
            kg: Knowledge graph to export
            base_uri: Base URI for the ontology

        Returns:
            Turtle-formatted RDF string
        """
        lines = [
            f"@prefix legal: <{base_uri}> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
        ]

        # Export nodes
        for node in kg.nodes.values():
            node_uri = f"legal:{node.id.replace(':', '_')}"
            lines.append(f"{node_uri} a legal:{node.entity_type.value} ;")
            lines.append(f'    rdfs:label "{node.text}" ;')
            lines.append(f"    legal:confidence {node.confidence:.2f} .")
            lines.append("")

        # Export edges
        for edge in kg.edges.values():
            source_uri = f"legal:{edge.source_id.replace(':', '_')}"
            target_uri = f"legal:{edge.target_id.replace(':', '_')}"
            pred_uri = f"legal:{edge.relation_type.value}"
            lines.append(f"{source_uri} {pred_uri} {target_uri} .")

        return "\n".join(lines)
