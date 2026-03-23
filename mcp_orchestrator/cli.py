"""CLI entry point for the MCP Auto-Orchestrator (Phase 2 stub)."""

import click


@click.group()
def cli() -> None:
    """MCP Auto-Orchestrator — topology-driven agent team planner."""


@cli.command()
@click.argument("topology", type=click.Path(exists=True))
def plan(topology: str) -> None:
    """Analyze a topology file and recommend an agent team."""
    click.echo(f"[Phase 2] Would analyze: {topology}")


@cli.command()
@click.argument("topology", type=click.Path(exists=True))
def generate(topology: str) -> None:
    """Generate Claude Desktop configs from a topology file."""
    click.echo(f"[Phase 2] Would generate configs from: {topology}")
