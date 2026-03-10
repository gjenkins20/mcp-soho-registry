"""Tool name extraction from MCP server repositories."""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

from mcp_registry.models import MCPServer

logger = logging.getLogger(__name__)

# Patterns for MCP tool registration across languages
# Ordered from most specific to least specific
TOOL_PATTERNS = [
    # Python: @mcp.tool(), @server.tool(), @app.tool() with name kwarg
    re.compile(r'@\w+\.tool\(\s*(?:name\s*=\s*)?["\'](\w+)["\']'),
    # Python: @mcp.tool() with function name as tool name
    re.compile(r'@\w+\.tool\(\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)'),
    # Python: Tool(name="...") or types.Tool(name="...")
    re.compile(r'(?:types\.)?Tool\(\s*name\s*=\s*["\'](\w[\w-]*)["\']'),
    # TypeScript: server.tool("name", ...) — must have .tool( prefix
    re.compile(r'\.tool\(\s*["\'](\w[\w-]*)["\']'),
]

# Directories to skip during extraction
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
}

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".ts", ".js", ".mjs"}


def _shallow_clone(repo_url: str, dest: Path) -> bool:
    """Shallow-clone a repo. Returns True on success."""
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", repo_url, str(dest)],
            capture_output=True,
            timeout=60,
        )
        return dest.exists() and (dest / ".git").exists()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.warning("Clone failed for %s: %s", repo_url, e)
        return False


def _scan_file_for_tools(filepath: Path) -> list[str]:
    """Extract tool names from a single source file."""
    try:
        text = filepath.read_text(errors="ignore")
    except OSError:
        return []

    tools: list[str] = []
    for pattern in TOOL_PATTERNS:
        tools.extend(pattern.findall(text))
    return tools


def _detect_tests(repo_path: Path) -> bool:
    """Check if the repo has a test suite."""
    test_indicators = [
        "tests/", "test/", "test_", "_test.py", ".test.ts", ".test.js",
        "spec/", ".spec.ts", ".spec.js", "pytest.ini", "jest.config",
    ]
    for path in repo_path.rglob("*"):
        if any(indicator in str(path) for indicator in test_indicators):
            return True
    return False


def _detect_docs(repo_path: Path) -> bool:
    """Check if the repo has documentation beyond a basic README."""
    readme = repo_path / "README.md"
    if not readme.exists():
        readme = repo_path / "readme.md"
    if not readme.exists():
        return False

    # A README with usage examples counts as docs
    try:
        text = readme.read_text(errors="ignore")
        has_examples = any(
            keyword in text.lower()
            for keyword in ["usage", "example", "getting started", "installation", "setup"]
        )
        return len(text) > 500 and has_examples
    except OSError:
        return False


def _read_readme(repo_path: Path) -> str:
    """Read the README content for downstream analysis."""
    for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        readme = repo_path / name
        if readme.exists():
            try:
                return readme.read_text(errors="ignore")[:10000]  # cap at 10KB
            except OSError:
                pass
    return ""


def extract_metadata(server: MCPServer) -> MCPServer:
    """Clone a repo and extract tool names, test/doc status, and README.

    Modifies the server object in place and returns it.
    """
    with tempfile.TemporaryDirectory(prefix="mcp-extract-") as tmpdir:
        dest = Path(tmpdir) / server.name
        if not _shallow_clone(server.url, dest):
            logger.warning("Skipping extraction for %s", server.full_name)
            server.tools_count = -1  # indicates extraction failure
            return server

        # Extract tool names
        all_tools: set[str] = set()
        for root, dirs, files in dest.walk():
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                fpath = root / fname
                if fpath.suffix in SCAN_EXTENSIONS:
                    tools = _scan_file_for_tools(fpath)
                    all_tools.update(tools)

        # Filter out common false positives
        false_positives = {
            "name", "type", "description", "input", "output", "test",
            "tool", "tools", "string", "object", "array", "boolean",
            "required", "properties", "schema", "title", "default",
            "config", "options", "value", "result", "error", "data",
            "id", "key", "path", "url", "uri", "method", "action",
            "main", "init", "setup", "run", "start", "stop", "close",
        }
        all_tools -= false_positives

        server.tool_names = sorted(all_tools)
        server.tools_count = len(all_tools)
        server.has_tests = _detect_tests(dest)
        server.has_docs = _detect_docs(dest)
        server.readme_text = _read_readme(dest)

    return server
