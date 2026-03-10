"""Tests for the database layer."""

from mcp_registry.db import RegistryDB
from mcp_registry.models import MCPServer


class TestRegistryDB:
    def test_upsert_and_get(self, db, sample_server):
        db.upsert_server(sample_server)
        result = db.get_server("example/fortigate-mcp-server")
        assert result is not None
        assert result.name == "fortigate-mcp-server"
        assert result.stars == 42
        assert sorted(result.tool_names) == [
            "get_interfaces", "get_policies", "get_routes",
            "get_system_info", "get_vpn_status",
        ]
        assert result.vendors == ["fortinet"]
        assert result.domain_tags == ["network", "security"]

    def test_upsert_updates_existing(self, db, sample_server):
        db.upsert_server(sample_server)
        sample_server.stars = 100
        sample_server.tool_names = ["new_tool"]
        db.upsert_server(sample_server)
        result = db.get_server("example/fortigate-mcp-server")
        assert result.stars == 100
        assert result.tool_names == ["new_tool"]

    def test_get_nonexistent(self, db):
        assert db.get_server("nonexistent/repo") is None

    def test_list_servers(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        results = db.list_servers()
        assert len(results) == 3

    def test_list_filter_by_domain(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        results = db.list_servers(domain="network")
        assert len(results) == 1
        assert results[0].full_name == "user1/fortigate-mcp"

    def test_list_filter_by_vendor(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        results = db.list_servers(vendor="synology")
        assert len(results) == 1
        assert results[0].full_name == "user2/synology-mcp"

    def test_list_min_maturity(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        results = db.list_servers(min_maturity=60)
        assert all(s.maturity_score >= 60 for s in results)

    def test_list_sort_by_stars(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        results = db.list_servers(sort_by="stars")
        assert results[0].stars >= results[-1].stars

    def test_search(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        db.rebuild_fts()
        results = db.search_servers("fortigate")
        assert len(results) >= 1
        assert results[0].full_name == "user1/fortigate-mcp"

    def test_stats(self, db, sample_servers):
        for s in sample_servers:
            db.upsert_server(s)
        stats = db.get_stats()
        assert stats["total_servers"] == 3
        assert stats["unique_vendors"] >= 1
        assert stats["unique_tags"] >= 1
