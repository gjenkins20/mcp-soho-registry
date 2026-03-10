"""Matching engine — maps topology devices and use cases to registry MCP servers."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcp_registry.db import RegistryDB
from mcp_registry.models import MCPServer

from mcp_orchestrator.topology import Topology

# Map device types to domain tags for matching
DEVICE_TYPE_TO_DOMAINS: dict[str, list[str]] = {
    "firewall": ["network", "security"],
    "router": ["network"],
    "switch": ["network"],
    "access-point": ["network"],
    "nas": ["storage"],
    "server": ["compute"],
    "camera": ["security", "iot"],
    "sensor": ["iot"],
    "media-server": ["media"],
}

# Map use cases to domain tags
USE_CASE_TO_DOMAINS: dict[str, list[str]] = {
    "network-monitoring": ["network"],
    "security-alerting": ["security", "network"],
    "photo-management": ["media", "storage"],
    "home-automation": ["iot"],
    "backup": ["storage"],
    "media-streaming": ["media"],
    "container-management": ["compute"],
    "log-management": ["network", "security"],
    "performance-monitoring": ["compute", "network"],
}

# Map services to vendor keywords for matching
# NOTE: "docker" is omitted — it's deployment infrastructure, not a signal
# that a server is specifically about Docker management. Including it pulls
# in every repo that happens to offer a Docker install method.
SERVICE_TO_VENDORS: dict[str, list[str]] = {
    "pihole": ["raspberry-pi"],
    "immich": ["immich"],
    "grafana": ["grafana"],
    "prometheus": ["prometheus"],
    "plex": ["plex"],
    "jellyfin": ["jellyfin"],
    "home-assistant": ["home-assistant"],
    "portainer": ["portainer"],
    "proxmox": ["proxmox"],
    "frigate": ["frigate"],
}


# Match reason weights — how much each type of match contributes
REASON_WEIGHTS: dict[str, float] = {
    "vendor": 25.0,   # Direct vendor match is the strongest signal
    "service": 15.0,  # Service running on a device
    "domain": 5.0,    # Domain tag overlap (weak on its own)
    "search": 3.0,    # FTS hit (weakest, most noise-prone)
}

# Generic services that match too many repos to be useful as FTS terms
GENERIC_SEARCH_TERMS = {"docker", "server", "compute", "network", "storage"}


@dataclass
class Match:
    """A matched MCP server with relevance context."""

    server: MCPServer
    match_reasons: list[str] = field(default_factory=list)
    combined_score: float = 0.0

    def recalculate_score(self) -> None:
        """Recalculate combined score from base scores + match reason weights."""
        base = (
            self.server.soho_relevance * 0.5
            + self.server.maturity_score * 0.3
        )
        # Add weighted reason bonuses
        reason_bonus = 0.0
        for reason in self.match_reasons:
            prefix = reason.split(":")[0]
            reason_bonus += REASON_WEIGHTS.get(prefix, 0)
        # Cap reason bonus contribution
        reason_bonus = min(reason_bonus, 30)
        self.combined_score = min(base + reason_bonus, 100)

    def __post_init__(self) -> None:
        if self.combined_score == 0:
            self.recalculate_score()


def find_matches(
    topology: Topology,
    db: RegistryDB,
    *,
    min_score: float = 40,
    limit_per_query: int = 10,
) -> list[Match]:
    """Find MCP servers matching the topology's devices, services, and use cases.

    Returns a deduplicated, scored, and sorted list of matches.

    Matching priority:
    1. Vendor matches (strongest) — topology vendor directly in server's vendor list
    2. Service matches — topology services mapped to vendor keywords
    3. Domain matches (weaker) — only servers with high SOHO relevance
    4. FTS search (weakest) — only for non-generic vendor/service terms
    """
    seen: set[str] = set()
    matches: list[Match] = []

    def _add_match(server: MCPServer, reason: str) -> None:
        if server.full_name in seen:
            for m in matches:
                if m.server.full_name == server.full_name:
                    m.match_reasons.append(reason)
                    m.recalculate_score()
                    break
            return
        seen.add(server.full_name)
        matches.append(Match(server=server, match_reasons=[reason]))

    # 1. Match by vendor name (highest priority, no score floor)
    for vendor in topology.all_vendors:
        results = db.list_servers(vendor=vendor, limit=limit_per_query)
        for server in results:
            _add_match(server, f"vendor:{vendor}")

    # 2. Match by service -> vendor mapping
    for service in topology.all_services:
        vendor_list = SERVICE_TO_VENDORS.get(service, [])
        for vendor in vendor_list:
            results = db.list_servers(vendor=vendor, limit=limit_per_query)
            for server in results:
                _add_match(server, f"service:{service}")

    # 3. Match by device type + use case -> domain tags
    #    Only pull in servers with SOHO relevance >= 60 to filter noise
    needed_domains: set[str] = set()
    for dtype in topology.all_device_types:
        domains = DEVICE_TYPE_TO_DOMAINS.get(dtype, [])
        needed_domains.update(domains)
    for use_case in topology.use_cases:
        domains = USE_CASE_TO_DOMAINS.get(use_case, [])
        needed_domains.update(domains)

    domain_min_soho = max(min_score, 70)
    for domain in needed_domains:
        results = db.list_servers(
            domain=domain, min_soho=domain_min_soho, limit=5,
        )
        for server in results:
            _add_match(server, f"domain:{domain}")

    # 4. FTS search — only for specific (non-generic) terms
    search_terms = (topology.all_vendors | topology.all_services) - GENERIC_SEARCH_TERMS
    for term in search_terms:
        try:
            results = db.search_servers(term, limit=3)
            for server in results:
                _add_match(server, f"search:{term}")
        except Exception:
            pass

    # Filter: require a strong signal, not just domain overlap
    filtered = []
    for m in matches:
        if m.combined_score < min_score:
            continue
        # Servers matched only by domain/search (no vendor or service match)
        # need a much higher score to be included — they're low-signal
        has_strong_match = any(
            r.startswith("vendor:") or r.startswith("service:")
            for r in m.match_reasons
        )
        if not has_strong_match and m.combined_score < 75:
            continue
        filtered.append(m)

    filtered.sort(key=lambda m: m.combined_score, reverse=True)
    return filtered
