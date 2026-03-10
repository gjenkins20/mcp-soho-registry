"""Configuration constants and helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Default database location (next to the package root)
DEFAULT_DB_PATH = Path("registry.db")

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_QUERIES = [
    "mcp server",
    "model context protocol server",
    "mcp-server",
    "topic:mcp-server",
    "topic:model-context-protocol",
]
GITHUB_PER_PAGE = 100
GITHUB_MAX_RESULTS_PER_QUERY = 1000

# Rate limiting
RATE_LIMIT_PAUSE_SECONDS = 5
MAX_RETRIES = 3


def get_github_token() -> str | None:
    """Resolve GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_db_path() -> Path:
    """Resolve database path from environment or default."""
    env_path = os.environ.get("MCP_REGISTRY_DB")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH
