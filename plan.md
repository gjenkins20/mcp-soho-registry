# SOHO MCP Server Registry + Auto-Orchestrator

**Status:** Planning
**Created:** 2026-03-09
**Source:** Morning Coffee briefing — Today's Top Lab Idea
**Project:** mcp-soho-registry (`~/Projects/mcp-soho-registry`)

---

## Problem Statement

MCP server discovery is fragmented across GitHub, Reddit, blog posts, and scattered docs. A developer managing a SOHO network (FortiGate, Synology, Ubiquiti, Raspberry Pi, etc.) has no way to answer: "Which MCP servers exist for my hardware, and how do I wire them into an agent team?"

Existing registries like [agent-skills-hub](https://github.com/zhuyansen/agent-skills-hub) provide general-purpose discovery but lack domain-specific scoring, topology-aware recommendations, and deployment configs.

---

## Vision

A two-part system:

1. **MCP Registry Curator** — Discovers, catalogs, and scores MCP servers with a SOHO lens
2. **Auto-Orchestrator** — Takes a network topology as input, recommends an agent team, and generates starter configs

---

## Architecture

```
                         ┌─────────────────────┐
                         │   GitHub Search API  │
                         │   agent-skills-hub   │
                         │   HuggingFace        │
                         └────────┬────────────┘
                                  │ scrape
                                  v
                      ┌───────────────────────┐
                      │   Registry Curator     │
                      │   (Python CLI)         │
                      │                        │
                      │  - Discover MCP repos  │
                      │  - Extract metadata    │
                      │  - Score & tag         │
                      │  - Store in SQLite     │
                      └────────┬──────────────┘
                               │
                               v
                      ┌───────────────────────┐
                      │   SQLite Registry DB   │
                      │                        │
                      │  servers, scores,      │
                      │  tags, capabilities,   │
                      │  vendor compatibility  │
                      └────────┬──────────────┘
                               │
                               v
                      ┌───────────────────────┐
                      │   Auto-Orchestrator    │
                      │   (Python CLI)         │
                      │                        │
                      │  Input: topology.yaml  │
                      │  Output:               │
                      │   - Agent team plan    │
                      │   - Claude Desktop cfg │
                      │   - MCP server configs │
                      │   - Safety guardrails  │
                      └───────────────────────┘
```

---

## Data Model

### MCP Server Record

| Field | Type | Description |
|---|---|---|
| `name` | str | Repo name (e.g., `fortigate-mcp-server`) |
| `full_name` | str | GitHub `owner/repo` |
| `url` | str | Repo URL |
| `description` | str | One-line description |
| `language` | str | Primary language |
| `stars` | int | GitHub stars |
| `last_commit` | date | Most recent commit |
| `tools_count` | int | Number of MCP tools exposed |
| `tool_names` | json | List of tool names (parsed from code) |
| `vendors` | json | Compatible hardware/software vendors |
| `domain_tags` | json | `[network, storage, security, compute, media, iot]` |
| `maturity_score` | float | 0-100, computed |
| `soho_relevance` | float | 0-100, computed |
| `has_tests` | bool | Test suite present |
| `has_docs` | bool | README + usage docs |
| `license` | str | SPDX identifier |
| `discovered_at` | datetime | First seen |
| `updated_at` | datetime | Last metadata refresh |

### Scoring Rubric

**Maturity Score (0-100):**

| Factor | Weight | Scoring |
|---|---|---|
| Commit frequency | 20 | >1/week=20, >1/month=10, stale=0 |
| Stars | 15 | >500=15, >100=10, >20=5, else=0 |
| Test coverage | 20 | Has tests=20, partial=10, none=0 |
| Documentation | 15 | README+examples=15, README only=8, none=0 |
| Issues responsiveness | 15 | <7d avg response=15, <30d=8, else=0 |
| License | 15 | OSI-approved=15, permissive=10, none=0 |

**SOHO Relevance Score (0-100):**

| Factor | Weight | Scoring |
|---|---|---|
| Vendor match | 40 | Direct vendor MCP (FortiGate, Synology, etc.)=40, generic network=20 |
| Domain tags | 25 | network/security/storage=25, compute/media=15, other=5 |
| Deployment complexity | 20 | Docker/pip install=20, complex deps=10, cloud-only=0 |
| Resource requirements | 15 | Runs on Pi=15, needs GPU=5, cloud-only=0 |

### Topology Input Format

```yaml
# topology.yaml
name: "My Home Network"
devices:
  - type: firewall
    vendor: fortinet
    model: FortiGate 40F
    ip: 192.168.1.99
  - type: nas
    vendor: buffalo
    model: LS-XL12C
    ip: 192.168.1.3
  - type: server
    vendor: raspberry-pi
    model: Pi 4B
    ip: 192.168.1.2
    services: [pihole, docker]
  - type: server
    vendor: raspberry-pi
    model: Pi 5
    ip: 192.168.1.4
    services: [immich, grafana, prometheus]
  - type: access-point
    vendor: tp-link
    model: Archer A54
    ip: 192.168.95.2
use_cases:
  - network-monitoring
  - security-alerting
  - photo-management
  - home-automation
constraints:
  max_agents: 8
  require_local: true  # no cloud dependencies
  approval_gated: [firewall, credentials]
```

---

## Phased Implementation

### Phase 1 — Registry Curator (Week 1-2)

**Goal:** Build the scraper and scoring engine.

- [ ] Project scaffolding (Python, SQLite, Click CLI)
- [ ] GitHub Search API scraper — discover MCP repos
  - Queries: `mcp server`, `model context protocol`, topic filters
  - Extract: stars, language, last commit, license, topics
- [ ] Tool name extractor — parse `list_tools()` or tool definitions from repo code
  - Strategy: clone shallow, grep for common MCP patterns (`@tool`, `server.tool`, tool arrays)
- [ ] Vendor detection — keyword match against known SOHO vendors
  - Vendor list: Fortinet, Ubiquiti, Synology, QNAP, TP-Link, Buffalo, Reolink, Hikvision, Raspberry Pi, Docker, Proxmox, pfSense, OPNsense
- [ ] Domain tagger — classify into network/storage/security/compute/media/iot
- [ ] Maturity scorer — implement the rubric above
- [ ] SOHO relevance scorer — implement the rubric above
- [ ] SQLite storage with upsert logic
- [ ] CLI: `mcp-registry update` — refresh the registry
- [ ] CLI: `mcp-registry list` — browse with filters
- [ ] CLI: `mcp-registry search <query>` — full-text search

**Deliverables:**
- `mcp_registry/` Python package
- `registry.db` SQLite database
- CLI with `update`, `list`, `search` commands

### Phase 2 — Auto-Orchestrator (Week 3)

**Goal:** Given a topology, recommend an agent team.

- [ ] Topology parser — read `topology.yaml`
- [ ] Matching engine — map devices/use-cases to registry MCP servers
  - Match by vendor, domain tag, capability overlap
  - Rank by combined maturity + SOHO relevance
- [ ] Agent team composer — group MCP servers into agent roles
  - Roles: network-engineer, security-ops, systems-engineer, storage-admin, media-manager
  - Assign MCP servers to roles based on tool capabilities
- [ ] Config generator — output Claude Desktop `claude_desktop_config.json`
  - Include MCP server configs with correct command/args
  - Add safety guardrails (approval gates, read-only defaults)
- [ ] Safety guardrails engine
  - Firewall/credential changes → approval-gated
  - Read-only by default for monitoring MCPs
  - Rate limiting recommendations per MCP
- [ ] CLI: `mcp-orchestrate plan topology.yaml` — generate recommendations
- [ ] CLI: `mcp-orchestrate generate topology.yaml` — output config files

**Deliverables:**
- `mcp_orchestrator/` Python package
- Config templates for Claude Desktop, agent system prompts
- Example `topology.yaml` for the MYRUG network

### Phase 3 — Testing & Polish (Week 4)

**Goal:** Validate with real SOHO setup, publish.

- [ ] Test with MYRUG network topology
  - Does it recommend FortiGate MCP, Webmin MCP, Syslog MCP, etc.?
  - Do the generated configs work with Claude Desktop?
  - Are the safety guardrails appropriate?
- [ ] Benchmark: time to set up an agent team from scratch (manual vs. orchestrator)
- [ ] Write README with usage examples and screenshots
- [ ] Create `topology-examples/` with common SOHO setups
  - Home lab (Pi + NAS + router)
  - Small office (Ubiquiti + Synology + pfSense)
  - Media server (Plex/Jellyfin + NAS + Docker)
- [ ] Publish to GitHub (public repo)
- [ ] Submit scoring rubric PR to agent-skills-hub
- [ ] Blog post: "How I automated my SOHO agent team setup"

**Deliverables:**
- Public GitHub repo with docs
- agent-skills-hub PR
- Blog post draft

---

## Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Fastest for scraping + CLI, rich ecosystem |
| CLI framework | Click | Standard, composable, well-documented |
| Database | SQLite | Zero-dependency, portable, good enough for <10K records |
| HTTP client | httpx | Async support, GitHub API pagination |
| YAML parsing | PyYAML | Topology input format |
| Config output | Jinja2 | Template Claude Desktop configs |
| Packaging | uv / pip | Modern Python tooling |

---

## Key References (from Morning Coffee 2026-03-09)

| Project | Stars | Relevance |
|---|---|---|
| [mcp2cli](https://github.com/knowsuchagency/mcp2cli) | 321 | Token-efficient MCP CLI wrappers — integration target |
| [agent-skills-hub](https://github.com/zhuyansen/agent-skills-hub) | 79 | Existing registry to integrate with / contribute to |
| [GitClaw](https://github.com/open-gitagent/gitclaw) | 66 | Git-native agent state — audit trail inspiration |
| [AgentSeal](https://github.com/nicholasyager/agentseal) | — | Agent security scanner — safety guardrail reference |

---

## Open Questions

1. **Scope of vendor coverage** — Start with vendors we actually use (Fortinet, Buffalo, TP-Link, Raspberry Pi) or go broad from day one?
2. **Registry freshness** — How often to re-scrape? Daily cron, or on-demand only?
3. **Community contribution model** — Accept PRs to add vendor mappings, or fully automated?
4. **Integration with existing MYRUG setup** — Should the orchestrator output update our existing `CLAUDE.md` and agent prompts, or generate standalone configs?
5. **Monetization** — Open-source the tool, sell consulting for custom topology analysis? Or SaaS registry with API?

---

## Estimated Effort

| Phase | Hours | Calendar |
|---|---|---|
| Phase 1 — Registry Curator | 8-10 | Week 1-2 |
| Phase 2 — Auto-Orchestrator | 8-10 | Week 3 |
| Phase 3 — Testing & Publish | 6-8 | Week 4 |
| **Total** | **22-28** | **~4 weeks** |

---

*Inspired by Morning Coffee briefing, 2026-03-09*
