"""
KG-SQLite Linker for Vietnamese legal documents.

Links Knowledge Graph nodes to SQLite database elements,
enabling bidirectional navigation between:
- KG nodes ↔ Articles/Clauses/Points in SQLite
- Cross-references ↔ KG edges

Provides unified query interface for:
- Context retrieval for RAG
- Provenance tracking
- Entity linking
"""

from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging import get_logger

from .db_manager import LegalDocumentDB
from .kg_builder import KGEdge, KGNode, LegalKnowledgeGraph
from .models import (
    LegalArticleModel,
    LegalChapterModel,
    LegalClauseModel,
    LegalCrossReferenceModel,
    LegalDocumentModel,
    LegalPointModel,
    LegalSectionModel,
)


class KGSQLiteLinker:
    """
    Links Knowledge Graph nodes to SQLite database elements.

    Enables:
    - Linking KG nodes to their source articles/clauses
    - Querying context for RAG applications
    - Bidirectional navigation between KG and DB

    Example:
        >>> linker = KGSQLiteLinker(db_path="data/legal_docs.db")
        >>> linker.link_kg_to_db(kg)
        >>> context = linker.get_context_for_node(node_id)
    """

    def __init__(self, db_path: str = "data/legal_docs.db"):
        """
        Initialize the linker.

        Args:
            db_path: Path to SQLite database
        """
        self.logger = get_logger("kg_sqlite_linker")
        self.db = LegalDocumentDB(db_path)

    def link_kg_to_db(
        self,
        kg: LegalKnowledgeGraph,
        update_db: bool = True,
    ) -> Dict[str, str]:
        """
        Link all KG nodes to their source database elements.

        Args:
            kg: Knowledge graph to link
            update_db: Update kg_node_id in database elements

        Returns:
            Mapping of node_id → element_id
        """
        node_to_element: Dict[str, str] = {}

        for node in kg.nodes.values():
            if not node.sources:
                continue

            # Use first source as primary element
            element_id = node.sources[0]
            node_to_element[node.id] = element_id

            if update_db:
                # Update database element with kg_node_id
                element_type = self._infer_element_type(element_id)
                if element_type:
                    success = self.db.link_to_kg(element_id, node.id, element_type)
                    if success:
                        self.logger.debug(
                            f"Linked {node.id} → {element_id} ({element_type})"
                        )

        return node_to_element

    def _infer_element_type(self, element_id: str) -> Optional[str]:
        """Infer element type from hierarchical ID format."""
        # ID format examples:
        # Document: "59-2020-QH14"
        # Chapter: "59-2020-QH14:c1"
        # Section: "59-2020-QH14:c1:m2"
        # Article: "59-2020-QH14:d5"
        # Clause: "59-2020-QH14:d5:k1"
        # Point: "59-2020-QH14:d5:k1:a"

        if ":" not in element_id:
            return "document"

        parts = element_id.split(":")
        last_part = parts[-1]

        if last_part.startswith("c"):
            return "chapter"
        elif last_part.startswith("m"):
            return "section"
        elif last_part.startswith("d"):
            return "article"
        elif last_part.startswith("k"):
            return "clause"
        elif last_part.startswith("pl"):
            return "appendix"
        elif last_part.startswith("mk"):
            return "appendix_item"
        elif len(last_part) == 1:  # Single letter like 'a', 'b'
            return "point"

        return None

    def get_context_for_node(
        self,
        node_id: str,
        kg: LegalKnowledgeGraph,
        include_neighbors: bool = True,
        max_depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Get full context for a KG node including database content.

        Args:
            node_id: Node ID to get context for
            kg: Knowledge graph
            include_neighbors: Include neighbor nodes' content
            max_depth: Depth for neighbor traversal

        Returns:
            Context dictionary with node info, text content, and neighbors
        """
        node = kg.get_node(node_id)
        if not node:
            return {"error": f"Node {node_id} not found"}

        context: Dict[str, Any] = {
            "node": {
                "id": node.id,
                "text": node.text,
                "type": node.entity_type.value,
                "confidence": node.confidence,
            },
            "sources": [],
            "neighbors": [],
        }

        # Get source content from database
        for source_id in node.sources:
            source_content = self._get_element_content(source_id)
            if source_content:
                context["sources"].append(source_content)

        # Get neighbor nodes if requested
        if include_neighbors and max_depth > 0:
            neighbors = kg.get_neighbors(node_id)
            for neighbor in neighbors:
                neighbor_context = {
                    "id": neighbor.id,
                    "text": neighbor.text,
                    "type": neighbor.entity_type.value,
                }
                # Get connecting edge
                edges = [
                    e for e in kg.edges.values()
                    if (e.source_id == node_id and e.target_id == neighbor.id) or
                       (e.target_id == node_id and e.source_id == neighbor.id)
                ]
                if edges:
                    neighbor_context["relation"] = edges[0].relation_type.value
                context["neighbors"].append(neighbor_context)

        return context

    def _get_element_content(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get content for a database element."""
        element_type = self._infer_element_type(element_id)
        if not element_type:
            return None

        content: Dict[str, Any] = {
            "element_id": element_id,
            "element_type": element_type,
        }

        try:
            if element_type == "article":
                article = self.db.get_article_by_id(element_id)
                if article:
                    content["title"] = article.title
                    content["content"] = article.content
                    content["raw_text"] = article.raw_text
                    content["article_number"] = article.article_number
            elif element_type == "clause":
                clause = self.db.get_clause_by_id(element_id)
                if clause:
                    content["content"] = clause.content
                    content["raw_text"] = clause.raw_text
                    content["clause_number"] = clause.clause_number
            elif element_type == "document":
                doc = self.db.get_document(element_id)
                if doc:
                    content["title"] = doc.title
                    content["so_hieu"] = doc.so_hieu
                    content["loai_van_ban"] = doc.loai_van_ban

            return content if len(content) > 2 else None
        except Exception as e:
            self.logger.warning(f"Error getting content for {element_id}: {e}")
            return None

    def get_nodes_for_element(
        self,
        element_id: str,
        kg: LegalKnowledgeGraph,
    ) -> List[KGNode]:
        """
        Get all KG nodes that reference a database element.

        Args:
            element_id: Database element ID
            kg: Knowledge graph

        Returns:
            List of nodes that have this element as a source
        """
        return [
            node for node in kg.nodes.values()
            if element_id in node.sources
        ]

    def get_edges_for_crossref(
        self,
        source_id: str,
        target_id: str,
        kg: LegalKnowledgeGraph,
    ) -> List[KGEdge]:
        """
        Get KG edges corresponding to a database cross-reference.

        Args:
            source_id: Source article ID
            target_id: Target article ID
            kg: Knowledge graph

        Returns:
            List of edges matching the cross-reference
        """
        matching_edges = []

        for edge in kg.edges.values():
            # Check if edge corresponds to this cross-reference
            edge_sources = set(edge.sources)
            if source_id in edge_sources:
                # Check if target matches
                target_node = kg.get_node(edge.target_id)
                if target_node and target_id in target_node.sources:
                    matching_edges.append(edge)

        return matching_edges

    def sync_crossrefs_to_kg(
        self,
        doc_id: str,
        kg: LegalKnowledgeGraph,
    ) -> int:
        """
        Sync database cross-references to KG edges.

        Args:
            doc_id: Document ID to sync cross-references from
            kg: Knowledge graph to update

        Returns:
            Number of edges added
        """
        from .relation_types import LegalRelationType

        added = 0

        with self.db.SessionLocal() as session:
            # Get all cross-references for this document
            crossrefs = (
                session.query(LegalCrossReferenceModel)
                .filter(LegalCrossReferenceModel.source_article_id.like(f"{doc_id}%"))
                .all()
            )

            for crossref in crossrefs:
                # Find or create nodes for source and target
                source_nodes = self.get_nodes_for_element(
                    crossref.source_article_id, kg
                )
                target_nodes = (
                    self.get_nodes_for_element(crossref.target_article_id, kg)
                    if crossref.target_article_id
                    else []
                )

                if source_nodes and target_nodes:
                    # Create edge
                    source_node = source_nodes[0]
                    target_node = target_nodes[0]

                    edge_id = (
                        f"{source_node.id}--REFERENCES-->{target_node.id}"
                    )

                    if edge_id not in kg.edges:
                        edge = KGEdge(
                            id=edge_id,
                            source_id=source_node.id,
                            target_id=target_node.id,
                            relation_type=LegalRelationType.REFERENCES,
                            confidence=crossref.confidence or 1.0,
                            sources=[crossref.id],
                            context=crossref.reference_text or "",
                            metadata={"from_crossref": True},
                        )
                        kg.add_edge(edge)
                        added += 1

        return added

    def build_context_window(
        self,
        node_ids: List[str],
        kg: LegalKnowledgeGraph,
        max_tokens: int = 2000,
    ) -> str:
        """
        Build a context window for RAG from multiple nodes.

        Args:
            node_ids: List of node IDs to include
            kg: Knowledge graph
            max_tokens: Approximate max tokens in context

        Returns:
            Combined context string
        """
        contexts = []
        estimated_tokens = 0
        chars_per_token = 4  # Rough estimate

        for node_id in node_ids:
            if estimated_tokens >= max_tokens:
                break

            context = self.get_context_for_node(node_id, kg, include_neighbors=False)
            if "error" in context:
                continue

            # Build context string for this node
            node_context = f"[{context['node']['type']}] {context['node']['text']}"

            for source in context.get("sources", []):
                if "content" in source:
                    node_context += f"\n  Nội dung: {source['content'][:500]}"
                if "title" in source:
                    node_context += f"\n  Tiêu đề: {source['title']}"

            estimated_tokens += len(node_context) // chars_per_token
            if estimated_tokens <= max_tokens:
                contexts.append(node_context)

        return "\n\n---\n\n".join(contexts)

    def get_stats(self, kg: LegalKnowledgeGraph) -> Dict[str, Any]:
        """
        Get linking statistics.

        Args:
            kg: Knowledge graph

        Returns:
            Statistics about KG-DB linking
        """
        linked_nodes = 0
        total_sources = 0

        for node in kg.nodes.values():
            if node.sources:
                linked_nodes += 1
                total_sources += len(node.sources)

        db_stats = self.db.count_stats()

        return {
            "kg_nodes": len(kg.nodes),
            "kg_edges": len(kg.edges),
            "linked_nodes": linked_nodes,
            "total_sources": total_sources,
            "db_documents": db_stats["documents"],
            "db_articles": db_stats["articles"],
            "db_clauses": db_stats["clauses"],
            "db_points": db_stats["points"],
        }
