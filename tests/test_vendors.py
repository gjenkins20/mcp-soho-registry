"""Tests for vendor detection."""

from mcp_registry.models import MCPServer
from mcp_registry.vendors import detect_vendors


class TestVendorDetection:
    def test_detect_from_name(self):
        s = MCPServer(name="fortigate-mcp", full_name="x/fortigate-mcp", url="")
        vendors = detect_vendors(s)
        assert "fortinet" in vendors

    def test_detect_from_description(self):
        s = MCPServer(
            name="some-mcp", full_name="x/some-mcp", url="",
            description="MCP server for Synology DiskStation",
        )
        vendors = detect_vendors(s)
        assert "synology" in vendors

    def test_detect_from_readme(self):
        s = MCPServer(
            name="mcp-net", full_name="x/mcp-net", url="",
            readme_text="Works with UniFi network controllers.",
        )
        vendors = detect_vendors(s)
        assert "ubiquiti" in vendors

    def test_detect_multiple_vendors(self):
        s = MCPServer(
            name="home-mcp", full_name="x/home-mcp", url="",
            description="Manage Docker containers on Raspberry Pi",
        )
        vendors = detect_vendors(s)
        assert "docker" in vendors
        assert "raspberry-pi" in vendors

    def test_no_vendors(self):
        s = MCPServer(
            name="weather-mcp", full_name="x/weather-mcp", url="",
            description="Get weather forecasts",
        )
        vendors = detect_vendors(s)
        assert vendors == []
