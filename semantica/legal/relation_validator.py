"""
Relation validation for Vietnamese legal KG pipeline.

Implements post-processing validation pipeline:
1. Self-reference filter (subject != object)
2. Type normalization (UPPERCASE)
3. Auto-persist new relation types to JSON config
4. Semantic type validation (soft warning)
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..utils.logging import get_logger


# Semantic type rules for soft validation
# Subject/Object entity types that are compatible with each relation type
SEMANTIC_TYPE_RULES = {
    "CÓ_QUYỀN": {
        "subject_types": ["ORGANIZATION", "PERSON_ROLE"],
        "object_types": ["ACTION", "LEGAL_TERM"],
    },
    "CÓ_NGHĨA_VỤ": {
        "subject_types": ["ORGANIZATION", "PERSON_ROLE"],
        "object_types": ["ACTION", "LEGAL_TERM"],
    },
    "ĐỊNH_NGHĨA_LÀ": {
        "subject_types": ["ORGANIZATION", "LEGAL_TERM", "PERSON_ROLE"],
        "object_types": ["LEGAL_TERM", "ORGANIZATION"],
    },
    "VI_PHẠM": {
        "subject_types": ["ACTION", "ORGANIZATION", "PERSON_ROLE"],
        "object_types": ["LEGAL_TERM", "ACTION"],
    },
    "CHỊU_TRÁCH_NHIỆM": {
        "subject_types": ["ORGANIZATION", "PERSON_ROLE"],
        "object_types": ["ACTION", "LEGAL_TERM"],
    },
    "NGHIÊM_CẤM": {
        "subject_types": ["ORGANIZATION", "PERSON_ROLE"],
        "object_types": ["ACTION"],
    },
    "YÊU_CẦU": {
        "subject_types": ["ORGANIZATION", "PERSON_ROLE", "LEGAL_TERM"],
        "object_types": ["LEGAL_TERM", "ACTION", "ORGANIZATION", "MONETARY", "DURATION"],
    },
    "BAO_GỒM": {
        "subject_types": ["ORGANIZATION", "LEGAL_TERM"],
        "object_types": ["ORGANIZATION", "LEGAL_TERM", "ACTION"],
    },
    "THAM_CHIẾU": {
        "subject_types": ["LEGAL_TERM"],
        "object_types": ["LEGAL_TERM"],
    },
}

# Default path for discovered relation types
DEFAULT_DISCOVERED_TYPES_PATH = Path("data/discovered_relation_types.json")


class RelationValidator:
    """
    Post-processing validator for extracted relations.

    Validation pipeline:
    1. Filter self-references (subject != object)
    2. Normalize types to UPPERCASE
    3. Auto-persist new types to JSON config
    4. Semantic type check (soft validation - warn, don't reject)
    """

    def __init__(
        self,
        defined_types: List[str],
        discovered_types_path: Optional[Path] = None,
        enable_semantic_validation: bool = True,
    ):
        """
        Initialize validator.

        Args:
            defined_types: List of predefined relation types
            discovered_types_path: Path to JSON file for discovered types
            enable_semantic_validation: Enable semantic type checking (soft)
        """
        self.logger = get_logger("relation_validator")
        self.defined_types = set(t.upper() for t in defined_types)
        self.discovered_types_path = discovered_types_path or DEFAULT_DISCOVERED_TYPES_PATH
        self.enable_semantic_validation = enable_semantic_validation

        # Load previously discovered types
        self.discovered_types = self._load_discovered_types()

        # Stats for reporting
        self.stats = {
            "total_input": 0,
            "self_references_filtered": 0,
            "types_normalized": 0,
            "new_types_discovered": 0,
            "semantic_warnings": 0,
            "total_output": 0,
        }

    def _load_discovered_types(self) -> Set[str]:
        """Load previously discovered relation types from JSON."""
        if not self.discovered_types_path.exists():
            return set()

        try:
            with open(self.discovered_types_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("relation_types", []))
        except Exception as e:
            self.logger.warning(f"Failed to load discovered types: {e}")
            return set()

    def _save_discovered_types(self):
        """Save discovered relation types to JSON."""
        try:
            # Ensure directory exists
            self.discovered_types_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.discovered_types_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "relation_types": sorted(list(self.discovered_types)),
                        "count": len(self.discovered_types),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            self.logger.info(f"Saved {len(self.discovered_types)} discovered types")
        except Exception as e:
            self.logger.error(f"Failed to save discovered types: {e}")

    def validate(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run full validation pipeline.

        Args:
            relations: List of relation dicts with subject_text, predicate, object_text

        Returns:
            Validated relations list
        """
        self.stats["total_input"] = len(relations)

        # Step 1: Filter self-references
        relations = self.filter_self_references(relations)

        # Step 2: Normalize types to UPPERCASE
        relations = self.normalize_types(relations)

        # Step 3: Persist new types (instead of rejecting)
        relations = self.persist_new_types(relations)

        # Step 4: Semantic type validation (soft - warn only)
        if self.enable_semantic_validation:
            self.check_semantic_types(relations)

        self.stats["total_output"] = len(relations)
        self._log_stats()

        return relations

    def filter_self_references(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove relations where subject == object.

        Comparison is case-insensitive and whitespace-normalized.
        """
        valid = []
        for r in relations:
            subj = self._normalize_text(r.get("subject_text", ""))
            obj = self._normalize_text(r.get("object_text", ""))

            if subj != obj:
                valid.append(r)
            else:
                self.stats["self_references_filtered"] += 1
                self.logger.debug(
                    f"Filtered self-reference: {subj} -> {r.get('predicate')} -> {obj}"
                )

        return valid

    def normalize_types(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize all predicate types to UPPERCASE.

        Also replaces spaces with underscores.
        """
        for r in relations:
            predicate = r.get("predicate", "")
            original = predicate

            # Normalize: spaces -> underscores, uppercase
            normalized = predicate.upper().replace(" ", "_")
            # Remove multiple underscores
            normalized = re.sub(r"_+", "_", normalized).strip("_")

            if normalized != original:
                self.stats["types_normalized"] += 1
                self.logger.debug(f"Normalized type: {original} -> {normalized}")

            r["predicate"] = normalized

        return relations

    def persist_new_types(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Auto-persist new relation types to JSON config.

        Instead of rejecting undefined types, save them for future use.
        """
        new_types = set()

        for r in relations:
            pred = r.get("predicate", "").upper()

            # Check if it's a new type
            if pred not in self.defined_types and pred not in self.discovered_types:
                new_types.add(pred)
                self.discovered_types.add(pred)
                self.stats["new_types_discovered"] += 1
                self.logger.info(f"Discovered new relation type: {pred}")

        # Save if new types were discovered
        if new_types:
            self._save_discovered_types()

        return relations

    def check_semantic_types(self, relations: List[Dict[str, Any]]):
        """
        Soft validation for semantic type compatibility.

        Logs warnings but does not reject relations.
        This helps identify potential extraction errors for review.
        """
        for r in relations:
            pred = r.get("predicate", "").upper()

            if pred not in SEMANTIC_TYPE_RULES:
                continue  # No rules defined for this type

            rules = SEMANTIC_TYPE_RULES[pred]

            # Check subject type compatibility
            subject_type = r.get("subject_type", "")
            if subject_type and subject_type not in rules.get("subject_types", []):
                self.stats["semantic_warnings"] += 1
                self.logger.debug(
                    f"Semantic warning: {pred} expects subject types "
                    f"{rules['subject_types']}, got {subject_type}"
                )

            # Check object type compatibility
            object_type = r.get("object_type", "")
            if object_type and object_type not in rules.get("object_types", []):
                self.stats["semantic_warnings"] += 1
                self.logger.debug(
                    f"Semantic warning: {pred} expects object types "
                    f"{rules['object_types']}, got {object_type}"
                )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, trim, collapse whitespace)."""
        return re.sub(r"\s+", " ", text.strip().lower())

    def _log_stats(self):
        """Log validation statistics."""
        self.logger.info(
            f"Validation stats: "
            f"input={self.stats['total_input']}, "
            f"output={self.stats['total_output']}, "
            f"self_refs_filtered={self.stats['self_references_filtered']}, "
            f"types_normalized={self.stats['types_normalized']}, "
            f"new_types={self.stats['new_types_discovered']}"
        )

    def get_all_relation_types(self) -> Set[str]:
        """Get all known relation types (defined + discovered)."""
        return self.defined_types | self.discovered_types

    def reset_stats(self):
        """Reset validation statistics."""
        self.stats = {
            "total_input": 0,
            "self_references_filtered": 0,
            "types_normalized": 0,
            "new_types_discovered": 0,
            "semantic_warnings": 0,
            "total_output": 0,
        }
