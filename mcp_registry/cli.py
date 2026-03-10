"""CLI interface for the MCP SOHO Registry."""

from __future__ import annotations

import logging
import sys

import click

from mcp_registry.config import get_db_path, get_github_token
from mcp_registry.db import RegistryDB
from mcp_registry.extractor import extract_metadata
from mcp_registry.models import MCPServer
from mcp_registry.scorer import score_maturity, score_soho_relevance
from mcp_registry.scraper import discover_repos_sync
from mcp_registry.tagger import tag_domains
from mcp_registry.vendors import detect_vendors


@click.group()
@click.option("--db", "db_path", default=None, help="Path to registry database")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, db_path: str | None, verbose: bool) -> None:
    """MCP SOHO Registry — discover and score MCP servers for your network."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path or str(get_db_path())


@cli.command()
@click.option("--skip-extract", is_flag=True, help="Skip tool extraction (metadata only)")
@click.option("--limit", default=100, help="Max repos per search query")
@click.option("--query", "queries", multiple=True, help="Custom search queries")
@click.pass_context
def update(
    ctx: click.Context,
    skip_extract: bool,
    limit: int,
    queries: tuple[str, ...],
) -> None:
    """Discover and update MCP servers from GitHub."""
    token = get_github_token()
    if not token:
        click.echo("Warning: No GitHub token found. Rate limits will be strict.", err=True)
        click.echo("Set GITHUB_TOKEN or run 'gh auth login'.", err=True)

    click.echo("Discovering MCP servers from GitHub...")
    servers = discover_repos_sync(
        token=token,
        queries=list(queries) if queries else None,
        max_per_query=limit,
    )
    click.echo(f"Found {len(servers)} unique repositories.")

    if not skip_extract:
        click.echo("Extracting tool metadata (this may take a while)...")
        with click.progressbar(servers, label="Extracting") as bar:
            for server in bar:
                extract_metadata(server)

    click.echo("Detecting vendors and tagging domains...")
    for server in servers:
        detect_vendors(server)
        tag_domains(server)
        score_maturity(server)
        score_soho_relevance(server)

    click.echo("Saving to database...")
    db = RegistryDB(ctx.obj["db_path"])
    try:
        for server in servers:
            db.upsert_server(server)
        db.rebuild_fts()
        stats = db.get_stats()
        click.echo(
            f"Done. Registry: {stats['total_servers']} servers, "
            f"{stats['unique_vendors']} vendors, {stats['unique_tags']} tags."
        )
    finally:
        db.close()


@cli.command("list")
@click.option("--domain", help="Filter by domain tag")
@click.option("--vendor", help="Filter by vendor")
@click.option("--min-maturity", type=float, default=0, help="Min maturity score")
@click.option("--min-soho", type=float, default=0, help="Min SOHO relevance score")
@click.option("--sort", "sort_by", default="soho_relevance",
              type=click.Choice(["soho_relevance", "maturity_score", "stars", "name"]))
@click.option("--limit", default=20, help="Max results")
@click.pass_context
def list_servers(
    ctx: click.Context,
    domain: str | None,
    vendor: str | None,
    min_maturity: float,
    min_soho: float,
    sort_by: str,
    limit: int,
) -> None:
    """Browse registered MCP servers with filters."""
    db = RegistryDB(ctx.obj["db_path"])
    try:
        servers = db.list_servers(
            domain=domain,
            vendor=vendor,
            min_maturity=min_maturity,
            min_soho=min_soho,
            sort_by=sort_by,
            limit=limit,
        )
        if not servers:
            click.echo("No servers found matching filters.")
            return
        _print_table(servers)
    finally:
        db.close()


@cli.command()
@click.argument("query")
@click.option("--limit", default=20, help="Max results")
@click.pass_context
def search(ctx: click.Context, query: str, limit: int) -> None:
    """Full-text search across the registry."""
    db = RegistryDB(ctx.obj["db_path"])
    try:
        servers = db.search_servers(query, limit=limit)
        if not servers:
            click.echo(f"No results for '{query}'.")
            return
        _print_table(servers)
    finally:
        db.close()


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show registry statistics."""
    db = RegistryDB(ctx.obj["db_path"])
    try:
        s = db.get_stats()
        click.echo(f"Total servers:  {s['total_servers']}")
        click.echo(f"Unique vendors: {s['unique_vendors']}")
        click.echo(f"Unique tags:    {s['unique_tags']}")
    finally:
        db.close()


def _print_table(servers: list[MCPServer]) -> None:
    """Print servers in a formatted table."""
    # Header
    click.echo(
        f"{'Name':<35} {'Stars':>5} {'Mat':>4} {'SOHO':>4} "
        f"{'Tools':>5} {'Vendors':<25} {'Tags':<20}"
    )
    click.echo("-" * 105)

    for s in servers:
        vendors = ", ".join(s.vendors[:3]) if s.vendors else "-"
        tags = ", ".join(s.domain_tags[:3]) if s.domain_tags else "-"
        name = s.full_name if len(s.full_name) <= 34 else s.full_name[:31] + "..."
        tools = str(s.tools_count) if s.tools_count >= 0 else "?"
        click.echo(
            f"{name:<35} {s.stars:>5} {s.maturity_score:>4.0f} "
            f"{s.soho_relevance:>4.0f} {tools:>5} {vendors:<25} {tags:<20}"
        )
