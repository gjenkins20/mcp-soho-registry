"""SQLite registry database — schema and CRUD operations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "registry.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS servers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    full_name       TEXT NOT NULL UNIQUE,
    url             TEXT NOT NULL,
    description     TEXT DEFAULT '',
    language        TEXT DEFAULT '',
    stars           INTEGER DEFAULT 0,
    last_commit     TEXT DEFAULT '',
    tools_count     INTEGER DEFAULT 0,
    tool_names      TEXT DEFAULT '[]',
    vendors         TEXT DEFAULT '[]',
    domain_tags     TEXT DEFAULT '[]',
    maturity_score  REAL DEFAULT 0.0,
    soho_relevance  REAL DEFAULT 0.0,
    has_tests       INTEGER DEFAULT 0,
    has_docs        INTEGER DEFAULT 0,
    license         TEXT DEFAULT '',
    discovered_at   TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_servers_full_name ON servers(full_name);
CREATE INDEX IF NOT EXISTS idx_servers_maturity ON servers(maturity_score DESC);
CREATE INDEX IF NOT EXISTS idx_servers_soho ON servers(soho_relevance DESC);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection and ensure the schema exists."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_server(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or update an MCP server record."""
    now = datetime.now(timezone.utc).isoformat()
    data.setdefault("discovered_at", now)
    data["updated_at"] = now

    # Serialize list/dict fields to JSON
    for field in ("tool_names", "vendors", "domain_tags"):
        if isinstance(data.get(field), (list, dict)):
            data[field] = json.dumps(data[field])

    conn.execute(
        """
        INSERT INTO servers (
            name, full_name, url, description, language, stars,
            last_commit, tools_count, tool_names, vendors, domain_tags,
            maturity_score, soho_relevance, has_tests, has_docs, license,
            discovered_at, updated_at
        ) VALUES (
            :name, :full_name, :url, :description, :language, :stars,
            :last_commit, :tools_count, :tool_names, :vendors, :domain_tags,
            :maturity_score, :soho_relevance, :has_tests, :has_docs, :license,
            :discovered_at, :updated_at
        )
        ON CONFLICT(full_name) DO UPDATE SET
            name=excluded.name, url=excluded.url,
            description=excluded.description, language=excluded.language,
            stars=excluded.stars, last_commit=excluded.last_commit,
            tools_count=excluded.tools_count, tool_names=excluded.tool_names,
            vendors=excluded.vendors, domain_tags=excluded.domain_tags,
            maturity_score=excluded.maturity_score,
            soho_relevance=excluded.soho_relevance,
            has_tests=excluded.has_tests, has_docs=excluded.has_docs,
            license=excluded.license, updated_at=excluded.updated_at
        """,
        data,
    )
    conn.commit()


def search_servers(
    conn: sqlite3.Connection,
    query: str | None = None,
    vendor: str | None = None,
    domain: str | None = None,
    min_maturity: float = 0,
    min_soho: float = 0,
    limit: int = 50,
) -> list[sqlite3.Row]:
    """Search and filter registry entries."""
    clauses = ["maturity_score >= ?", "soho_relevance >= ?"]
    params: list = [min_maturity, min_soho]

    if query:
        clauses.append("(name LIKE ? OR description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if vendor:
        clauses.append("vendors LIKE ?")
        params.append(f'%"{vendor}"%')
    if domain:
        clauses.append("domain_tags LIKE ?")
        params.append(f'%"{domain}"%')

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM servers WHERE {where} "
        f"ORDER BY soho_relevance DESC, maturity_score DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    return rows
