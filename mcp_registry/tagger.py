"""Domain tag classifier for MCP servers."""

from __future__ import annotations

from mcp_registry.models import MCPServer

# Domain -> keywords that indicate relevance
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "network": [
        "network", "firewall", "router", "switch", "vlan", "dns", "dhcp",
        "vpn", "wifi", "wireless", "snmp", "netflow", "syslog", "ping",
        "traceroute", "bandwidth", "latency", "packet", "interface",
        "subnet", "gateway", "routing", "arp", "bgp", "ospf",
    ],
    "security": [
        "security", "firewall", "ids", "ips", "threat", "vulnerability",
        "audit", "compliance", "ssl", "tls", "certificate", "auth",
        "authentication", "authorization", "encryption", "malware",
        "antivirus", "intrusion", "exploit", "cve", "pentest",
    ],
    "storage": [
        "storage", "nas", "san", "backup", "raid", "disk", "volume",
        "share", "smb", "nfs", "cifs", "snapshot", "replication",
        "file server", "s3", "minio", "rsync",
    ],
    "compute": [
        "compute", "vm ", "virtual machine", "container", "docker",
        "kubernetes", "k8s", "proxmox", "hypervisor", "cpu",
        "systemd", "ssh", "ansible", "terraform",
    ],
    "media": [
        "media", "plex", "jellyfin", "emby", "transcod", "stream",
        "video", "audio", "photo", "image", "gallery", "immich",
        "sonarr", "radarr", "lidarr", "torrent",
    ],
    "iot": [
        "iot", "home assistant", "homeassistant", "mqtt", "zigbee",
        "z-wave", "sensor", "thermostat", "smart home", "automation",
        "esp32", "arduino", "gpio", "i2c", "camera", "motion",
    ],
}


def tag_domains(server: MCPServer) -> list[str]:
    """Classify a server into domain tags based on metadata.

    Scans name, description, README, tool names, and topics.
    Returns a sorted list of matched domain tags.
    """
    corpus = " ".join([
        server.name.lower(),
        server.full_name.lower(),
        server.description.lower(),
        server.readme_text.lower(),
        " ".join(server.tool_names).lower(),
        " ".join(server.topics).lower(),
    ])

    matched: set[str] = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in corpus)
        # Require at least 2 keyword matches to reduce false positives
        # (except for single-word matches in the name itself)
        if match_count >= 2:
            matched.add(domain)
        elif match_count == 1:
            # Single match is ok if it's in the name or description (higher signal)
            name_desc = f"{server.name} {server.description}".lower()
            if any(kw in name_desc for kw in keywords):
                matched.add(domain)

    server.domain_tags = sorted(matched)
    return server.domain_tags
