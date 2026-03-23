"""Tests for the database layer."""

import sqlite3
from pathlib import Path

from mcp_registry.db import get_connection, search_servers, upsert_server


def _make_server(**overrides) -> dict:
    defaults = {
        "name": "test-mcp",
        "full_name": "user/test-mcp",
        "url": "https://github.com/user/test-mcp",
        "description": "A test MCP server",
        "language": "Python",
        "stars": 42,
        "last_commit": "2026-03-01",
        "tools_count": 3,
        "tool_names": ["tool_a", "tool_b", "tool_c"],
        "vendors": ["fortinet"],
        "domain_tags": ["network", "security"],
        "maturity_score": 55.0,
        "soho_relevance": 65.0,
        "has_tests": True,
        "has_docs": True,
        "license": "MIT",
    }
    defaults.update(overrides)
    return defaults


class TestDatabase:
    def test_upsert_and_search(self, tmp_path: Path):
        conn = get_connection(tmp_path / "test.db")
        upsert_server(conn, _make_server())

        rows = search_servers(conn)
        assert len(rows) == 1
        assert rows[0]["full_name"] == "user/test-mcp"

    def test_upsert_updates_existing(self, tmp_path: Path):
        conn = get_connection(tmp_path / "test.db")
        upsert_server(conn, _make_server(stars=10))
        upsert_server(conn, _make_server(stars=99))

        rows = search_servers(conn)
        assert len(rows) == 1
        assert rows[0]["stars"] == 99

    def test_search_by_query(self, tmp_path: Path):
        conn = get_connection(tmp_path / "test.db")
        upsert_server(conn, _make_server(full_name="a/fortigate-mcp", name="fortigate-mcp"))
        upsert_server(conn, _make_server(full_name="b/generic-tool", name="generic-tool"))

        rows = search_servers(conn, query="fortigate")
        assert len(rows) == 1

    def test_filter_by_min_scores(self, tmp_path: Path):
        conn = get_connection(tmp_path / "test.db")
        upsert_server(conn, _make_server(full_name="a/high", maturity_score=80, soho_relevance=70))
        upsert_server(conn, _make_server(full_name="b/low", maturity_score=10, soho_relevance=5))

        rows = search_servers(conn, min_maturity=50, min_soho=50)
        assert len(rows) == 1
        assert rows[0]["full_name"] == "a/high"
