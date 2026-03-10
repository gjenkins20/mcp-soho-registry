"""Safety guardrails engine — determines access controls for MCP servers."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcp_orchestrator.composer import AgentAssignment, AgentTeam
from mcp_orchestrator.topology import Topology

# Keywords in server names/vendors that indicate write-capable / dangerous tools
APPROVAL_GATED_KEYWORDS = {
    "firewall": "Firewall rule changes can disrupt network connectivity",
    "credential": "Credential operations require human oversight",
    "password": "Password changes require human oversight",
    "dns": "DNS changes can break name resolution network-wide",
    "vpn": "VPN config changes can expose or isolate network segments",
    "certificate": "Certificate operations affect TLS/SSL security",
    "user": "User management changes affect access controls",
    "delete": "Destructive operations require human confirmation",
    "reboot": "System restarts cause service interruptions",
    "shutdown": "System shutdown causes service interruptions",
    "format": "Disk formatting is irreversible",
    "reset": "Reset operations may be irreversible",
}

# Keywords indicating read-only monitoring tools (safe by default)
READONLY_KEYWORDS = [
    "monitor", "status", "get", "list", "show", "view", "read",
    "check", "query", "fetch", "log", "metric", "stat", "info",
    "describe", "inspect", "report", "health", "ping", "discover",
]

# Rate limit recommendations by domain
RATE_LIMITS: dict[str, dict] = {
    "network": {"requests_per_minute": 10, "reason": "Network device APIs are often rate-limited"},
    "security": {"requests_per_minute": 5, "reason": "Security operations should be deliberate"},
    "storage": {"requests_per_minute": 15, "reason": "Storage APIs handle large payloads"},
    "compute": {"requests_per_minute": 20, "reason": "Compute operations are generally fast"},
    "media": {"requests_per_minute": 10, "reason": "Media operations can involve large transfers"},
    "iot": {"requests_per_minute": 30, "reason": "IoT sensors may need frequent polling"},
}


@dataclass
class GuardrailConfig:
    """Safety configuration for a single MCP server."""

    server_name: str
    server_full_name: str
    access_mode: str = "read-only"  # "read-only", "approval-gated", "unrestricted"
    approval_reasons: list[str] = field(default_factory=list)
    rate_limit: int = 20  # requests per minute
    rate_limit_reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class GuardrailPlan:
    """Complete guardrail plan for the agent team."""

    configs: list[GuardrailConfig] = field(default_factory=list)
    global_warnings: list[str] = field(default_factory=list)

    @property
    def approval_gated_count(self) -> int:
        return sum(1 for c in self.configs if c.access_mode == "approval-gated")

    @property
    def readonly_count(self) -> int:
        return sum(1 for c in self.configs if c.access_mode == "read-only")


def assess_guardrails(
    team: AgentTeam,
    topology: Topology,
) -> GuardrailPlan:
    """Assess safety guardrails for each MCP server in the team."""
    plan = GuardrailPlan()
    gated_types = {g.lower() for g in topology.constraints.approval_gated}

    # Collect all assignments
    all_assignments: list[tuple[str, AgentAssignment]] = []
    for agent in team.agents:
        for assignment in agent.assignments:
            all_assignments.append((agent.role, assignment))
    for assignment in team.unassigned:
        all_assignments.append(("unassigned", assignment))

    for role, assignment in all_assignments:
        config = GuardrailConfig(
            server_name=assignment.server_name,
            server_full_name=assignment.server_full_name,
        )

        corpus = assignment.server_name.lower()
        reasons_text = " ".join(assignment.match_reasons).lower()
        full_corpus = f"{corpus} {reasons_text}"

        # Check if any approval-gated keywords match
        gated_reasons: list[str] = []
        for keyword, reason in APPROVAL_GATED_KEYWORDS.items():
            if keyword in full_corpus:
                gated_reasons.append(f"{keyword}: {reason}")

        # Check if topology constraints gate this type
        for gated_type in gated_types:
            if gated_type in full_corpus or gated_type in role:
                gated_reasons.append(
                    f"Topology constraint: '{gated_type}' operations require approval"
                )

        # Determine access mode
        is_likely_readonly = any(kw in corpus for kw in READONLY_KEYWORDS)

        if gated_reasons:
            config.access_mode = "approval-gated"
            config.approval_reasons = gated_reasons
        elif is_likely_readonly:
            config.access_mode = "read-only"
        else:
            # Default to read-only for safety
            config.access_mode = "read-only"
            config.warnings.append(
                "Defaulting to read-only. Review tool capabilities and "
                "change to 'unrestricted' if write operations are needed."
            )

        # Determine rate limit from domain
        for match_reason in assignment.match_reasons:
            if match_reason.startswith("domain:"):
                domain = match_reason.split(":")[1]
                if domain in RATE_LIMITS:
                    rl = RATE_LIMITS[domain]
                    config.rate_limit = rl["requests_per_minute"]
                    config.rate_limit_reason = rl["reason"]
                    break

        plan.configs.append(config)

    # Global warnings
    if not topology.constraints.approval_gated:
        plan.global_warnings.append(
            "No approval gates defined in topology constraints. "
            "Consider adding 'approval_gated: [firewall, credentials]' for safety."
        )

    if any(c.access_mode == "unrestricted" for c in plan.configs):
        plan.global_warnings.append(
            "Some MCP servers have unrestricted access. "
            "Review carefully before deploying."
        )

    return plan
