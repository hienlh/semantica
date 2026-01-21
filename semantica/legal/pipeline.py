"""
Legal Semantica Pipeline for Vietnamese legal documents.

Orchestrates the full pipeline from document parsing to KG construction:
1. Load documents from SQLite database
2. Extract entities using LegalNERExtractor
3. Extract relations using LegalRelationExtractor
4. Build knowledge graph using LegalKGBuilder
5. Generate ontology using LegalOntologyGenerator
6. Link KG to SQLite using KGSQLiteLinker

Provides:
- Single document processing
- Batch document processing
- Progress tracking
- Export to multiple formats
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..utils.logging import get_logger

from .db_manager import LegalDocumentDB
from .entity_types import LegalEntityType
from .kg_builder import LegalKGBuilder, LegalKnowledgeGraph
from .kg_linker import KGSQLiteLinker
from .models import LegalArticleModel, LegalClauseModel, LegalDocumentModel, LegalPointModel
from .ner_extractor import LegalEntity, LegalNERExtractor
from .ontology_generator import LegalOntology, LegalOntologyGenerator
from .relation_extractor import LegalRelation, LegalRelationExtractor
from .relation_types import LegalRelationType


@dataclass
class PipelineConfig:
    """Configuration for the legal pipeline."""

    # Database
    db_path: str = "data/legal_docs.db"

    # NER extraction
    ner_method: str = "pattern"  # "pattern", "llm", "hybrid"
    ner_confidence_threshold: float = 0.5

    # Relation extraction
    rel_method: str = "pattern"  # "pattern", "llm", "hybrid"
    rel_confidence_threshold: float = 0.5
    bidirectional_relations: bool = False

    # KG building
    merge_entities: bool = True
    similarity_threshold: float = 0.85
    resolve_conflicts: bool = True
    enable_temporal: bool = False

    # Ontology
    include_base_ontology: bool = True
    ontology_base_uri: str = "https://semantica.dev/legal/ontology#"

    # LLM (optional)
    llm_provider: Optional[Any] = None


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    entities: List[LegalEntity] = field(default_factory=list)
    relations: List[LegalRelation] = field(default_factory=list)
    kg: Optional[LegalKnowledgeGraph] = None
    ontology: Optional[LegalOntology] = None
    stats: Dict[str, Any] = field(default_factory=dict)


class LegalSemanticaPipeline:
    """
    Full pipeline for legal document semantic processing.

    Orchestrates entity extraction, relation extraction, KG building,
    and ontology generation from Vietnamese legal documents.

    Example:
        >>> pipeline = LegalSemanticaPipeline()
        >>> result = pipeline.process_document("59-2020-QH14")
        >>> print(f"Entities: {len(result.entities)}, Relations: {len(result.relations)}")
        >>> print(f"KG nodes: {len(result.kg.nodes)}, edges: {len(result.kg.edges)}")

        # Export
        >>> pipeline.export_kg(result.kg, "output/kg.json")
        >>> pipeline.export_ontology(result.ontology, "output/ontology.ttl")
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.

        Args:
            config: Pipeline configuration
        """
        self.logger = get_logger("legal_semantica_pipeline")
        self.config = config or PipelineConfig()

        # Initialize components
        self.db = LegalDocumentDB(self.config.db_path)

        self.ner_extractor = LegalNERExtractor(
            llm_provider=self.config.llm_provider,
            method=self.config.ner_method,
            confidence_threshold=self.config.ner_confidence_threshold,
        )

        self.rel_extractor = LegalRelationExtractor(
            llm_provider=self.config.llm_provider,
            method=self.config.rel_method,
            confidence_threshold=self.config.rel_confidence_threshold,
            bidirectional=self.config.bidirectional_relations,
        )

        self.kg_builder = LegalKGBuilder(
            merge_entities=self.config.merge_entities,
            similarity_threshold=self.config.similarity_threshold,
            resolve_conflicts=self.config.resolve_conflicts,
            enable_temporal=self.config.enable_temporal,
        )

        self.ontology_generator = LegalOntologyGenerator(
            base_uri=self.config.ontology_base_uri,
        )

        self.linker = KGSQLiteLinker(self.config.db_path)

    def process_document(
        self,
        doc_id: str,
        include_ontology: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> PipelineResult:
        """
        Process a single document through the full pipeline.

        Args:
            doc_id: Document ID (e.g., "59-2020-QH14")
            include_ontology: Generate ontology
            progress_callback: Optional callback for progress updates

        Returns:
            PipelineResult with entities, relations, KG, and ontology
        """
        result = PipelineResult()

        def report_progress(stage: str, pct: float):
            if progress_callback:
                progress_callback(stage, pct)
            self.logger.info(f"{stage}: {pct:.0%}")

        # Step 1: Load document from database
        report_progress("Loading document", 0.0)
        doc = self.db.get_document(doc_id)
        if not doc:
            self.logger.error(f"Document {doc_id} not found")
            return result

        # Step 2: Collect text from all levels
        report_progress("Collecting text", 0.1)
        text_items = self._collect_document_text(doc)

        # Step 3: Extract entities
        report_progress("Extracting entities", 0.2)
        for item in text_items:
            entities = self.ner_extractor.extract(
                item["text"],
                item["source_id"],
            )
            result.entities.extend(entities)

        report_progress("Entities extracted", 0.4)
        self.logger.info(f"Extracted {len(result.entities)} entities")

        # Step 4: Extract relations
        report_progress("Extracting relations", 0.5)
        for item in text_items:
            # Get entities for this item
            item_entities = [
                e for e in result.entities if e.source_id == item["source_id"]
            ]
            relations = self.rel_extractor.extract(
                item["text"],
                item_entities,
                item["source_id"],
            )
            result.relations.extend(relations)

        report_progress("Relations extracted", 0.6)
        self.logger.info(f"Extracted {len(result.relations)} relations")

        # Step 5: Build knowledge graph
        report_progress("Building knowledge graph", 0.7)
        result.kg = self.kg_builder.build(
            entities=result.entities,
            relations=result.relations,
            metadata={"document_id": doc_id},
        )

        self.logger.info(
            f"Built KG: {len(result.kg.nodes)} nodes, {len(result.kg.edges)} edges"
        )

        # Step 6: Link KG to database
        report_progress("Linking KG to database", 0.8)
        self.linker.link_kg_to_db(result.kg, update_db=True)

        # Sync cross-references from database
        crossref_count = self.linker.sync_crossrefs_to_kg(doc_id, result.kg)
        self.logger.info(f"Synced {crossref_count} cross-references to KG")

        # Step 7: Generate ontology
        if include_ontology:
            report_progress("Generating ontology", 0.9)
            result.ontology = self.ontology_generator.generate_from_kg(
                result.kg,
                include_base=self.config.include_base_ontology,
            )

        # Collect stats
        result.stats = {
            "document_id": doc_id,
            "text_items": len(text_items),
            "entities": len(result.entities),
            "relations": len(result.relations),
            "kg_nodes": len(result.kg.nodes),
            "kg_edges": len(result.kg.edges),
            "crossrefs_synced": crossref_count,
        }

        if result.ontology:
            result.stats["ontology_classes"] = len(result.ontology.classes)
            result.stats["ontology_properties"] = len(result.ontology.properties)

        report_progress("Complete", 1.0)
        return result

    def process_batch(
        self,
        doc_ids: Optional[List[str]] = None,
        include_ontology: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> PipelineResult:
        """
        Process multiple documents and combine into single KG.

        Args:
            doc_ids: List of document IDs (None for all)
            include_ontology: Generate ontology
            progress_callback: Optional callback for progress updates

        Returns:
            Combined PipelineResult
        """
        if doc_ids is None:
            # Get all document IDs
            docs = self.db.list_documents()
            doc_ids = [doc.id for doc in docs]

        if not doc_ids:
            self.logger.warning("No documents to process")
            return PipelineResult()

        combined = PipelineResult()
        combined.kg = LegalKnowledgeGraph()

        for i, doc_id in enumerate(doc_ids):
            progress = i / len(doc_ids)
            if progress_callback:
                progress_callback(f"Processing {doc_id}", progress)

            result = self.process_document(
                doc_id,
                include_ontology=False,  # Generate once at end
            )

            # Combine results
            combined.entities.extend(result.entities)
            combined.relations.extend(result.relations)

            # Merge KG
            if result.kg:
                for node in result.kg.nodes.values():
                    combined.kg.add_node(node)
                for edge in result.kg.edges.values():
                    combined.kg.add_edge(edge)

        # Generate combined ontology
        if include_ontology and combined.kg:
            combined.ontology = self.ontology_generator.generate_from_kg(
                combined.kg,
                include_base=self.config.include_base_ontology,
            )

        # Combined stats
        combined.stats = {
            "documents_processed": len(doc_ids),
            "entities": len(combined.entities),
            "relations": len(combined.relations),
            "kg_nodes": len(combined.kg.nodes),
            "kg_edges": len(combined.kg.edges),
        }

        if combined.ontology:
            combined.stats["ontology_classes"] = len(combined.ontology.classes)
            combined.stats["ontology_properties"] = len(combined.ontology.properties)

        return combined

    def _collect_document_text(
        self,
        doc: LegalDocumentModel,
    ) -> List[Dict[str, str]]:
        """
        Collect text from all document levels.

        Uses fresh queries to avoid SQLAlchemy detached instance issues.
        """
        items: List[Dict[str, str]] = []
        doc_id = doc.id

        # Document level (if raw_text available)
        if doc.raw_text:
            items.append({
                "text": doc.raw_text,
                "source_id": doc.id,
            })

        # Query articles directly with fresh session
        with self.db.SessionLocal() as session:
            # Get all articles for this document
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            articles = (
                session.query(LegalArticleModel)
                .options(
                    joinedload(LegalArticleModel.clauses)
                    .joinedload(LegalClauseModel.points)
                )
                .filter(LegalArticleModel.document_id == doc_id)
                .order_by(LegalArticleModel.position)
                .all()
            )

            for article in articles:
                article_text = article.content or article.raw_text or ""
                if article_text:
                    items.append({
                        "text": article_text,
                        "source_id": article.id,
                    })

                # Clause level
                for clause in article.clauses:
                    if clause.content:
                        items.append({
                            "text": clause.content,
                            "source_id": clause.id,
                        })

                    # Point level
                    for point in clause.points:
                        if point.content:
                            items.append({
                                "text": point.content,
                                "source_id": point.id,
                            })

        return items

    def export_kg(
        self,
        kg: LegalKnowledgeGraph,
        output_path: str,
        format: str = "json",
    ) -> None:
        """
        Export knowledge graph to file.

        Args:
            kg: Knowledge graph to export
            output_path: Output file path
            format: Export format - "json", "rdf", or "graphml"
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(kg.to_dict(), f, ensure_ascii=False, indent=2)

        elif format == "rdf":
            rdf_content = self.kg_builder.export_to_rdf(kg)
            with open(path, "w", encoding="utf-8") as f:
                f.write(rdf_content)

        elif format == "graphml":
            self._export_graphml(kg, path)

        else:
            raise ValueError(f"Unknown format: {format}")

        self.logger.info(f"Exported KG to {output_path}")

    def _export_graphml(self, kg: LegalKnowledgeGraph, path: Path) -> None:
        """Export KG to GraphML format."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="d0" for="node" attr.name="label" attr.type="string"/>',
            '  <key id="d1" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="d2" for="edge" attr.name="type" attr.type="string"/>',
            '  <graph id="G" edgedefault="directed">',
        ]

        # Nodes
        for node in kg.nodes.values():
            safe_id = node.id.replace(":", "_").replace(">", "_")
            safe_text = node.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f'    <node id="{safe_id}">')
            lines.append(f'      <data key="d0">{safe_text}</data>')
            lines.append(f'      <data key="d1">{node.entity_type.value}</data>')
            lines.append("    </node>")

        # Edges
        for edge in kg.edges.values():
            safe_source = edge.source_id.replace(":", "_").replace(">", "_")
            safe_target = edge.target_id.replace(":", "_").replace(">", "_")
            lines.append(f'    <edge source="{safe_source}" target="{safe_target}">')
            lines.append(f'      <data key="d2">{edge.relation_type.value}</data>')
            lines.append("    </edge>")

        lines.append("  </graph>")
        lines.append("</graphml>")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def export_ontology(
        self,
        ontology: LegalOntology,
        output_path: str,
    ) -> None:
        """
        Export ontology to Turtle file.

        Args:
            ontology: Ontology to export
            output_path: Output file path
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(ontology.to_turtle())

        self.logger.info(f"Exported ontology to {output_path}")

    def get_context_for_query(
        self,
        query: str,
        kg: LegalKnowledgeGraph,
        top_k: int = 5,
    ) -> str:
        """
        Get context from KG for a query (simple keyword matching).

        Args:
            query: Query string
            kg: Knowledge graph
            top_k: Maximum nodes to include

        Returns:
            Context string for RAG
        """
        query_lower = query.lower()
        matching_nodes = []

        for node in kg.nodes.values():
            if query_lower in node.text.lower():
                matching_nodes.append((1.0, node.id))
            else:
                # Partial match scoring
                words = query_lower.split()
                matches = sum(1 for w in words if w in node.text.lower())
                if matches > 0:
                    score = matches / len(words)
                    matching_nodes.append((score, node.id))

        # Sort by score and take top_k
        matching_nodes.sort(reverse=True)
        node_ids = [nid for _, nid in matching_nodes[:top_k]]

        return self.linker.build_context_window(node_ids, kg)
