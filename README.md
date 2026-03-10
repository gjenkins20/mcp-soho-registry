# MCP SOHO Registry

Discover, catalog, and score MCP (Model Context Protocol) servers with a SOHO network lens. Then auto-generate agent team configurations for your home lab.

## Features

- **Registry Curator** — Scrapes GitHub for MCP servers, extracts tool metadata, detects SOHO hardware vendors, and scores maturity + relevance
- **Auto-Orchestrator** — Takes your network topology as input, recommends an agent team, and generates Claude Desktop configs with safety guardrails

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# 1. Populate the registry from GitHub
mcp-registry update

# 2. Describe your network (see topology-examples/)
# 3. Get agent team recommendations
mcp-orchestrate plan topology-examples/home-lab.yaml

# 4. Generate config files
mcp-orchestrate generate topology-examples/home-lab.yaml -o ./my-config
```

## Registry Commands

### Update the registry

```bash
# Discover MCP servers from GitHub (set GITHUB_TOKEN for higher rate limits)
mcp-registry update

# Quick metadata-only scan (skip tool extraction via shallow clones)
mcp-registry update --skip-extract

# Custom search queries
mcp-registry update --query "unifi mcp" --query "fortigate mcp"
```

### Browse and search

```bash
# List top SOHO-relevant servers
mcp-registry list

# Filter by vendor or domain
mcp-registry list --vendor fortinet
mcp-registry list --domain network
mcp-registry list --min-soho 50 --sort stars

# Full-text search
mcp-registry search "firewall"
mcp-registry search "synology backup"

# Registry stats
mcp-registry stats
```

### Example output

```
Name                                Stars  Mat SOHO Tools Vendors                   Tags
---------------------------------------------------------------------------------------------------------
myraffy/homelab-mcp                     0   70   95    60 ansible, docker, home-a~  compute, network, security
ridafkih/keeper.sh                    411   95   85     0 docker, home-assistant    compute, security
Betoche57/mcp-firewall                  1   50   85     0 opnsense, pfsense         network, security, storage
activepieces/activepieces           21157   78   85  4736 docker, synology          compute, iot, media
```

## Orchestrator Commands

### Plan an agent team

```bash
mcp-orchestrate plan topology-examples/home-lab.yaml
```

Output includes:
- Matched MCP servers grouped by agent role (network-engineer, security-ops, systems-engineer, storage-admin, media-manager, iot-coordinator)
- Combined scores based on vendor match, SOHO relevance, and maturity
- Coverage gaps (missing vendors, uncovered use cases)
- Safety guardrail summary

### Generate config files

```bash
mcp-orchestrate generate topology-examples/small-office.yaml -o ./my-config
```

Generates:
- `claude_desktop_config.json` — Drop-in MCP server configuration
- `agent_prompts/` — Per-role system prompts with safety guidelines
- `plan_report.md` — Human-readable team plan

## Topology Format

Describe your network in YAML:

```yaml
name: "Home Lab"
devices:
  - type: firewall
    vendor: pfsense
    model: SG-3100
    ip: 10.0.0.1
  - type: nas
    vendor: synology
    model: DS920+
    ip: 10.0.0.10
  - type: server
    vendor: raspberry-pi
    model: Pi 5
    ip: 10.0.0.20
    services: [docker, grafana, prometheus]
use_cases:
  - network-monitoring
  - security-alerting
  - backup
constraints:
  max_agents: 6
  require_local: true
  approval_gated: [firewall, credentials]
```

See `topology-examples/` for more templates.

## Scoring

Each server gets two scores (0–100):

**Maturity Score** — Commit frequency, stars, tests, docs, license, responsiveness

**SOHO Relevance Score** — Vendor match (FortiGate, Synology, etc.), domain tags (network/security/storage), deployment simplicity, resource requirements

## Safety Guardrails

The orchestrator applies safety defaults to every generated config:

- **Read-only by default** — All MCP servers start in read-only mode
- **Approval-gated operations** — Firewall changes, credential operations, DNS modifications, and other dangerous actions require human confirmation
- **Rate limiting** — Per-domain rate limits (e.g., 5 req/min for security, 30 req/min for IoT polling)
- **Topology constraints** — Honor `approval_gated` and `max_agents` from your topology

## Supported Vendors

| Category | Vendors |
|----------|---------|
| Network/Firewall | Fortinet, Ubiquiti, pfSense, OPNsense, TP-Link, MikroTik, Netgear |
| Storage/NAS | Synology, QNAP, Buffalo, TrueNAS |
| Compute | Raspberry Pi, Proxmox, Docker, Portainer |
| Monitoring | Grafana, Prometheus, Zabbix |
| Media | Plex, Jellyfin, Immich |
| IoT/Automation | Home Assistant, MQTT, Frigate |
| Camera/Security | Reolink, Hikvision |
| System Management | Webmin, Cockpit, Ansible |

## Project Structure

```
mcp_registry/       # Phase 1: Registry Curator
  scraper.py        #   GitHub API discovery
  extractor.py      #   Tool name extraction via shallow clone
  vendors.py        #   SOHO vendor detection
  tagger.py         #   Domain classification
  scorer.py         #   Maturity + SOHO relevance scoring
  db.py             #   SQLite + FTS5 storage
  cli.py            #   mcp-registry CLI

mcp_orchestrator/   # Phase 2: Auto-Orchestrator
  topology.py       #   YAML topology parser
  matcher.py        #   Topology-to-registry matching engine
  composer.py       #   Agent team composition
  guardrails.py     #   Safety guardrail assessment
  generator.py      #   Config file generation
  cli.py            #   mcp-orchestrate CLI

topology-examples/  # Sample network topologies
tests/              # pytest test suite
```

## About the Developer

Built by **Gregori Jenkins** — originally from Chicago, a humble student of Computer Science, and a proud cat dad.

[Connect on LinkedIn](https://www.linkedin.com/in/gregorijenkins)

## License

MIT
