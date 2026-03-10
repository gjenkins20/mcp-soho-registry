"""Agent team composer — groups MCP servers into agent roles."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcp_orchestrator.matcher import Match
from mcp_orchestrator.topology import Topology

# Agent role definitions with their domain affinities
AGENT_ROLES: dict[str, dict] = {
    "network-engineer": {
        "description": "Monitors and manages network infrastructure",
        "domains": ["network"],
        "device_types": ["firewall", "router", "switch", "access-point"],
        "vendors": ["fortinet", "ubiquiti", "pfsense", "opnsense", "tp-link", "mikrotik", "netgear"],
    },
    "security-ops": {
        "description": "Monitors security events and manages access controls",
        "domains": ["security"],
        "device_types": ["firewall", "camera"],
        "vendors": ["fortinet", "pfsense", "opnsense", "reolink", "hikvision", "frigate"],
    },
    "systems-engineer": {
        "description": "Manages compute infrastructure and containers",
        "domains": ["compute"],
        "device_types": ["server"],
        "vendors": ["docker", "proxmox", "portainer", "raspberry-pi", "ansible", "webmin", "cockpit"],
    },
    "storage-admin": {
        "description": "Manages storage, backups, and file shares",
        "domains": ["storage"],
        "device_types": ["nas"],
        "vendors": ["synology", "qnap", "buffalo", "truenas"],
    },
    "media-manager": {
        "description": "Manages media servers and photo libraries",
        "domains": ["media"],
        "device_types": ["media-server"],
        "vendors": ["plex", "jellyfin", "immich"],
    },
    "iot-coordinator": {
        "description": "Manages IoT devices and home automation",
        "domains": ["iot"],
        "device_types": ["sensor"],
        "vendors": ["home-assistant", "mqtt"],
    },
}


@dataclass
class AgentAssignment:
    """An MCP server assigned to an agent role."""

    server_full_name: str
    server_name: str
    server_url: str
    match_reasons: list[str]
    combined_score: float


@dataclass
class AgentRole:
    """A composed agent with its assigned MCP servers."""

    role: str
    description: str
    assignments: list[AgentAssignment] = field(default_factory=list)

    @property
    def server_count(self) -> int:
        return len(self.assignments)


@dataclass
class AgentTeam:
    """The complete agent team recommendation."""

    topology_name: str
    agents: list[AgentRole] = field(default_factory=list)
    unassigned: list[AgentAssignment] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def total_servers(self) -> int:
        return sum(a.server_count for a in self.agents) + len(self.unassigned)

    @property
    def active_agents(self) -> list[AgentRole]:
        return [a for a in self.agents if a.assignments]


def _match_to_assignment(match: Match) -> AgentAssignment:
    return AgentAssignment(
        server_full_name=match.server.full_name,
        server_name=match.server.name,
        server_url=match.server.url,
        match_reasons=match.match_reasons,
        combined_score=match.combined_score,
    )


def _score_role_fit(match: Match, role_def: dict) -> float:
    """Score how well a match fits a given agent role (0-100)."""
    score = 0.0

    # Domain overlap
    server_domains = set(match.server.domain_tags)
    role_domains = set(role_def["domains"])
    if server_domains & role_domains:
        score += 40

    # Vendor overlap
    server_vendors = set(match.server.vendors)
    role_vendors = set(role_def["vendors"])
    if server_vendors & role_vendors:
        score += 35

    # Match reason alignment
    for reason in match.match_reasons:
        if reason.startswith("domain:"):
            domain = reason.split(":")[1]
            if domain in role_def["domains"]:
                score += 10
                break
        elif reason.startswith("vendor:"):
            vendor = reason.split(":")[1]
            if vendor in role_def["vendors"]:
                score += 10
                break

    # Original combined score as tiebreaker
    score += match.combined_score * 0.15

    return min(score, 100)


def compose_team(
    topology: Topology,
    matches: list[Match],
) -> AgentTeam:
    """Group matched MCP servers into agent roles.

    Each server is assigned to its best-fitting role. Roles without
    assignments are omitted. Servers that don't fit any role go to unassigned.
    """
    team = AgentTeam(topology_name=topology.name)

    # Initialize all roles
    roles: dict[str, AgentRole] = {}
    for role_name, role_def in AGENT_ROLES.items():
        roles[role_name] = AgentRole(
            role=role_name,
            description=role_def["description"],
        )

    # Assign each match to its best-fitting role
    assigned_servers: set[str] = set()
    max_per_agent = max(
        1,
        topology.constraints.max_agents * 2,  # allow some flexibility
    )

    for match in matches:
        best_role: str | None = None
        best_score = 0.0

        for role_name, role_def in AGENT_ROLES.items():
            fit = _score_role_fit(match, role_def)
            if fit > best_score and len(roles[role_name].assignments) < max_per_agent:
                best_score = fit
                best_role = role_name

        assignment = _match_to_assignment(match)
        if best_role and best_score >= 20:
            roles[best_role].assignments.append(assignment)
        else:
            team.unassigned.append(assignment)
        assigned_servers.add(match.server.full_name)

    # Only include roles that have assignments
    team.agents = [r for r in roles.values() if r.assignments]

    # Detect gaps — topology needs without matching servers
    needed_vendors = topology.all_vendors
    matched_vendors: set[str] = set()
    for match in matches:
        matched_vendors.update(v.lower() for v in match.server.vendors)

    for vendor in needed_vendors:
        if vendor not in matched_vendors:
            team.gaps.append(
                f"No MCP server found for vendor '{vendor}'. "
                f"Consider building or requesting one."
            )

    needed_use_cases = set(topology.use_cases)
    # Rough check: if use case domains aren't covered
    from mcp_orchestrator.matcher import USE_CASE_TO_DOMAINS
    covered_domains: set[str] = set()
    for match in matches:
        covered_domains.update(match.server.domain_tags)

    for uc in needed_use_cases:
        uc_domains = USE_CASE_TO_DOMAINS.get(uc, [])
        if uc_domains and not any(d in covered_domains for d in uc_domains):
            team.gaps.append(
                f"Use case '{uc}' may not be fully covered. "
                f"Needs domains: {', '.join(uc_domains)}"
            )

    # Trim to max_agents constraint
    if len(team.active_agents) > topology.constraints.max_agents:
        # Sort by total assignment score, keep top N
        team.agents.sort(
            key=lambda a: sum(x.combined_score for x in a.assignments),
            reverse=True,
        )
        overflow = team.agents[topology.constraints.max_agents:]
        team.agents = team.agents[:topology.constraints.max_agents]
        for role in overflow:
            team.unassigned.extend(role.assignments)

    return team
