"""Maturity and SOHO relevance scoring engine."""

from datetime import datetime, timezone

# --- Vendor and domain constants ---

SOHO_VENDORS = [
    "fortinet", "fortigate",
    "ubiquiti", "unifi",
    "synology",
    "qnap",
    "tp-link", "tplink", "archer",
    "buffalo", "linkstation",
    "reolink",
    "hikvision",
    "raspberry pi", "raspberrypi", "rpi",
    "docker",
    "proxmox",
    "pfsense",
    "opnsense",
    "mikrotik",
    "netgear",
    "pihole", "pi-hole",
]

DOMAIN_KEYWORDS = {
    "network": ["network", "router", "switch", "vlan", "firewall", "dns", "dhcp", "wifi", "snmp", "netflow"],
    "security": ["security", "firewall", "ids", "ips", "threat", "vuln", "auth", "certificate", "ssl", "tls"],
    "storage": ["storage", "nas", "backup", "file", "smb", "nfs", "raid", "disk", "s3"],
    "compute": ["server", "vm", "container", "docker", "kubernetes", "k8s", "proxmox", "lxc"],
    "media": ["media", "plex", "jellyfin", "photo", "immich", "video", "stream", "transcod"],
    "iot": ["iot", "sensor", "mqtt", "zigbee", "zwave", "home assistant", "homeassistant", "automation"],
}


def detect_vendors(text: str) -> list[str]:
    """Find known SOHO vendors mentioned in text."""
    lower = text.lower()
    found = []
    for vendor in SOHO_VENDORS:
        if vendor in lower:
            found.append(vendor)
    return sorted(set(found))


def detect_domains(text: str) -> list[str]:
    """Classify text into domain tags."""
    lower = text.lower()
    tags = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            tags.append(domain)
    return tags


def compute_maturity_score(
    stars: int = 0,
    last_commit: str = "",
    has_tests: bool = False,
    has_docs: bool = False,
    license_id: str = "",
) -> float:
    """Compute maturity score (0-100) based on the rubric."""
    score = 0.0

    # Commit frequency (20 pts) — approximate from last_commit date
    if last_commit:
        try:
            last_dt = datetime.fromisoformat(last_commit.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - last_dt).days
            if days_ago < 7:
                score += 20
            elif days_ago < 30:
                score += 10
        except (ValueError, TypeError):
            pass

    # Stars (15 pts)
    if stars > 500:
        score += 15
    elif stars > 100:
        score += 10
    elif stars > 20:
        score += 5

    # Test coverage (20 pts)
    if has_tests:
        score += 20

    # Documentation (15 pts)
    if has_docs:
        score += 15

    # License (15 pts)
    permissive = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"}
    osi = permissive | {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "MPL-2.0", "AGPL-3.0"}
    if license_id in permissive:
        score += 15
    elif license_id in osi:
        score += 10

    # Issues responsiveness (15 pts) — skip for now, requires extra API call
    return score


def compute_soho_relevance(
    vendors: list[str],
    domain_tags: list[str],
    description: str = "",
) -> float:
    """Compute SOHO relevance score (0-100)."""
    score = 0.0

    # Vendor match (40 pts)
    if vendors:
        score += 40
    elif any(kw in description.lower() for kw in ["network", "router", "firewall", "nas"]):
        score += 20

    # Domain tags (25 pts)
    high_value = {"network", "security", "storage"}
    mid_value = {"compute", "media"}
    if high_value & set(domain_tags):
        score += 25
    elif mid_value & set(domain_tags):
        score += 15
    elif domain_tags:
        score += 5

    # Deployment complexity & resource requirements — would need deeper
    # repo analysis (Dockerfile presence, requirements.txt, etc.)
    # For now, give partial credit if Python or TypeScript (easy to install)
    # These will be refined in Phase 1 implementation

    return score
