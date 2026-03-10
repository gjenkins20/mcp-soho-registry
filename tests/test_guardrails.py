"""Tests for the safety guardrails engine."""

from mcp_registry.models import MCPServer
from mcp_orchestrator.composer import compose_team
from mcp_orchestrator.guardrails import assess_guardrails
from mcp_orchestrator.matcher import Match
from mcp_orchestrator.topology import Topology, Device, Constraints


def _make_topology():
    return Topology(
        name="Test",
        devices=[Device(type="firewall", vendor="fortinet")],
        use_cases=[],
        constraints=Constraints(approval_gated=["firewall", "credentials"]),
    )


class TestGuardrails:
    def test_firewall_server_gets_approval_gated(self):
        topo = _make_topology()
        matches = [
            Match(
                server=MCPServer(
                    name="firewall-manager", full_name="x/firewall-manager", url="",
                    vendors=["fortinet"], domain_tags=["network", "security"],
                    maturity_score=70, soho_relevance=90,
                ),
                match_reasons=["vendor:fortinet"],
            ),
        ]
        team = compose_team(topo, matches)
        guardrails = assess_guardrails(team, topo)
        fw_configs = [c for c in guardrails.configs if "firewall" in c.server_name]
        assert len(fw_configs) == 1
        assert fw_configs[0].access_mode == "approval-gated"

    def test_monitoring_server_gets_readonly(self):
        topo = _make_topology()
        matches = [
            Match(
                server=MCPServer(
                    name="status-monitor", full_name="x/status-monitor", url="",
                    vendors=[], domain_tags=["network"],
                    maturity_score=50, soho_relevance=50,
                ),
                match_reasons=["domain:network"],
            ),
        ]
        team = compose_team(topo, matches)
        guardrails = assess_guardrails(team, topo)
        mon_configs = [c for c in guardrails.configs if "monitor" in c.server_name]
        assert len(mon_configs) == 1
        assert mon_configs[0].access_mode == "read-only"

    def test_no_approval_gates_warning(self):
        topo = Topology(
            name="Test",
            devices=[Device(type="server", vendor="raspberry-pi")],
            use_cases=[],
            constraints=Constraints(approval_gated=[]),
        )
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
        guardrails = assess_guardrails(team, topo)
        assert any("No approval gates" in w for w in guardrails.global_warnings)
