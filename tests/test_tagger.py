"""Tests for domain tagging."""

from mcp_registry.models import MCPServer
from mcp_registry.tagger import tag_domains


class TestDomainTagger:
    def test_network_from_description(self):
        s = MCPServer(
            name="fw-mcp", full_name="x/fw-mcp", url="",
            description="Manage firewall rules and network interfaces",
        )
        tags = tag_domains(s)
        assert "network" in tags

    def test_security_tags(self):
        s = MCPServer(
            name="vuln-scanner-mcp", full_name="x/vuln-scanner-mcp", url="",
            description="Vulnerability scanning and security audit tool",
        )
        tags = tag_domains(s)
        assert "security" in tags

    def test_storage_tags(self):
        s = MCPServer(
            name="nas-mcp", full_name="x/nas-mcp", url="",
            description="NAS management with backup and snapshot support",
        )
        tags = tag_domains(s)
        assert "storage" in tags

    def test_multiple_domains(self):
        s = MCPServer(
            name="network-security-mcp", full_name="x/net-sec-mcp", url="",
            description="Network firewall with intrusion detection and security monitoring",
        )
        tags = tag_domains(s)
        assert "network" in tags
        assert "security" in tags

    def test_no_tags_for_generic(self):
        s = MCPServer(
            name="calculator-mcp", full_name="x/calc-mcp", url="",
            description="A simple calculator",
        )
        tags = tag_domains(s)
        assert tags == []
