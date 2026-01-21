"""
Legal KG Pipeline - Build Knowledge Graph from legal documents.

Uses Semantica NERExtractor, RelationExtractor, and GraphBuilder directly.
No wrapper classes - just configuration and orchestration.

Features:
- Entity extraction with legal-specific types
- Relation extraction with legal relation types
- Cross-reference integration from Phase 03
- Ontology generation from KG
- Export to multiple formats (JSON, Neo4j, RDF, etc.)
- Visualization (network, hierarchy, etc.)
- Quality assurance validation
"""

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ..semantic_extract import NERExtractor, RelationExtractor
from ..kg import GraphBuilder, GraphValidator
from ..ontology import OntologyGenerator
from ..export import export_json, export_lpg, export_rdf
from ..visualization import KGVisualizer, OntologyVisualizer, visualize_kg
from ..utils.logging import get_logger

from .db_manager import LegalDocumentDB
from .entity_types import LEGAL_ENTITY_TYPES, LEGAL_NER_PROMPT_VI, LEGAL_ABBREVIATIONS
from .relation_types import (
    LEGAL_RELATION_TYPES,
    LEGAL_RELATION_TYPES_SET,
    LEGAL_RELATION_PROMPT_VI,
    LEGAL_RELATION_FREE_PROMPT_VI,
    LEGAL_RELATION_COT_PROMPT_VI,
    LEGAL_RELATION_PATTERNS,
)
from .relation_validator import RelationValidator
from .entity_resolver import EntityResolver

from ..semantic_extract.providers import create_provider
from .models import LegalArticleModel, LegalCrossReferenceModel


def slugify_vietnamese(text: str) -> str:
    """
    Convert Vietnamese text to slug format.

    Example: "Công ty cổ phần" -> "cong-ty-co-phan"
    """
    # Normalize unicode (NFD decomposes accented chars)
    text = unicodedata.normalize("NFD", text)
    # Remove diacritics (combining characters)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Convert to lowercase
    text = text.lower()
    # Replace đ/Đ with d
    text = text.replace("đ", "d").replace("Đ", "d")
    # Replace non-alphanumeric with hyphen
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Remove leading/trailing hyphens, collapse multiple hyphens
    text = re.sub(r"-+", "-", text).strip("-")
    return text


