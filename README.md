# MCP SOHO Registry

A discovery and scoring engine for [Model Context Protocol](https://modelcontextprotocol.io/) servers, built with small office / home office (SOHO) networks in mind.

## Problem

MCP server discovery is fragmented across GitHub, Reddit, blog posts, and scattered docs. If you manage a SOHO network — firewalls, NAS devices, Raspberry Pis, access points — there's no way to answer: *"Which MCP servers exist for my hardware, and how do I wire them into an agent team?"*

## What This Does

**Registry Curator** — Discovers MCP server repos via the GitHub Search API, then scores each one for maturity and SOHO relevance.

**Auto-Orchestrator** *(planned)* — Takes a YAML description of your network topology, matches it against the registry, and generates Claude Desktop configs with safety guardrails.

## Quick Start

```bash
# Install
pip install -e .

# Populate the registry (optional: set GITHUB_TOKEN for higher rate limits)
mcp-registry update

# Browse registered servers
mcp-registry list --min-soho 40

# Search for something specific
mcp-registry search firewall
```

## Scoring

Every discovered MCP server gets two scores:

**Maturity (0-100)** — Based on commit recency, stars, test coverage, documentation, and license.

**SOHO Relevance (0-100)** — Based on vendor compatibility (Fortinet, Ubiquiti, Synology, QNAP, TP-Link, Raspberry Pi, etc.), domain tags (network, security, storage, compute, media, IoT), and deployment complexity.

## Topology-Driven Orchestration

Define your network in YAML and let the orchestrator recommend an agent team:

```yaml
# topology.yaml
name: "My Home Lab"
devices:
  - type: firewall
    vendor: fortinet
    model: FortiGate 40F
    ip: 10.0.0.1
  - type: nas
    vendor: synology
    model: DS923+
    ip: 10.0.0.10
  - type: server
    vendor: raspberry-pi
    model: Pi 5
    ip: 10.0.0.20
    services: [pihole, docker, grafana]
use_cases:
  - network-monitoring
  - security-alerting
constraints:
  max_agents: 8
  require_local: true
  approval_gated: [firewall, credentials]
```

See [`topology-examples/`](topology-examples/) for more examples.

## Project Structure

```
mcp_registry/       # Registry curator — scraper, scorer, SQLite DB, CLI
mcp_orchestrator/   # Auto-orchestrator — topology parser, config generator (Phase 2)
topology-examples/  # Sample network topologies
tests/              # Test suite
```

## Status

Early development. The registry curator (Phase 1) is functional. The auto-orchestrator (Phase 2) is stubbed out.

## Requirements

- Python 3.11+
- Optional: `GITHUB_TOKEN` environment variable for higher API rate limits

## License

MIT

## About the Developer

Built by **Gregori Jenkins** — originally from Chicago, a humble student of Computer Science, and a proud cat dad.

[Connect on LinkedIn](https://www.linkedin.com/in/gregorijenkins)
