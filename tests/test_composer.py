"""Tests for the agent team composer."""

from mcp_registry.models import MCPServer
from mcp_orchestrator.composer import compose_team, AgentTeam
from mcp_orchestrator.matcher import Match
from mcp_orchestrator.topology import Topology, Device, Constraints


def _make_topology():
    return Topology(
        name="Test Network",
        devices=[
            Device(type="firewall", vendor="fortinet"),
            Device(type="server", vendor="raspberry-pi", services=["docker"]),
        ],
        use_cases=["network-monitoring"],
        constraints=Constraints(max_agents=4, approval_gated=["firewall"]),
    )


def _make_matches():
    return [
        Match(
            server=MCPServer(
                name="fortigate-mcp", full_name="x/fortigate-mcp", url="",
                vendors=["fortinet"], domain_tags=["network", "security"],
                maturity_score=70, soho_relevance=90,
            ),
            match_reasons=["vendor:fortinet", "domain:network"],
        ),
        Match(
            server=MCPServer(
                name="docker-mcp", full_name="x/docker-mcp", url="",
                vendors=["docker"], domain_tags=["compute"],
                maturity_score=80, soho_relevance=60,
            ),
            match_reasons=["service:docker", "domain:compute"],
        ),
        Match(
            server=MCPServer(
                name="monitor-mcp", full_name="x/monitor-mcp", url="",
                vendors=[], domain_tags=["network"],
                maturity_score=50, soho_relevance=40,
            ),
            match_reasons=["domain:network"],
        ),
    ]


class TestComposer:
    def test_compose_assigns_to_roles(self):
        team = compose_team(_make_topology(), _make_matches())
        assert isinstance(team, AgentTeam)
        assert len(team.active_agents) > 0

    def test_network_server_assigned_to_network_role(self):
        team = compose_team(_make_topology(), _make_matches())
        roles = {a.role for a in team.active_agents}
        # fortigate-mcp should land in network-engineer or security-ops
        assert "network-engineer" in roles or "security-ops" in roles

    def test_docker_server_assigned_to_systems_role(self):
        team = compose_team(_make_topology(), _make_matches())
        sys_agents = [a for a in team.active_agents if a.role == "systems-engineer"]
        if sys_agents:
            names = [x.server_name for x in sys_agents[0].assignments]
            assert "docker-mcp" in names

    def test_gaps_detected_for_missing_vendor(self):
        topo = _make_topology()
        # No matches for fortinet
        matches = [
            Match(
                server=MCPServer(
                    name="generic-mcp", full_name="x/generic-mcp", url="",
                    vendors=["docker"], domain_tags=["compute"],
                    maturity_score=50, soho_relevance=50,
                ),
                match_reasons=["domain:compute"],
            ),
        ]
        team = compose_team(topo, matches)
        # fortinet should be flagged as a gap
        assert any("fortinet" in g for g in team.gaps)

    def test_max_agents_constraint(self):
        topo = Topology(
            name="Test",
            devices=[Device(type="server", vendor="raspberry-pi")],
            use_cases=[],
            constraints=Constraints(max_agents=1),
        )
        team = compose_team(topo, _make_matches())
        assert len(team.active_agents) <= 1