class VietnameseLegalPipeline:
    """
    Build Knowledge Graph from legal documents using Semantica core.

    Uses Semantica components directly with legal-specific configuration.

    Example:
        >>> pipeline = VietnameseLegalPipeline("data/legal_docs.db")
        >>> kg = pipeline.run()
        >>> print(f"Entities: {len(kg['entities'])}, Edges: {len(kg['relationships'])}")
    """

    def __init__(
        self,
        db_path: str,
        llm_provider: str = "gemini",
        llm_model: str = "gemini-2.0-flash",
        **config,
    ):
        """
        Initialize pipeline.

        Args:
            db_path: Path to SQLite database
            llm_provider: LLM provider for extraction (gemini, openai, etc.)
            llm_model: LLM model name
            **config: Additional config for extractors
        """
        self.logger = get_logger("legal_kg_pipeline")
        self.db = LegalDocumentDB(db_path)
        self.config = config

        # Initialize Semantica NERExtractor with legal config
        self.ner = NERExtractor(
            method="llm",
            entity_types=LEGAL_ENTITY_TYPES,
            provider=llm_provider,
            llm_model=llm_model,
            min_confidence=config.get("min_confidence", 0.5),
        )

        # Initialize Semantica RelationExtractor with Vietnamese legal config
        # - relation_patterns: Vietnamese patterns from LEGAL_RELATION_PATTERNS
        # - fallback_predicate: "LIÊN_QUAN" for Vietnamese fallback relations
        # - disable_cooccurrence_fallback=True to avoid noisy fallback relations
        # - disable_last_resort_fallback=True to avoid weak adjacency-based relations
        self.rel_extractor = RelationExtractor(
            method="llm",
            relation_types=LEGAL_RELATION_TYPES,
            relation_patterns=LEGAL_RELATION_PATTERNS,
            fallback_predicate="LIÊN_QUAN",
            provider=llm_provider,
            llm_model=llm_model,
            min_confidence=config.get("min_confidence", 0.5),
            disable_cooccurrence_fallback=True,
            disable_last_resort_fallback=True,
        )

        # Store LLM config for fallback Vietnamese relation extraction
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.confidence_threshold = config.get("confidence_threshold", 0.6)

        # Initialize RelationValidator for post-processing
        self.relation_validator = RelationValidator(
            defined_types=LEGAL_RELATION_TYPES,
            enable_semantic_validation=config.get("enable_semantic_validation", True),
        )

        # Initialize EntityResolver for entity deduplication
        self.entity_resolver = EntityResolver(
            abbreviations=LEGAL_ABBREVIATIONS,
            scope_by_document=config.get("scope_entities_by_document", True),
        )

        # Initialize Semantica GraphBuilder
        # Use exact matching to avoid merging different entities with similar names
        # This preserves relationship integrity (source/dest IDs match entity IDs)
        self.builder = GraphBuilder(
            merge_entities=config.get("merge_entities", False),
            entity_resolution_strategy=config.get("entity_resolution_strategy", "exact"),
            resolve_conflicts=config.get("resolve_conflicts", True),
        )

    def _extract_relations_vietnamese(
        self, text: str, entities: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract relations using Vietnamese prompt with FREE relation types.

        LLM will discover relation types from context (not predefined list).
        Returns relation dicts directly (not Relation objects).
        """
        import json

        if not text or not entities:
            return []

        # Create LLM provider
        try:
            llm = create_provider(self.llm_provider, model=self.llm_model)
            if not llm.is_available():
                self.logger.warning(f"{self.llm_provider} not available for relation extraction")
                return []
        except Exception as e:
            self.logger.warning(f"Failed to create LLM provider: {e}")
            return []

        # Format entities for prompt
        entities_str = "\n".join([f"- {e.text} [{e.label}]" for e in entities])

        # Use Vietnamese CoT extraction prompt (with step-by-step reasoning)
        prompt = LEGAL_RELATION_COT_PROMPT_VI.format(
            entities=entities_str,
            text=text,
        )

        try:
            # Generate response
            response = llm.generate(prompt)

            # Parse JSON from response
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if not json_match:
                self.logger.debug(f"No JSON array found in response: {response[:200]}")
                return []

            relations_data = json.loads(json_match.group())

            # Convert to relation dicts
            relations = []
            for r in relations_data:
                if not isinstance(r, dict):
                    continue

                subject = r.get("subject", "")
                predicate = r.get("predicate", "")
                obj = r.get("object", "")
                confidence = r.get("confidence", 0.8)

                if not subject or not predicate or not obj:
                    continue

                if confidence < self.confidence_threshold:
                    continue

                relations.append({
                    "subject_text": subject,
                    "predicate": predicate,
                    "object_text": obj,
                    "confidence": confidence,
                })

            # Validate relations (filter self-refs, normalize types, persist new types)
            relations = self.relation_validator.validate(relations)

            return relations

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse relation JSON: {e}")
            return []
        except Exception as e:
            self.logger.warning(f"Relation extraction failed: {e}")
            return []

    def run(
        self,
        limit: Optional[int] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run full KG pipeline.

        Args:
            limit: Limit number of articles to process (for testing)
            document_id: Only process articles from this document

        Returns:
            KG dict with {entities, relationships, metadata}
        """
        self.logger.info("Starting Legal KG Pipeline")

        # 1. Load articles from SQLite
        articles = self._load_articles(limit=limit, document_id=document_id)
        self.logger.info(f"Loaded {len(articles)} articles")

        # 2. Extract entities from each article
        all_entities = []
        entities_by_article = {}  # Store entities per article for relation extraction

        for article in articles:
            if not article.content:
                continue

            self.logger.debug(f"Extracting entities from {article.id}")
            entities = self.ner.extract_entities(article.content)

            # Add source_id to metadata for provenance
            for entity in entities:
                if not hasattr(entity, "metadata") or entity.metadata is None:
                    entity.metadata = {}
                entity.metadata["source_id"] = article.id
                entity.metadata["document_id"] = article.document_id

            entities_by_article[article.id] = entities
            all_entities.extend(entities)

        self.logger.info(f"Extracted {len(all_entities)} entities")

        # 3. Extract relations from each article using Semantica RelationExtractor
        all_relations = []
        for article in articles:
            if not article.content:
                continue

            article_entities = entities_by_article.get(article.id, [])
            if not article_entities:
                continue

            self.logger.debug(f"Extracting relations from {article.id}")
            # Use Semantica RelationExtractor (returns Relation objects)
            relations = self.rel_extractor.extract_relations(
                article.content, article_entities
            )

            # Add source_id to metadata for each relation
            for rel in relations:
                if not hasattr(rel, "metadata") or rel.metadata is None:
                    rel.metadata = {}
                rel.metadata["source_id"] = article.id

            all_relations.extend(relations)

        self.logger.info(f"Extracted {len(all_relations)} relations")

        # 4. Load cross-references from Phase 03 as REFERENCES edges
        # Only include refs where both source and target are in extracted articles
        extracted_article_ids = {a.id for a in articles}
        crossref_relations = self._load_crossrefs_as_relations(
            extracted_article_ids=extracted_article_ids,
            document_id=document_id,
        )
        self.logger.info(f"Loaded {len(crossref_relations)} cross-reference edges")

        # 5. Build KG using Semantica GraphBuilder
        # First, create entity dicts and collect their IDs
        entity_dicts = [self._entity_to_dict(e) for e in all_entities]
        valid_entity_ids = {ed["id"] for ed in entity_dicts}

        # Create lookup: slug -> entity_id (for matching relation subjects/objects)
        slug_to_entity_id = {}
        for ed in entity_dicts:
            # Extract slug from entity ID (format: source_id:slug)
            parts = ed["id"].rsplit(":", 1)
            if len(parts) == 2:
                slug = parts[1]
                slug_to_entity_id[slug] = ed["id"]

        # Convert Semantica Relation objects to GraphBuilder format
        relation_dicts = []
        skipped_relations = 0
        for r in all_relations:
            # Semantica RelationExtractor returns Relation objects with subject/object as Entity objects
            source_id = r.metadata.get("source_id", "unknown") if r.metadata else "unknown"

            # Convert subject/object text to entity IDs using slug matching
            subject_slug = slugify_vietnamese(r.subject.text)
            object_slug = slugify_vietnamese(r.object.text)

            # Try to find matching entity IDs
            subject_entity_id = f"{source_id}:{subject_slug}"
            object_entity_id = f"{source_id}:{object_slug}"

            # Only include if both exist in entities
            if subject_entity_id in valid_entity_ids and object_entity_id in valid_entity_ids:
                relation_dicts.append({
                    "source": subject_entity_id,
                    "target": object_entity_id,
                    "type": r.predicate,
                    "confidence": r.confidence,
                    "metadata": {
                        "source_id": source_id,
                        "context": r.context,
                        "source_phase": "phase04_semantica_extraction",
                    },
                })
            else:
                skipped_relations += 1

        if skipped_relations > 0:
            self.logger.info(f"Skipped {skipped_relations} relations with dangling references")

        # Add cross-refs (already dicts)
        relation_dicts.extend(crossref_relations)

        # Validate ALL relations (filter self-refs, normalize types, persist new)
        # Convert relation_dicts format for validator (source/target -> subject_text/object_text)
        relations_for_validation = []
        for r in relation_dicts:
            relations_for_validation.append({
                "subject_text": r.get("source", ""),
                "predicate": r.get("type", ""),
                "object_text": r.get("target", ""),
                "confidence": r.get("confidence", 0.8),
                "metadata": r.get("metadata", {}),
            })

        validated_relations = self.relation_validator.validate(relations_for_validation)

        # Convert back to relation_dicts format
        relation_dicts = []
        for r in validated_relations:
            relation_dicts.append({
                "source": r["subject_text"],
                "target": r["object_text"],
                "type": r["predicate"],
                "confidence": r["confidence"],
                "metadata": r.get("metadata", {}),
            })

        self.logger.info(f"After validation: {len(relation_dicts)} relations")

        kg = self.builder.build(
            sources={
                "entities": entity_dicts,
                "relationships": relation_dicts,
            }
        )

        # 6. Link KG nodes back to SQLite
        self._link_kg_to_db(kg)

        self.logger.info(
            f"Pipeline complete: {len(kg.get('entities', []))} nodes, "
            f"{len(kg.get('relationships', []))} edges"
        )

        return kg

    def _load_articles(
        self,
        limit: Optional[int] = None,
        document_id: Optional[str] = None,
    ) -> List[LegalArticleModel]:
        """Load articles from database."""
        from sqlalchemy import select

        with self.db.SessionLocal() as session:
            stmt = select(LegalArticleModel)

            if document_id:
                stmt = stmt.where(LegalArticleModel.document_id == document_id)

            if limit:
                stmt = stmt.limit(limit)

            articles = session.scalars(stmt).all()

            # Detach from session
            for article in articles:
                session.expunge(article)

            return list(articles)

    def _load_crossrefs_as_relations(
        self,
        extracted_article_ids: Set[str],
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load Phase 03 cross-references as relation dicts.

        Only includes cross-refs where BOTH source and target articles
        are in the extracted set (to avoid dangling edges).

        Args:
            extracted_article_ids: Set of article IDs that were extracted
            document_id: Optional filter by document
        """
        from sqlalchemy import select

        relations = []

        with self.db.SessionLocal() as session:
            stmt = select(LegalCrossReferenceModel)

            if document_id:
                # Filter by source article's document
                stmt = stmt.join(
                    LegalArticleModel,
                    LegalCrossReferenceModel.source_article_id == LegalArticleModel.id,
                ).where(LegalArticleModel.document_id == document_id)

            crossrefs = session.scalars(stmt).all()

            for ref in crossrefs:
                # Skip if source not in extracted articles
                if ref.source_article_id not in extracted_article_ids:
                    continue

                # Skip if target not resolved or not in extracted articles
                if not ref.target_article_id:
                    continue
                if ref.target_article_id not in extracted_article_ids:
                    continue

                relations.append(
                    {
                        "source": ref.source_article_id,
                        "target": ref.target_article_id,
                        "type": ref.reference_type.upper()
                        if ref.reference_type
                        else "THAM_CHIẾU",
                        "confidence": ref.confidence or 0.8,
                        "metadata": {
                            "reference_text": ref.reference_text,
                            "resolved": True,
                            "source_phase": "phase03_crossref",
                        },
                    }
                )

        return relations

    def _entity_to_dict(self, entity) -> Dict[str, Any]:
        """Convert Entity to dict for GraphBuilder using EntityResolver."""
        source_id = entity.metadata.get("source_id", "unknown")
        document_id = entity.metadata.get("document_id", "unknown")

        # Use EntityResolver for canonical ID (handles abbreviations, dedup)
        entity_id = self.entity_resolver.resolve(
            entity_text=entity.text,
            entity_type=entity.label,
            document_id=source_id,
        )

        # Get additional metadata from resolver
        entity_meta = self.entity_resolver.get_entity_metadata(entity.text)

        return {
            "id": entity_id,
            "name": entity.text,
            "type": entity.label,
            "confidence": entity.confidence,
            "metadata": {
                "source_id": source_id,
                "document_id": document_id,
                "start_char": entity.start_char,
                "end_char": entity.end_char,
                # Entity resolution metadata
                "original_text": entity_meta["original_text"],
                "expanded_text": entity_meta["expanded_text"],
                "is_abbreviation": entity_meta["is_abbreviation"],
                "full_form": entity_meta["full_form"],
            },
        }

    def _relation_to_dict(self, relation) -> Dict[str, Any]:
        """Convert Relation to dict for GraphBuilder."""
        # Use slug format for source/target IDs (same as entity IDs)
        source_id = relation.metadata.get("source_id", "unknown")
        subject_slug = slugify_vietnamese(relation.subject.text)
        object_slug = slugify_vietnamese(relation.object.text)

        return {
            "source": f"{source_id}:{subject_slug}",
            "target": f"{source_id}:{object_slug}",
            "type": relation.predicate,
            "confidence": relation.confidence,
            "metadata": {
                "source_id": source_id,
                "context": relation.context,
                "source_phase": "phase04_extraction",
            },
        }

    def _link_kg_to_db(self, kg: Dict[str, Any]):
        """Link KG nodes back to SQLite for citation lookup."""
        linked = 0

        for entity in kg.get("entities", []):
            source_id = entity.get("metadata", {}).get("source_id")
            kg_node_id = entity.get("id")

            if source_id and kg_node_id:
                # Determine element type from source_id format
                element_type = self._detect_element_type(source_id)
                if element_type:
                    try:
                        self.db.link_to_kg(source_id, kg_node_id, element_type)
                        linked += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to link {source_id}: {e}")

        self.logger.info(f"Linked {linked} KG nodes to SQLite")

    def _detect_element_type(self, element_id: str) -> Optional[str]:
        """Detect element type from hierarchical ID format."""
        # ID format: "doc_id:dX" (article), "doc_id:dX:kY" (clause), etc.
        parts = element_id.split(":")

        if len(parts) >= 2:
            last_part = parts[-1]
            if last_part.startswith("d"):
                return "article"
            elif last_part.startswith("k"):
                return "clause"
            elif last_part.startswith("dd"):
                return "point"

        return None

    # =========================================================================
    # ONTOLOGY GENERATION
    # =========================================================================

    def generate_ontology(
        self,
        kg: Dict[str, Any],
        name: str = "VietnameseLegalOntology",
        base_uri: str = "https://semantica.dev/legal/ontology/",
    ) -> Dict[str, Any]:
        """
        Generate ontology from KG using Semantica OntologyGenerator.

        Args:
            kg: Knowledge graph from run()
            name: Ontology name
            base_uri: Base URI for ontology

        Returns:
            Ontology dict with classes, properties, hierarchy
        """
        self.logger.info("Generating ontology from KG")

        generator = OntologyGenerator(base_uri=base_uri)
        ontology = generator.generate_ontology(
            data={
                "entities": kg.get("entities", []),
                "relationships": kg.get("relationships", []),
            },
            name=name,
            build_hierarchy=True,
        )

        self.logger.info(
            f"Generated ontology: {len(ontology.get('classes', []))} classes, "
            f"{len(ontology.get('properties', []))} properties"
        )

        return ontology

    # =========================================================================
    # QUALITY ASSURANCE
    # =========================================================================

    def validate(self, kg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate KG quality using Semantica GraphValidator.

        Args:
            kg: Knowledge graph from run()

        Returns:
            Validation result dict with is_valid, issues, stats
        """
        self.logger.info("Validating KG quality")

        validator = GraphValidator()
        result = validator.validate(kg)

        # Log summary
        if result.is_valid:
            self.logger.info("KG validation passed")
        else:
            self.logger.warning(f"KG validation found {len(result.issues)} issues")

        return result.to_dict()

    # =========================================================================
    # EXPORT
    # =========================================================================

    def export(
        self,
        kg: Dict[str, Any],
        output_path: Union[str, Path],
        format: str = "json",
        **options,
    ) -> str:
        """
        Export KG to file using Semantica exporters.

        Args:
            kg: Knowledge graph from run()
            output_path: Output file path
            format: Export format (json, neo4j, rdf, csv)
            **options: Format-specific options

        Returns:
            Path to exported file

        Supported formats:
            - json: JSON/JSON-LD format
            - neo4j: Cypher queries for Neo4j (LPG)
            - rdf: RDF/Turtle format
            - csv: CSV files (entities.csv, relations.csv)
        """
        output_path = Path(output_path)
        self.logger.info(f"Exporting KG to {format}: {output_path}")

        if format == "json":
            export_json(kg, str(output_path), **options)
        elif format == "neo4j":
            export_lpg(kg, str(output_path), method="cypher", **options)
        elif format == "rdf":
            export_rdf(kg, str(output_path), format="turtle", **options)
        else:
            raise ValueError(f"Unsupported format: {format}")

        self.logger.info(f"Exported to {output_path}")
        return str(output_path)

    # =========================================================================
    # VISUALIZATION
    # =========================================================================

    def visualize(
        self,
        kg: Dict[str, Any],
        output_path: Union[str, Path],
        layout: str = "force",
        output_format: str = "html",
        **options,
    ) -> str:
        """
        Visualize KG using Semantica KGVisualizer.

        Args:
            kg: Knowledge graph from run()
            output_path: Output file path
            layout: Layout algorithm (force, hierarchical, circular)
            output_format: Output format (html, png, svg)
            **options: Visualization options

        Returns:
            Path to visualization file
        """
        output_path = Path(output_path)
        self.logger.info(f"Visualizing KG: {output_path}")

        viz = KGVisualizer(layout=layout, color_scheme="vibrant")
        fig = viz.visualize_network(kg, output="interactive")

        # Export based on format
        if output_format == "html":
            fig.write_html(str(output_path))
        elif output_format == "png":
            fig.write_image(str(output_path))
        elif output_format == "svg":
            fig.write_image(str(output_path), format="svg")
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        self.logger.info(f"Visualization saved to {output_path}")
        return str(output_path)

    def visualize_ontology(
        self,
        ontology: Dict[str, Any],
        output_path: Union[str, Path],
        output_format: str = "html",
    ) -> str:
        """
        Visualize ontology hierarchy using Semantica OntologyVisualizer.

        Args:
            ontology: Ontology from generate_ontology()
            output_path: Output file path
            output_format: Output format (html, png, svg)

        Returns:
            Path to visualization file
        """
        output_path = Path(output_path)
        self.logger.info(f"Visualizing ontology: {output_path}")

        viz = OntologyVisualizer()
        fig = viz.visualize_hierarchy(ontology, output="interactive")

        if output_format == "html":
            fig.write_html(str(output_path))
        elif output_format == "png":
            fig.write_image(str(output_path))
        else:
            fig.write_image(str(output_path), format=output_format)

        self.logger.info(f"Ontology visualization saved to {output_path}")
        return str(output_path)

    # =========================================================================
    # FULL PIPELINE WITH ALL STEPS
    # =========================================================================

    def run_full(
        self,
        output_dir: Union[str, Path],
        limit: Optional[int] = None,
        document_id: Optional[str] = None,
        export_formats: List[str] = None,
        visualize: bool = True,
    ) -> Dict[str, Any]:
        """
        Run full pipeline with ontology, export, visualization, and QA.

        Args:
            output_dir: Directory for all outputs
            limit: Limit articles (for testing)
            document_id: Filter by document
            export_formats: List of export formats (default: ["json"])
            visualize: Generate visualizations

        Returns:
            Dict with kg, ontology, validation, and output paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        export_formats = export_formats or ["json"]

        self.logger.info(f"Running full pipeline, output: {output_dir}")

        # 1. Build KG
        kg = self.run(limit=limit, document_id=document_id)

        # 2. Validate KG
        validation = self.validate(kg)

        # 3. Generate ontology
        ontology = self.generate_ontology(kg)

        # 4. Export
        export_paths = {}
        for fmt in export_formats:
            suffix = {"json": ".json", "neo4j": ".cypher", "rdf": ".ttl"}.get(fmt, f".{fmt}")
            path = self.export(kg, output_dir / f"legal_kg{suffix}", format=fmt)
            export_paths[fmt] = path

        # 5. Visualize (optional - requires plotly)
        viz_paths = {}
        if visualize:
            try:
                viz_paths["kg"] = self.visualize(kg, output_dir / "kg_network.html")
            except Exception as e:
                self.logger.warning(f"KG visualization skipped: {e}")
            try:
                viz_paths["ontology"] = self.visualize_ontology(
                    ontology, output_dir / "ontology_hierarchy.html"
                )
            except Exception as e:
                self.logger.warning(f"Ontology visualization skipped: {e}")

        self.logger.info("Full pipeline complete")

        return {
            "kg": kg,
            "ontology": ontology,
            "validation": validation,
            "exports": export_paths,
            "visualizations": viz_paths,
        }
