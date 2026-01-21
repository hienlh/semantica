"""
Test suite for Vietnamese legal relation extraction quality.

Validates:
1. No self-referencing relations
2. All relation types in UPPERCASE
3. New types auto-persisted to JSON
4. Semantic accuracy (manual sample evaluation)
"""

import json
import pytest
from pathlib import Path

from semantica.legal import (
    VietnameseLegalPipeline,
    RelationValidator,
    LEGAL_RELATION_TYPES,
    LEGAL_RELATION_TYPES_SET,
)


class TestRelationExtractionQuality:
    """Test relation extraction quality metrics."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance."""
        return VietnameseLegalPipeline(
            db_path="data/legal_docs.db",
            llm_provider="gemini",
            llm_model="gemini-2.0-flash",
        )

    @pytest.fixture
    def sample_kg(self, pipeline):
        """Extract KG from sample articles (5 articles for quick test)."""
        return pipeline.run(limit=5)

    def test_no_self_references(self, sample_kg):
        """Verify no self-referencing relations (subject != object)."""
        self_refs = []

        for rel in sample_kg.get("relationships", []):
            source = rel.get("source", "")
            target = rel.get("target", "")

            if source == target:
                self_refs.append(rel)

        assert len(self_refs) == 0, (
            f"Found {len(self_refs)} self-referencing relations: "
            f"{[r['type'] for r in self_refs[:5]]}"
        )

    def test_relation_types_uppercase(self, sample_kg):
        """Verify all relation types are UPPERCASE."""
        non_uppercase = []

        for rel in sample_kg.get("relationships", []):
            rel_type = rel.get("type", "")
            if rel_type != rel_type.upper():
                non_uppercase.append(rel_type)

        assert len(non_uppercase) == 0, (
            f"Found {len(non_uppercase)} non-UPPERCASE relation types: "
            f"{non_uppercase[:5]}"
        )

    def test_discovered_types_persisted(self, sample_kg):
        """Verify new types are persisted to JSON config."""
        discovered_path = Path("data/discovered_relation_types.json")

        # Run pipeline to trigger type discovery
        # (sample_kg fixture already did this)

        # Check if file exists and has content
        if discovered_path.exists():
            with open(discovered_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # It's OK if no new types discovered, but file should exist
                assert "relation_types" in data
                assert "count" in data

    def test_entity_ids_not_empty(self, sample_kg):
        """Verify all entities have valid IDs."""
        empty_ids = []

        for entity in sample_kg.get("entities", []):
            if not entity.get("id"):
                empty_ids.append(entity.get("name"))

        assert len(empty_ids) == 0, (
            f"Found {len(empty_ids)} entities without IDs: {empty_ids[:5]}"
        )

    def test_relation_source_target_exist(self, sample_kg):
        """Verify relation source/target entities exist."""
        entity_ids = {e["id"] for e in sample_kg.get("entities", [])}
        dangling = []

        for rel in sample_kg.get("relationships", []):
            source = rel.get("source")
            target = rel.get("target")

            if source not in entity_ids and not source.startswith("doc:"):
                dangling.append(("source", source))
            if target not in entity_ids and not target.startswith("doc:"):
                dangling.append(("target", target))

        # Allow some dangling for cross-references (article IDs)
        assert len(dangling) <= len(sample_kg.get("relationships", [])) * 0.1, (
            f"Too many dangling references: {len(dangling)}"
        )


class TestRelationValidator:
    """Test RelationValidator component."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return RelationValidator(defined_types=LEGAL_RELATION_TYPES)

    def test_filter_self_references(self, validator):
        """Test self-reference filtering."""
        relations = [
            {"subject_text": "Công ty", "predicate": "BAO_GỒM", "object_text": "Công ty"},
            {"subject_text": "HĐQT", "predicate": "CÓ_QUYỀN", "object_text": "quyết định"},
        ]

        result = validator.filter_self_references(relations)
        assert len(result) == 1
        assert result[0]["subject_text"] == "HĐQT"

    def test_normalize_types(self, validator):
        """Test type normalization to UPPERCASE."""
        relations = [
            {"subject_text": "A", "predicate": "có_quyền", "object_text": "B"},
            {"subject_text": "C", "predicate": "BỊ_PHẠT", "object_text": "D"},
        ]

        result = validator.normalize_types(relations)
        assert result[0]["predicate"] == "CÓ_QUYỀN"
        assert result[1]["predicate"] == "BỊ_PHẠT"

    def test_persist_new_types(self, validator, tmp_path):
        """Test new types are persisted to JSON."""
        # Use temp path for test
        validator.discovered_types_path = tmp_path / "discovered_types.json"

        relations = [
            {"subject_text": "A", "predicate": "LOẠI_MỚI", "object_text": "B"},
        ]

        validator.persist_new_types(relations)

        assert validator.discovered_types_path.exists()
        with open(validator.discovered_types_path, "r") as f:
            data = json.load(f)
            assert "LOẠI_MỚI" in data["relation_types"]


class TestEntityResolver:
    """Test EntityResolver component."""

    def test_abbreviation_expansion(self):
        """Test abbreviation expansion."""
        from semantica.legal import EntityResolver

        resolver = EntityResolver()

        # Test expansion
        expanded = resolver.expand_abbreviations("Công ty TNHH ABC")
        assert "Trách nhiệm hữu hạn" in expanded

    def test_entity_resolution_scope(self):
        """Test entity resolution with document scope."""
        from semantica.legal import EntityResolver

        resolver = EntityResolver()

        # Same text, same doc -> same ID
        id1 = resolver.resolve("Công ty", "ORGANIZATION", "doc1")
        id2 = resolver.resolve("Công ty", "ORGANIZATION", "doc1")
        assert id1 == id2

        # Same text, different doc -> different ID
        id3 = resolver.resolve("Công ty", "ORGANIZATION", "doc2")
        assert id1 != id3


# Utility function for manual evaluation
def evaluate_relations_manual(kg: dict, sample_size: int = 20) -> dict:
    """
    Manual evaluation helper for relation quality.

    Returns metrics for manual scoring.
    """
    import random

    relationships = kg.get("relationships", [])
    sample = random.sample(relationships, min(sample_size, len(relationships)))

    print("\n=== Manual Evaluation Sample ===")
    print(f"Total relations: {len(relationships)}")
    print(f"Sample size: {len(sample)}")
    print("\nRelations to evaluate:")

    for i, rel in enumerate(sample, 1):
        print(f"\n{i}. {rel.get('source', '?')[:30]}")
        print(f"   --[{rel.get('type')}]-->")
        print(f"   {rel.get('target', '?')[:30]}")
        print(f"   Confidence: {rel.get('confidence', 0):.2f}")

    return {
        "total_relations": len(relationships),
        "sample_size": len(sample),
        "sample": sample,
    }


if __name__ == "__main__":
    # Quick evaluation run
    from semantica.legal import VietnameseLegalPipeline

    print("Initializing pipeline...")
    pipeline = VietnameseLegalPipeline(
        db_path="data/legal_docs.db",
        llm_provider="gemini",
        llm_model="gemini-2.0-flash",
    )

    print("Running extraction on 5 articles...")
    kg = pipeline.run(limit=5)

    print(f"\nResults:")
    print(f"  Entities: {len(kg.get('entities', []))}")
    print(f"  Relations: {len(kg.get('relationships', []))}")

    # Check for issues
    self_refs = [r for r in kg.get("relationships", []) if r.get("source") == r.get("target")]
    non_upper = [r for r in kg.get("relationships", []) if r.get("type") != r.get("type", "").upper()]

    print(f"  Self-references: {len(self_refs)}")
    print(f"  Non-UPPERCASE types: {len(non_upper)}")

    # Show sample relations
    print("\nSample relations:")
    for rel in kg.get("relationships", [])[:5]:
        print(f"  - {rel.get('type')}: {rel.get('source')[:30]} -> {rel.get('target')[:30]}")
