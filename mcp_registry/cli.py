"""CLI entry point for the MCP Registry Curator."""

import asyncio
import json
import os

import click
from rich.console import Console
from rich.table import Table

from . import db, scoring, scraper

console = Console()


@click.group()
@click.option(
    "--db-path",
    envvar="MCP_REGISTRY_DB",
    default=str(db.DEFAULT_DB_PATH),
    help="Path to the SQLite registry database.",
)
@click.pass_context
def cli(ctx: click.Context, db_path: str) -> None:
    """MCP SOHO Registry — discover, catalog, and score MCP servers."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


@cli.command()
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub API token.")
@click.pass_context
def update(ctx: click.Context, token: str | None) -> None:
    """Scrape GitHub and refresh the registry."""
    db_path = ctx.obj["db_path"]
    conn = db.get_connection(db_path)

    console.print("[bold]Searching GitHub for MCP servers...[/bold]")
    repos = asyncio.run(scraper.search_github(token=token))
    console.print(f"Found [green]{len(repos)}[/green] repositories.")

    for repo in repos:
        text = f"{repo['name']} {repo['description']}"
        vendors = scoring.detect_vendors(text)
        domains = scoring.detect_domains(text)
        maturity = scoring.compute_maturity_score(
            stars=repo["stars"],
            last_commit=repo["last_commit"],
            has_docs=repo["has_docs"],
            license_id=repo["license"],
        )
        soho = scoring.compute_soho_relevance(vendors, domains, repo["description"])

        repo.update(
            vendors=vendors,
            domain_tags=domains,
            maturity_score=maturity,
            soho_relevance=soho,
        )
        db.upsert_server(conn, repo)

    conn.close()
    console.print(f"[bold green]Registry updated — {len(repos)} servers processed.[/bold green]")


@cli.command("list")
@click.option("--vendor", default=None, help="Filter by vendor name.")
@click.option("--domain", default=None, help="Filter by domain tag.")
@click.option("--min-maturity", default=0, type=float, help="Minimum maturity score.")
@click.option("--min-soho", default=0, type=float, help="Minimum SOHO relevance.")
@click.option("--limit", default=20, type=int, help="Max results.")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_servers(
    ctx: click.Context,
    vendor: str | None,
    domain: str | None,
    min_maturity: float,
    min_soho: float,
    limit: int,
    as_json: bool,
) -> None:
    """List registered MCP servers with optional filters."""
    conn = db.get_connection(ctx.obj["db_path"])
    rows = db.search_servers(
        conn, vendor=vendor, domain=domain,
        min_maturity=min_maturity, min_soho=min_soho, limit=limit,
    )
    conn.close()

    if as_json:
        click.echo(json.dumps([dict(r) for r in rows], indent=2))
        return

    if not rows:
        console.print("[yellow]No servers found matching filters.[/yellow]")
        return

    table = Table(title="MCP Server Registry")
    table.add_column("Name", style="cyan")
    table.add_column("Stars", justify="right")
    table.add_column("Maturity", justify="right")
    table.add_column("SOHO", justify="right")
    table.add_column("Vendors")
    table.add_column("Domains")

    for row in rows:
        table.add_row(
            row["full_name"],
            str(row["stars"]),
            f"{row['maturity_score']:.0f}",
            f"{row['soho_relevance']:.0f}",
            row["vendors"],
            row["domain_tags"],
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--limit", default=20, type=int)
@click.pass_context
def search(ctx: click.Context, query: str, limit: int) -> None:
    """Full-text search across registry entries."""
    conn = db.get_connection(ctx.obj["db_path"])
    rows = db.search_servers(conn, query=query, limit=limit)
    conn.close()

    if not rows:
        console.print(f"[yellow]No results for '{query}'.[/yellow]")
        return

    table = Table(title=f"Search: {query}")
    table.add_column("Name", style="cyan")
    table.add_column("Description", max_width=50)
    table.add_column("Stars", justify="right")
    table.add_column("SOHO", justify="right")

    for row in rows:
        table.add_row(
            row["full_name"],
            row["description"][:50],
            str(row["stars"]),
            f"{row['soho_relevance']:.0f}",
        )

    console.print(table)
