"""Data models for MCP server records."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MCPServer:
    """Represents a discovered MCP server."""

    name: str
    full_name: str  # owner/repo
    url: str
    description: str = ""
    language: str = ""
    stars: int = 0
    last_commit: str = ""  # ISO 8601 date
    tools_count: int = 0
    tool_names: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)
    domain_tags: list[str] = field(default_factory=list)
    maturity_score: float = 0.0
    soho_relevance: float = 0.0
    has_tests: bool = False
    has_docs: bool = False
    license: str = ""
    readme_text: str = ""  # transient, not stored in DB
    topics: list[str] = field(default_factory=list)  # GitHub topics, transient
    discovered_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        if not self.discovered_at:
            self.discovered_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_db_row(self) -> dict:
        """Convert to a dict suitable for SQLite insertion."""
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "description": self.description,
            "language": self.language,
            "stars": self.stars,
            "last_commit": self.last_commit,
            "tools_count": self.tools_count,
            "tool_names_json": json.dumps(self.tool_names),
            "vendors_json": json.dumps(self.vendors),
            "domain_tags_json": json.dumps(self.domain_tags),
            "maturity_score": self.maturity_score,
            "soho_relevance": self.soho_relevance,
            "has_tests": int(self.has_tests),
            "has_docs": int(self.has_docs),
            "license": self.license,
            "discovered_at": self.discovered_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> MCPServer:
        """Create an MCPServer from a database row dict."""
        return cls(
            name=row["name"],
            full_name=row["full_name"],
            url=row["url"],
            description=row["description"] or "",
            language=row["language"] or "",
            stars=row["stars"],
            last_commit=row["last_commit"] or "",
            tools_count=row["tools_count"],
            tool_names=json.loads(row["tool_names_json"] or "[]"),
            vendors=json.loads(row["vendors_json"] or "[]"),
            domain_tags=json.loads(row["domain_tags_json"] or "[]"),
            maturity_score=row["maturity_score"],
            soho_relevance=row["soho_relevance"],
            has_tests=bool(row["has_tests"]),
            has_docs=bool(row["has_docs"]),
            license=row["license"] or "",
            discovered_at=row["discovered_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def from_github_api(cls, item: dict) -> MCPServer:
        """Create an MCPServer from a GitHub Search API result item."""
        return cls(
            name=item["name"],
            full_name=item["full_name"],
            url=item["html_url"],
            description=item.get("description") or "",
            language=item.get("language") or "",
            stars=item.get("stargazers_count", 0),
            last_commit=item.get("pushed_at", "")[:10],  # date only
            license=(item.get("license") or {}).get("spdx_id", ""),
            topics=item.get("topics", []),
        )
