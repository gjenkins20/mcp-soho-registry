"""Maturity and SOHO relevance scoring for MCP servers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mcp_registry.models import MCPServer

# Vendors that are direct SOHO hardware/software
SOHO_DIRECT_VENDORS = {
    "fortinet", "ubiquiti", "pfsense", "opnsense", "tp-link", "mikrotik",
    "synology", "qnap", "buffalo", "truenas", "raspberry-pi",
    "reolink", "hikvision", "home-assistant",
}

# Vendors that are generic infrastructure (relevant but less specific)
SOHO_GENERIC_VENDORS = {
    "docker", "proxmox", "portainer", "grafana", "prometheus",
    "ansible", "webmin", "cockpit", "mqtt", "plex", "jellyfin",
    "immich", "frigate", "zabbix", "netgear",
}

# Domains most relevant to SOHO management
SOHO_PRIMARY_DOMAINS = {"network", "security", "storage"}
SOHO_SECONDARY_DOMAINS = {"compute", "media", "iot"}

# Keywords suggesting cloud-only deployment
CLOUD_ONLY_KEYWORDS = [
    "aws lambda", "google cloud function", "azure function",
    "cloud run", "fargate", "vercel", "netlify", "heroku",
]

# Keywords suggesting lightweight / Pi-friendly deployment
LIGHTWEIGHT_KEYWORDS = [
    "raspberry pi", "arm64", "aarch64", "lightweight", "minimal",
    "low memory", "pip install", "docker", "single binary",
]


def score_maturity(server: MCPServer) -> float:
    """Score server maturity 0-100 based on the rubric.

    Factors:
    - Commit recency (20): >1/week=20, >1/month=10, stale=0
    - Stars (15): >500=15, >100=10, >20=5, else=0
    - Test coverage (20): has tests=20, else=0
    - Documentation (15): README+examples=15, README only=8, else=0
    - License (15): present=15, else=0
    - Issues responsiveness (15): approximated from activity signals
    """
    score = 0.0

    # Commit recency (20 points)
    if server.last_commit:
        try:
            last = datetime.fromisoformat(server.last_commit).replace(tzinfo=UTC)
            age = datetime.now(UTC) - last
            if age < timedelta(days=7):
                score += 20
            elif age < timedelta(days=30):
                score += 15
            elif age < timedelta(days=90):
                score += 10
            elif age < timedelta(days=180):
                score += 5
        except ValueError:
            pass

    # Stars (15 points)
    if server.stars >= 500:
        score += 15
    elif server.stars >= 100:
        score += 10
    elif server.stars >= 20:
        score += 5
    elif server.stars >= 5:
        score += 2

    # Test coverage (20 points)
    if server.has_tests:
        score += 20

    # Documentation (15 points)
    if server.has_docs:
        score += 15
    elif server.readme_text or server.description:
        score += 8

    # License (15 points)
    if server.license and server.license not in ("NOASSERTION", ""):
        score += 15

    # Issues responsiveness (15 points) - approximated
    # High stars + recent commits = likely responsive
    if server.stars >= 50 and server.last_commit:
        try:
            last = datetime.fromisoformat(server.last_commit).replace(tzinfo=UTC)
            if (datetime.now(UTC) - last) < timedelta(days=30):
                score += 15
            elif (datetime.now(UTC) - last) < timedelta(days=90):
                score += 8
        except ValueError:
            pass
    elif server.stars >= 10:
        score += 5

    server.maturity_score = min(score, 100)
    return server.maturity_score


def score_soho_relevance(server: MCPServer) -> float:
    """Score SOHO relevance 0-100 based on the rubric.

    Factors:
    - Vendor match (40): direct SOHO vendor=40, generic=20, none=5
    - Domain tags (25): primary SOHO domains=25, secondary=15, other=5
    - Deployment complexity (20): simple=20, moderate=10, cloud-only=0
    - Resource requirements (15): Pi-friendly=15, moderate=10, cloud=0
    """
    score = 0.0
    corpus = " ".join([
        server.name.lower(),
        server.description.lower(),
        server.readme_text.lower(),
    ])

    # Vendor match (40 points)
    has_direct = any(v in SOHO_DIRECT_VENDORS for v in server.vendors)
    has_generic = any(v in SOHO_GENERIC_VENDORS for v in server.vendors)
    direct_count = sum(1 for v in server.vendors if v in SOHO_DIRECT_VENDORS)
    if has_direct and direct_count >= 2:
        score += 40  # multiple direct vendors = very SOHO
    elif has_direct:
        score += 35
    elif has_generic:
        score += 15  # generic infra only = moderate signal
    elif server.vendors:
        score += 5

    # Domain tags (25 points)
    has_primary = any(t in SOHO_PRIMARY_DOMAINS for t in server.domain_tags)
    has_secondary = any(t in SOHO_SECONDARY_DOMAINS for t in server.domain_tags)
    primary_count = sum(1 for t in server.domain_tags if t in SOHO_PRIMARY_DOMAINS)
    if has_primary and primary_count >= 2:
        score += 25  # multiple primary domains = strong SOHO signal
    elif has_primary:
        score += 20
    elif has_secondary:
        score += 10
    elif server.domain_tags:
        score += 5

    # Deployment complexity (20 points)
    is_cloud = any(kw in corpus for kw in CLOUD_ONLY_KEYWORDS)
    has_docker = "docker" in corpus or "pip install" in corpus
    if is_cloud and not has_docker:
        score += 0
    elif has_docker:
        score += 15
    else:
        score += 10  # assume moderate

    # Resource requirements (15 points)
    is_lightweight = any(kw in corpus for kw in LIGHTWEIGHT_KEYWORDS)
    needs_gpu = "gpu" in corpus or "cuda" in corpus or "nvidia" in corpus
    if is_lightweight:
        score += 15
    elif needs_gpu:
        score += 0
    elif is_cloud:
        score += 0
    else:
        score += 10  # assume moderate

    server.soho_relevance = min(score, 100)
    return server.soho_relevance
