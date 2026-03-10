"""CLI for the MCP Auto-Orchestrator."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from mcp_registry.config import get_db_path
from mcp_registry.db import RegistryDB

from mcp_orchestrator.composer import compose_team
from mcp_orchestrator.generator import (
    generate_plan_report,
    generate_claude_desktop_config,
    write_configs,
)
from mcp_orchestrator.guardrails import assess_guardrails
from mcp_orchestrator.matcher import find_matches
from mcp_orchestrator.topology import Topology


@click.group()
@click.option("--db", "db_path", default=None, help="Path to registry database")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, db_path: str | None, verbose: bool) -> None:
    """MCP Auto-Orchestrator — generate agent teams from network topologies."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path or str(get_db_path())


@cli.command()
@click.argument("topology_file", type=click.Path(exists=True))
@click.option("--min-score", default=30.0, help="Minimum combined score for matches")
@click.pass_context
def plan(ctx: click.Context, topology_file: str, min_score: float) -> None:
    """Analyze a topology and show recommended agent team."""
    topology = Topology.from_yaml(topology_file)
    click.echo(f"Topology: {topology.name}")
    click.echo(
        f"  {len(topology.devices)} devices, "
        f"{len(topology.use_cases)} use cases, "
        f"max {topology.constraints.max_agents} agents"
    )
    click.echo()

    db = RegistryDB(ctx.obj["db_path"])
    try:
        matches = find_matches(topology, db, min_score=min_score)
        click.echo(f"Found {len(matches)} matching MCP servers.")

        team = compose_team(topology, matches)
        guardrails = assess_guardrails(team, topology)
        report = generate_plan_report(team, guardrails, topology)
        click.echo()
        click.echo(report)
    finally:
        db.close()


@cli.command()
@click.argument("topology_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="./orchestrator-output",
              help="Output directory for generated configs")
@click.option("--min-score", default=30.0, help="Minimum combined score for matches")
@click.pass_context
def generate(
    ctx: click.Context,
    topology_file: str,
    output: str,
    min_score: float,
) -> None:
    """Generate config files from a topology."""
    topology = Topology.from_yaml(topology_file)
    click.echo(f"Topology: {topology.name}")

    db = RegistryDB(ctx.obj["db_path"])
    try:
        matches = find_matches(topology, db, min_score=min_score)
        click.echo(f"Found {len(matches)} matching MCP servers.")

        team = compose_team(topology, matches)
        guardrails = assess_guardrails(team, topology)

        output_dir = Path(output)
        written = write_configs(output_dir, team, guardrails, topology)

        click.echo(f"\nGenerated {len(written)} files in {output_dir}/:")
        for path in written:
            click.echo(f"  {path.relative_to(output_dir)}")
    finally:
        db.close()
