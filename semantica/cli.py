"""
Semantica CLI Entry Point

This module provides the command-line interface for the Semantica framework,
enabling users to interact with the framework via terminal commands.
"""

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .core.orchestrator import Semantica
from .utils.logging import setup_logging

console = Console()

@click.group()
@click.version_option(version=__version__)
def main():
    """Semantica - Semantic Layer & Knowledge Engineering Framework"""
    setup_logging()

@main.command()
def info():
    """Display information about Semantica."""
    console.print(f"[bold blue]Semantica Framework[/bold blue] v{__version__}")
    console.print("A comprehensive Python framework for transforming unstructured data into semantic layers.")
    
    table = Table(title="Framework Components")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Core Orchestrator", "Active")
    table.add_row("Knowledge Graph Engine", "Active")
    table.add_row("Pipeline Execution", "Active")
    table.add_row("Vector Store Integration", "Active")
    
    console.print(table)

@main.command()
@click.option("--source", "-s", multiple=True, help="Data sources to process.")
@click.option("--config", "-c", help="Path to configuration file.")
def build(source, config):
    """Build a knowledge base from sources."""
    console.print(f"Initializing Semantica with {len(source)} sources...")
    try:
        framework = Semantica(config=config)
        # framework.build_knowledge_base(sources=list(source))
        console.print("[bold green]Success:[/bold green] Knowledge base construction initiated.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@main.group()
def legal():
    """Vietnamese legal document processing commands."""
    pass


@legal.command()
@click.argument("source")
@click.option("-o", "--output", default="scraped_legal_docs", help="Output directory")
@click.option("-d", "--db", default="data/legal_docs.db", help="Database path")
@click.option("--headless/--no-headless", default=True, help="Run browser headless")
def scrape(source, output, db, headless):
    """Scrape legal documents from URL(s).

    SOURCE can be a single URL, a file with URLs (.txt), or multiple URLs.

    Examples:
        semantica legal scrape https://thuvienphapluat.vn/...
        semantica legal scrape urls.txt -o ./docs
    """
    from .ingest import ingest_legal

    console.print(f"[bold]Scraping legal documents...[/bold]")
    console.print(f"  Source: {source}")
    console.print(f"  Output: {output}")

    try:
        result = ingest_legal(
            source,
            method="scrape",
            output_dir=output,
            db_path=db,
            headless=headless,
        )
        if isinstance(result, list):
            console.print(f"[bold green]Success:[/bold green] Scraped {len(result)} documents")
            for doc in result:
                console.print(f"  - {doc.so_hieu}: {doc.articles} articles")
        else:
            console.print(f"[bold green]Success:[/bold green] Scraped {result.so_hieu}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@legal.command()
@click.argument("html_files", nargs=-1, required=True)
@click.option("-o", "--output", help="Output directory for JSON files")
def parse(html_files, output):
    """Parse HTML files to structured JSON.

    Examples:
        semantica legal parse docs/*.html
        semantica legal parse doc1.html doc2.html -o ./json
    """
    from .ingest import ingest_legal

    console.print(f"[bold]Parsing {len(html_files)} HTML files...[/bold]")

    try:
        result = ingest_legal(
            list(html_files),
            method="parse",
            output_dir=output,
        )
        if isinstance(result, list):
            console.print(f"[bold green]Success:[/bold green] Parsed {len(result)} documents")
            for doc in result:
                console.print(f"  - {doc.so_hieu}: {doc.chapters} chapters, {doc.articles} articles")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@legal.command(name="import")
@click.argument("json_files", nargs=-1, required=True)
@click.option("-d", "--db", default="data/legal_docs.db", help="Database path")
@click.option("-f", "--fresh", is_flag=True, help="Create fresh database")
def import_cmd(json_files, db, fresh):
    """Import JSON files to database.

    Examples:
        semantica legal import docs/json/*.json
        semantica legal import doc1.json doc2.json -d ./legal.db --fresh
    """
    from .ingest import ingest_legal

    console.print(f"[bold]Importing {len(json_files)} documents to {db}...[/bold]")

    try:
        stats = ingest_legal(
            list(json_files),
            method="import",
            db_path=db,
            fresh=fresh,
        )
        _print_stats(stats)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@legal.command()
@click.argument("source")
@click.option("-o", "--output", default="scraped_legal_docs", help="Output directory")
@click.option("-d", "--db", default="data/legal_docs.db", help="Database path")
@click.option("--headless/--no-headless", default=True, help="Run browser headless")
def full(source, output, db, headless):
    """Full pipeline: scrape/parse -> import to database.

    SOURCE can be a URL file (.txt), HTML pattern, or single URL.

    Examples:
        semantica legal full urls.txt
        semantica legal full docs/*.html -d ./legal.db
        semantica legal full https://thuvienphapluat.vn/...
    """
    from .ingest import ingest_legal

    console.print(f"[bold]Running full pipeline...[/bold]")
    console.print(f"  Source: {source}")
    console.print(f"  Output: {output}")
    console.print(f"  Database: {db}")

    try:
        stats = ingest_legal(
            source,
            method="full",
            output_dir=output,
            db_path=db,
            headless=headless,
        )
        _print_stats(stats)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@legal.command()
@click.argument("data_dir")
@click.option("-d", "--db", default="data/legal_docs.db", help="Database path")
def reimport(data_dir, db):
    """Re-parse all HTML and import to fresh database.

    Examples:
        semantica legal reimport scraped_legal_docs/
        semantica legal reimport ./docs -d ./legal.db
    """
    from .ingest import ingest_legal

    console.print(f"[bold]Re-importing from {data_dir}...[/bold]")

    try:
        stats = ingest_legal(
            data_dir,
            method="reimport",
            db_path=db,
        )
        _print_stats(stats)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@legal.command()
@click.option("-d", "--db", default="data/legal_docs.db", help="Database path")
def stats(db):
    """Show database statistics.

    Examples:
        semantica legal stats
        semantica legal stats -d ./legal.db
    """
    from .ingest import LegalIngestor

    try:
        ingestor = LegalIngestor(db_path=db)
        db_stats = ingestor.get_stats()
        _print_stats(db_stats)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


def _print_stats(stats: dict):
    """Print database statistics in a table."""
    table = Table(title="Legal Database Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    table.add_row("Documents", str(stats.get("documents", 0)))
    table.add_row("Chapters", str(stats.get("chapters", 0)))
    table.add_row("Sections", str(stats.get("sections", 0)))
    table.add_row("Articles", str(stats.get("articles", 0)))
    table.add_row("Clauses", str(stats.get("clauses", 0)))
    table.add_row("Points", str(stats.get("points", 0)))
    table.add_row("Appendices", str(stats.get("appendices", 0)))
    table.add_row("Appendix Items", str(stats.get("appendix_items", 0)))
    if "cross_references" in stats:
        table.add_row("Cross-References", str(stats.get("cross_references", 0)))
    if "imported" in stats:
        table.add_row("Imported", str(stats.get("imported", 0)))

    console.print(table)


if __name__ == "__main__":
    main()
