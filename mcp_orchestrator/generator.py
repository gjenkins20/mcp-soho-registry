"""Config generator — outputs Claude Desktop config and agent system prompts."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mcp_orchestrator.composer import AgentTeam
from mcp_orchestrator.guardrails import GuardrailPlan
from mcp_orchestrator.topology import Topology

# Default templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def generate_claude_desktop_config(
    team: AgentTeam,
    guardrails: GuardrailPlan,
) -> dict:
    """Generate a claude_desktop_config.json structure.

    Since we don't know the exact install commands for discovered servers,
    we generate a skeleton config with placeholders and comments.
    """
    mcp_servers: dict = {}
    guardrail_lookup = {g.server_full_name: g for g in guardrails.configs}

    for agent in team.agents:
        for assignment in agent.assignments:
            server_key = assignment.server_name.replace("-", "_")
            guard = guardrail_lookup.get(assignment.server_full_name)

            config: dict = {
                "_comment": f"Agent role: {agent.role} | Source: {assignment.server_url}",
                "command": "uvx",
                "args": [assignment.server_name],
            }

            if guard:
                config["_access_mode"] = guard.access_mode
                if guard.access_mode == "approval-gated":
                    config["_approval_reasons"] = guard.approval_reasons
                if guard.rate_limit:
                    config["_rate_limit_rpm"] = guard.rate_limit

            mcp_servers[server_key] = config

    return {"mcpServers": mcp_servers}


def generate_agent_prompts(
    team: AgentTeam,
    topology: Topology,
    guardrails: GuardrailPlan,
) -> dict[str, str]:
    """Generate system prompts for each agent role."""
    prompts: dict[str, str] = {}
    guardrail_lookup = {g.server_full_name: g for g in guardrails.configs}

    for agent in team.active_agents:
        lines = [
            f"# {agent.role.replace('-', ' ').title()}",
            "",
            f"**Role:** {agent.description}",
            f"**Network:** {topology.name}",
            "",
            "## Available MCP Servers",
            "",
        ]

        for assignment in agent.assignments:
            guard = guardrail_lookup.get(assignment.server_full_name)
            access = guard.access_mode if guard else "read-only"
            lines.append(f"- **{assignment.server_name}** ({access})")
            lines.append(f"  Source: {assignment.server_url}")
            if guard and guard.approval_reasons:
                lines.append(f"  ⚠ Approval required: {'; '.join(guard.approval_reasons)}")
            lines.append("")

        # Safety instructions
        lines.extend([
            "## Safety Guidelines",
            "",
        ])

        gated_servers = [
            a for a in agent.assignments
            if guardrail_lookup.get(a.server_full_name, None)
            and guardrail_lookup[a.server_full_name].access_mode == "approval-gated"
        ]

        if gated_servers:
            lines.append("**Approval-gated operations:**")
            for a in gated_servers:
                guard = guardrail_lookup[a.server_full_name]
                for reason in guard.approval_reasons:
                    lines.append(f"- {a.server_name}: {reason}")
            lines.append("")

        lines.extend([
            "- Always prefer read-only operations (get, list, show, status) before write operations",
            "- Never make changes to production infrastructure without explicit user approval",
            "- Report anomalies and let the user decide on remediation actions",
            "",
        ])

        if topology.constraints.approval_gated:
            lines.append(
                f"**Topology constraints:** The following categories require "
                f"human approval: {', '.join(topology.constraints.approval_gated)}"
            )
            lines.append("")

        prompts[agent.role] = "\n".join(lines)

    return prompts


def generate_plan_report(
    team: AgentTeam,
    guardrails: GuardrailPlan,
    topology: Topology,
) -> str:
    """Generate a human-readable plan report."""
    lines = [
        f"# Agent Team Plan: {team.topology_name}",
        "",
        f"**Devices:** {len(topology.devices)} | "
        f"**Use cases:** {len(topology.use_cases)} | "
        f"**Max agents:** {topology.constraints.max_agents}",
        "",
    ]

    # Agent summary
    lines.append(f"## Agent Roles ({len(team.active_agents)} active)")
    lines.append("")

    for agent in team.active_agents:
        lines.append(f"### {agent.role.replace('-', ' ').title()}")
        lines.append(f"*{agent.description}*")
        lines.append("")
        for a in agent.assignments:
            guard_lookup = {g.server_full_name: g for g in guardrails.configs}
            guard = guard_lookup.get(a.server_full_name)
            access = f" [{guard.access_mode}]" if guard else ""
            score = f" (score: {a.combined_score:.0f})"
            lines.append(f"- **{a.server_name}**{access}{score}")
            lines.append(f"  {a.server_url}")
            if a.match_reasons:
                lines.append(f"  Matched: {', '.join(a.match_reasons)}")
        lines.append("")

    # Unassigned servers
    if team.unassigned:
        lines.append(f"## Unassigned Servers ({len(team.unassigned)})")
        lines.append("")
        for a in team.unassigned:
            lines.append(f"- {a.server_name} (score: {a.combined_score:.0f})")
            lines.append(f"  {a.server_url}")
        lines.append("")

    # Gaps
    if team.gaps:
        lines.append("## Coverage Gaps")
        lines.append("")
        for gap in team.gaps:
            lines.append(f"- {gap}")
        lines.append("")

    # Guardrails summary
    lines.append("## Safety Guardrails")
    lines.append("")
    lines.append(
        f"- **Read-only:** {guardrails.readonly_count} servers"
    )
    lines.append(
        f"- **Approval-gated:** {guardrails.approval_gated_count} servers"
    )
    lines.append("")

    if guardrails.global_warnings:
        lines.append("### Warnings")
        lines.append("")
        for w in guardrails.global_warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def write_configs(
    output_dir: Path,
    team: AgentTeam,
    guardrails: GuardrailPlan,
    topology: Topology,
) -> list[Path]:
    """Write all config files to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # 1. Claude Desktop config
    config = generate_claude_desktop_config(team, guardrails)
    config_path = output_dir / "claude_desktop_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    written.append(config_path)

    # 2. Agent system prompts
    prompts = generate_agent_prompts(team, topology, guardrails)
    prompts_dir = output_dir / "agent_prompts"
    prompts_dir.mkdir(exist_ok=True)
    for role, prompt in prompts.items():
        prompt_path = prompts_dir / f"{role}.md"
        prompt_path.write_text(prompt)
        written.append(prompt_path)

    # 3. Plan report
    report = generate_plan_report(team, guardrails, topology)
    report_path = output_dir / "plan_report.md"
    report_path.write_text(report)
    written.append(report_path)

    return written
