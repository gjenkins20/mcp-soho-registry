"""Vendor detection for SOHO hardware and software."""

from __future__ import annotations

from mcp_registry.models import MCPServer

# Vendor keyword mappings: vendor name -> list of keywords to search for
VENDOR_KEYWORDS: dict[str, list[str]] = {
    # Network / Firewall
    "fortinet": ["fortinet", "fortigate", "fortianalyzer", "fortios"],
    "ubiquiti": ["ubiquiti", " unifi ", "unifi-", "-unifi", "edgerouter", "usg "],
    "pfsense": ["pfsense", "opnsense"],
    "opnsense": ["opnsense"],
    "tp-link": ["tp-link", "tplink", "omada"],
    "mikrotik": ["mikrotik", "routeros"],
    "netgear": ["netgear"],

    # NAS / Storage
    "synology": ["synology", "dsm", "diskstation"],
    "qnap": ["qnap", "qts"],
    "buffalo": ["buffalo", "linkstation", "terastation"],
    "truenas": ["truenas", "freenas"],

    # Compute / SBC
    "raspberry-pi": ["raspberry pi", "raspberry-pi", "raspberrypi", "rpi", "pi-hole", "pihole"],
    "proxmox": ["proxmox", "pve"],
    "docker": ["docker", "container", "docker-compose", "dockerfile"],
    "portainer": ["portainer"],

    # Media
    "plex": ["plexmedia", "plexmediaserver", "plex media server"],
    "jellyfin": ["jellyfin"],
    "immich": ["immich"],

    # Monitoring
    "grafana": ["grafana"],
    "prometheus": ["prometheus"],
    "zabbix": ["zabbix"],

    # Home Automation
    "home-assistant": ["home-assistant", "homeassistant", "hass"],
    "mqtt": ["mqtt", "mosquitto"],

    # Camera / Security
    "reolink": ["reolink"],
    "hikvision": ["hikvision"],
    "frigate": ["frigate"],

    # System Management
    "webmin": ["webmin"],
    "cockpit": ["cockpit-project", "cockpit-ws"],
    "ansible": ["ansible"],
}


def detect_vendors(server: MCPServer) -> list[str]:
    """Detect compatible vendors from server metadata.

    Scans name, description, README, tool names, and topics.
    Returns a sorted list of matched vendor names.
    """
    # Build a single text corpus to search
    corpus = " ".join([
        server.name.lower(),
        server.full_name.lower(),
        server.description.lower(),
        server.readme_text.lower(),
        " ".join(server.tool_names).lower(),
        " ".join(server.topics).lower(),
    ])

    matched: set[str] = set()
    for vendor, keywords in VENDOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in corpus:
                matched.add(vendor)
                break

    server.vendors = sorted(matched)
    return server.vendors
