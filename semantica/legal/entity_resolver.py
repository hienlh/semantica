"""
Entity resolution for Vietnamese legal documents.

Handles:
- Multi-pass entity resolution (exact → abbreviation → scope-based)
- Abbreviation expansion (TNHH → Trách nhiệm hữu hạn)
- Document-scoped deduplication
- Preserves original text in metadata
"""

import re
from typing import Any, Dict, Optional, Tuple

from ..utils.logging import get_logger
from .entity_types import LEGAL_ABBREVIATIONS


class EntityResolver:
    """
    Resolve entities to canonical IDs with abbreviation handling.

    Resolution pipeline:
    1. Exact match cache (text, type, document_id)
    2. Abbreviation expansion (TNHH → full form)
    3. Scope-based dedup (same document only)

    Args:
        abbreviations: Dict of abbreviation → full form mappings
        scope_by_document: Whether to scope entity IDs by document
    """

    def __init__(
        self,
        abbreviations: Optional[Dict[str, str]] = None,
        scope_by_document: bool = True,
    ):
        self.logger = get_logger("entity_resolver")
        self.abbreviations = abbreviations or LEGAL_ABBREVIATIONS
        self.scope_by_document = scope_by_document

        # Cache: (text, type, document_id) -> entity_id
        self.cache: Dict[Tuple[str, str, str], str] = {}

        # Reverse abbreviations for quick lookup
        self._abbrev_lookup = {k.upper(): v for k, v in self.abbreviations.items()}
        self._full_to_abbrev = {v.upper(): k for k, v in self.abbreviations.items()}

        # Stats
        self.stats = {
            "cache_hits": 0,
            "abbrev_expansions": 0,
            "new_entities": 0,
        }

    def resolve(
        self,
        entity_text: str,
        entity_type: str,
        document_id: str,
    ) -> str:
        """
        Resolve entity to canonical ID.

        Args:
            entity_text: Original entity text
            entity_type: Entity type label
            document_id: Document ID for scoping

        Returns:
            Canonical entity ID
        """
        # Normalize for comparison
        norm_text = self._normalize_for_comparison(entity_text)

        # 1. Check exact cache
        cache_key = (norm_text, entity_type, document_id if self.scope_by_document else "global")
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[cache_key]

        # 2. Try abbreviation expansion and check cache
        expanded = self.expand_abbreviations(entity_text)
        if expanded != entity_text:
            norm_expanded = self._normalize_for_comparison(expanded)
            expanded_key = (norm_expanded, entity_type, document_id if self.scope_by_document else "global")
            if expanded_key in self.cache:
                # Link abbreviation to expanded form's ID
                self.stats["abbrev_expansions"] += 1
                self.cache[cache_key] = self.cache[expanded_key]
                return self.cache[expanded_key]

        # 3. Create new entity ID
        entity_id = self._create_entity_id(entity_text, document_id)
        self.cache[cache_key] = entity_id
        self.stats["new_entities"] += 1

        # Also cache expanded form if different
        if expanded != entity_text:
            norm_expanded = self._normalize_for_comparison(expanded)
            expanded_key = (norm_expanded, entity_type, document_id if self.scope_by_document else "global")
            self.cache[expanded_key] = entity_id

        return entity_id

    def expand_abbreviations(self, text: str) -> str:
        """
        Expand known abbreviations in text.

        Example: "Công ty TNHH ABC" → "Công ty Trách nhiệm hữu hạn ABC"
        """
        result = text

        for abbrev, full_form in self.abbreviations.items():
            # Replace whole word only (case-insensitive)
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            result = re.sub(pattern, full_form, result, flags=re.IGNORECASE)

        return result

    def get_abbreviation(self, text: str) -> Optional[str]:
        """
        Get abbreviation for a full form if exists.

        Example: "Trách nhiệm hữu hạn" → "TNHH"
        """
        norm = text.upper().strip()
        return self._full_to_abbrev.get(norm)

    def is_abbreviation(self, text: str) -> bool:
        """Check if text is a known abbreviation."""
        return text.upper().strip() in self._abbrev_lookup

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison (lowercase, trim, collapse whitespace)."""
        return re.sub(r"\s+", " ", text.strip().lower())

    def _create_entity_id(self, entity_text: str, document_id: str) -> str:
        """Create entity ID from text and document."""
        # Import here to avoid circular dependency
        from .kg_pipeline import slugify_vietnamese

        slug = slugify_vietnamese(entity_text)

        if self.scope_by_document:
            return f"{document_id}:{slug}"
        else:
            return slug

    def get_entity_metadata(self, entity_text: str) -> Dict[str, Any]:
        """
        Get additional metadata for entity.

        Returns:
            Dict with original_text, expanded_text, is_abbreviation, full_form
        """
        expanded = self.expand_abbreviations(entity_text)
        is_abbrev = self.is_abbreviation(entity_text)

        return {
            "original_text": entity_text,
            "expanded_text": expanded if expanded != entity_text else None,
            "is_abbreviation": is_abbrev,
            "full_form": self._abbrev_lookup.get(entity_text.upper()) if is_abbrev else None,
        }

    def clear_cache(self):
        """Clear entity cache (useful between pipeline runs)."""
        self.cache.clear()
        self.stats = {
            "cache_hits": 0,
            "abbrev_expansions": 0,
            "new_entities": 0,
        }

    def log_stats(self):
        """Log resolver statistics."""
        self.logger.info(
            f"EntityResolver stats: "
            f"cache_hits={self.stats['cache_hits']}, "
            f"abbrev_expansions={self.stats['abbrev_expansions']}, "
            f"new_entities={self.stats['new_entities']}"
        )
