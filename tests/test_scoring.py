"""Tests for the scoring engine."""

from mcp_registry.scoring import (
    compute_maturity_score,
    compute_soho_relevance,
    detect_domains,
    detect_vendors,
)


class TestDetectVendors:
    def test_finds_fortinet(self):
        assert "fortinet" in detect_vendors("FortiGate MCP Server for Fortinet devices")

    def test_finds_multiple(self):
        vendors = detect_vendors("Synology NAS + Ubiquiti UniFi integration")
        assert "synology" in vendors
        assert "ubiquiti" in vendors

    def test_no_match(self):
        assert detect_vendors("generic web scraper tool") == []


class TestDetectDomains:
    def test_network(self):
        assert "network" in detect_domains("network router VLAN management")

    def test_security(self):
        assert "security" in detect_domains("firewall threat detection IDS")

    def test_multiple(self):
        tags = detect_domains("NAS storage with Docker containers")
        assert "storage" in tags
        assert "compute" in tags


class TestMaturityScore:
    def test_high_stars(self):
        score = compute_maturity_score(stars=600, has_docs=True, license_id="MIT")
        assert score >= 45

    def test_zero_everything(self):
        score = compute_maturity_score()
        assert score == 0


class TestSohoRelevance:
    def test_vendor_match(self):
        score = compute_soho_relevance(
            vendors=["fortinet"], domain_tags=["network", "security"]
        )
        assert score >= 65

    def test_no_match(self):
        score = compute_soho_relevance(vendors=[], domain_tags=[])
        assert score == 0
