#!/usr/bin/env python3
"""
Run Vietnamese Legal Pipeline - Test & Visualization Script.

Usage:
    python scripts/run_legal_pipeline.py                    # Run with defaults
    python scripts/run_legal_pipeline.py --limit 10         # Limit articles
    python scripts/run_legal_pipeline.py --full             # Full pipeline with all exports
    python scripts/run_legal_pipeline.py --export neo4j     # Export to Neo4j format
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from semantica.legal import VietnameseLegalPipeline


def main():
    parser = argparse.ArgumentParser(description="Run Vietnamese Legal KG Pipeline")
    parser.add_argument(
        "--db",
        default="data/legal_docs.db",
        help="Path to SQLite database (default: data/legal_docs.db)"
    )
    parser.add_argument(
        "--output",
        default="data/kg_output",
        help="Output directory (default: data/kg_output)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of articles to process"
    )
    parser.add_argument(
        "--document",
        default=None,
        help="Filter by document ID"
    )
    parser.add_argument(
        "--provider",
        default="openai",
        help="LLM provider (default: openai)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline with ontology, export, visualization"
    )
    parser.add_argument(
        "--export",
        nargs="+",
        default=["json"],
        choices=["json", "neo4j", "rdf"],
        help="Export formats (default: json)"
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization (useful if plotly not installed)"
    )

    args = parser.parse_args()

    # Initialize pipeline
    print(f"Initializing VietnameseLegalPipeline...")
    print(f"  Database: {args.db}")
    print(f"  Provider: {args.provider}")
    print(f"  Model: {args.model}")

    pipeline = VietnameseLegalPipeline(
        db_path=args.db,
        llm_provider=args.provider,
        llm_model=args.model,
    )

    if args.full:
        # Run full pipeline
        print(f"\nRunning full pipeline...")
        print(f"  Output: {args.output}")
        print(f"  Limit: {args.limit or 'all'}")
        print(f"  Exports: {args.export}")
        print(f"  Visualize: {not args.no_viz}")

        result = pipeline.run_full(
            output_dir=args.output,
            limit=args.limit,
            document_id=args.document,
            export_formats=args.export,
            visualize=not args.no_viz,
        )

        # Print results
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        print(f"KG Entities: {len(result['kg'].get('entities', []))}")
        print(f"KG Relationships: {len(result['kg'].get('relationships', []))}")
        print(f"Ontology Classes: {len(result['ontology'].get('classes', []))}")
        print(f"Ontology Properties: {len(result['ontology'].get('properties', []))}")
        print(f"Validation Valid: {result['validation'].get('is_valid')}")
        print(f"Validation Issues: {len(result['validation'].get('issues', []))}")
        print(f"\nExported files:")
        for fmt, path in result['exports'].items():
            print(f"  - {fmt}: {path}")
        if result['visualizations']:
            print(f"\nVisualizations:")
            for name, path in result['visualizations'].items():
                print(f"  - {name}: {path}")

    else:
        # Run basic pipeline
        print(f"\nRunning KG extraction...")
        print(f"  Limit: {args.limit or 'all'}")

        kg = pipeline.run(limit=args.limit, document_id=args.document)

        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        print(f"Entities: {len(kg.get('entities', []))}")
        print(f"Relationships: {len(kg.get('relationships', []))}")

        # Show sample entities
        entities = kg.get('entities', [])
        if entities:
            print(f"\nSample entities:")
            for e in entities[:5]:
                print(f"  - {e.get('name')} [{e.get('type')}]")

        # Show relationship types
        rel_types = {}
        for r in kg.get('relationships', []):
            t = r.get('type', 'UNKNOWN')
            rel_types[t] = rel_types.get(t, 0) + 1

        if rel_types:
            print(f"\nRelationship types:")
            for t, c in sorted(rel_types.items(), key=lambda x: -x[1])[:10]:
                print(f"  - {t}: {c}")

        # Export if requested
        if args.export and args.export != ["json"]:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"\nExporting...")
            for fmt in args.export:
                suffix = {"json": ".json", "neo4j": ".cypher", "rdf": ".ttl"}.get(fmt, f".{fmt}")
                path = pipeline.export(kg, output_dir / f"legal_kg{suffix}", format=fmt)
                print(f"  - {fmt}: {path}")


if __name__ == "__main__":
    main()
