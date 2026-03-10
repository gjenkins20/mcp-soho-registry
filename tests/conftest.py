"""Shared test fixtures."""

import pytest

from mcp_registry.db import RegistryDB
from mcp_registry.models import MCPServer


@pytest.fixture
def db():
    """In-memory database for testing."""
    registry = RegistryDB(":memory:")
    yield registry
    registry.close()


@pytest.fixture
def sample_server():
    """A sample MCPServer for testing."""
    return MCPServer(
        name="fortigate-mcp-server",
        full_name="example/fortigate-mcp-server",
        url="https://github.com/example/fortigate-mcp-server",
        description="MCP server for FortiGate firewall management",
        language="Python",
        stars=42,
        last_commit="2026-03-01",
        tools_count=5,
        tool_names=["get_interfaces", "get_routes", "get_policies", "get_vpn_status", "get_system_info"],
        vendors=["fortinet"],
        domain_tags=["network", "security"],
        maturity_score=65.0,
        soho_relevance=85.0,
        has_tests=True,
        has_docs=True,
        license="MIT",
        readme_text="# FortiGate MCP Server\n\nManage your FortiGate firewall via MCP.\n\n## Usage\n\npip install fortigate-mcp",
        topics=["mcp", "fortigate", "firewall"],
    )


@pytest.fixture
def sample_servers():
    """Multiple sample servers for list/search testing."""
    return [
        MCPServer(
            name="fortigate-mcp",
            full_name="user1/fortigate-mcp",
            url="https://github.com/user1/fortigate-mcp",
            description="FortiGate firewall MCP server",
            stars=100,
            vendors=["fortinet"],
            domain_tags=["network", "security"],
            maturity_score=70,
            soho_relevance=90,
        ),
        MCPServer(
            name="synology-mcp",
            full_name="user2/synology-mcp",
            url="https://github.com/user2/synology-mcp",
            description="Synology NAS MCP server",
            stars=50,
            vendors=["synology"],
            domain_tags=["storage"],
            maturity_score=55,
            soho_relevance=75,
        ),
        MCPServer(
            name="docker-mcp",
            full_name="user3/docker-mcp",
            url="https://github.com/user3/docker-mcp",
            description="Docker container management MCP",
            stars=200,
            vendors=["docker"],
            domain_tags=["compute"],
            maturity_score=80,
            soho_relevance=40,
        ),
    ]
