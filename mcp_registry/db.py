"""SQLite database layer for the MCP server registry."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcp_registry.models import MCPServer

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    full_name TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    stars INTEGER DEFAULT 0,
    last_commit TEXT,
    tools_count INTEGER DEFAULT 0,
    tool_names_json TEXT,
    vendors_json TEXT,
    domain_tags_json TEXT,
    maturity_score REAL DEFAULT 0,
    soho_relevance REAL DEFAULT 0,
    has_tests INTEGER DEFAULT 0,
    has_docs INTEGER DEFAULT 0,
    license TEXT,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS server_tools (
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    PRIMARY KEY (server_id, tool_name)
);

CREATE TABLE IF NOT EXISTS server_tags (
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (server_id, tag)
);

CREATE TABLE IF NOT EXISTS server_vendors (
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    vendor TEXT NOT NULL,
    PRIMARY KEY (server_id, vendor)
);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS servers_fts USING fts5(
    name, full_name, description, tool_names_json, vendors_json, domain_tags_json,
    content='servers', content_rowid='id'
);
"""


class RegistryDB:
    """Manages the SQLite registry database."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.executescript(FTS_SQL)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_server(self, server: MCPServer) -> int:
        """Insert or update a server record. Returns the row id."""
        row = server.to_db_row()
        cur = self.conn.execute(
            """
            INSERT INTO servers (
                name, full_name, url, description, language, stars,
                last_commit, tools_count, tool_names_json, vendors_json,
                domain_tags_json, maturity_score, soho_relevance,
                has_tests, has_docs, license, discovered_at, updated_at
            ) VALUES (
                :name, :full_name, :url, :description, :language, :stars,
                :last_commit, :tools_count, :tool_names_json, :vendors_json,
                :domain_tags_json, :maturity_score, :soho_relevance,
                :has_tests, :has_docs, :license, :discovered_at, :updated_at
            )
            ON CONFLICT(full_name) DO UPDATE SET
                name=excluded.name, url=excluded.url,
                description=excluded.description, language=excluded.language,
                stars=excluded.stars, last_commit=excluded.last_commit,
                tools_count=excluded.tools_count,
                tool_names_json=excluded.tool_names_json,
                vendors_json=excluded.vendors_json,
                domain_tags_json=excluded.domain_tags_json,
                maturity_score=excluded.maturity_score,
                soho_relevance=excluded.soho_relevance,
                has_tests=excluded.has_tests, has_docs=excluded.has_docs,
                license=excluded.license, updated_at=excluded.updated_at
            """,
            row,
        )
        server_id = cur.lastrowid
        assert server_id is not None

        # Update junction tables
        self.conn.execute(
            "DELETE FROM server_tools WHERE server_id=?", (server_id,)
        )
        self.conn.execute(
            "DELETE FROM server_tags WHERE server_id=?", (server_id,)
        )
        self.conn.execute(
            "DELETE FROM server_vendors WHERE server_id=?", (server_id,)
        )
        for tool in server.tool_names:
            self.conn.execute(
                "INSERT OR IGNORE INTO server_tools VALUES (?, ?)",
                (server_id, tool),
            )
        for tag in server.domain_tags:
            self.conn.execute(
                "INSERT OR IGNORE INTO server_tags VALUES (?, ?)",
                (server_id, tag),
            )
        for vendor in server.vendors:
            self.conn.execute(
                "INSERT OR IGNORE INTO server_vendors VALUES (?, ?)",
                (server_id, vendor),
            )
        self.conn.commit()
        return server_id

    def rebuild_fts(self) -> None:
        """Rebuild the full-text search index."""
        self.conn.execute(
            "INSERT INTO servers_fts(servers_fts) VALUES('rebuild')"
        )
        self.conn.commit()

    def get_server(self, full_name: str) -> MCPServer | None:
        """Fetch a single server by owner/repo."""
        cur = self.conn.execute(
            "SELECT * FROM servers WHERE full_name=?", (full_name,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return MCPServer.from_db_row(dict(row))

    def list_servers(
        self,
        *,
        domain: str | None = None,
        vendor: str | None = None,
        min_maturity: float = 0,
        min_soho: float = 0,
        sort_by: str = "soho_relevance",
        limit: int = 50,
    ) -> list[MCPServer]:
        """List servers with optional filters."""
        query = "SELECT s.* FROM servers s"
        conditions: list[str] = []
        params: list = []

        if domain:
            query += " JOIN server_tags st ON s.id = st.server_id"
            conditions.append("st.tag = ?")
            params.append(domain)
        if vendor:
            query += " JOIN server_vendors sv ON s.id = sv.server_id"
            conditions.append("sv.vendor = ?")
            params.append(vendor)
        if min_maturity > 0:
            conditions.append("s.maturity_score >= ?")
            params.append(min_maturity)
        if min_soho > 0:
            conditions.append("s.soho_relevance >= ?")
            params.append(min_soho)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Validate sort column
        allowed_sorts = {
            "soho_relevance", "maturity_score", "stars", "name", "last_commit",
        }
        if sort_by not in allowed_sorts:
            sort_by = "soho_relevance"
        query += f" ORDER BY s.{sort_by} DESC LIMIT ?"
        params.append(limit)

        cur = self.conn.execute(query, params)
        return [MCPServer.from_db_row(dict(row)) for row in cur.fetchall()]

    def search_servers(self, query: str, limit: int = 20) -> list[MCPServer]:
        """Full-text search across server metadata."""
        cur = self.conn.execute(
            """
            SELECT s.* FROM servers_fts fts
            JOIN servers s ON fts.rowid = s.id
            WHERE servers_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [MCPServer.from_db_row(dict(row)) for row in cur.fetchall()]

    def get_stats(self) -> dict:
        """Return summary statistics."""
        cur = self.conn.execute("SELECT COUNT(*) as total FROM servers")
        total = cur.fetchone()["total"]
        cur = self.conn.execute(
            "SELECT COUNT(DISTINCT tag) as tags FROM server_tags"
        )
        tags = cur.fetchone()["tags"]
        cur = self.conn.execute(
            "SELECT COUNT(DISTINCT vendor) as vendors FROM server_vendors"
        )
        vendors = cur.fetchone()["vendors"]
        return {"total_servers": total, "unique_tags": tags, "unique_vendors": vendors}
