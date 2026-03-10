"""GitHub API scraper for discovering MCP server repositories."""

from __future__ import annotations

import asyncio
import logging

import httpx

from mcp_registry.config import (
    GITHUB_API_BASE,
    GITHUB_MAX_RESULTS_PER_QUERY,
    GITHUB_PER_PAGE,
    GITHUB_SEARCH_QUERIES,
    MAX_RETRIES,
    RATE_LIMIT_PAUSE_SECONDS,
)
from mcp_registry.models import MCPServer

logger = logging.getLogger(__name__)


async def _search_repos(
    client: httpx.AsyncClient,
    query: str,
    *,
    max_results: int = GITHUB_MAX_RESULTS_PER_QUERY,
) -> list[dict]:
    """Run a single GitHub code search query with pagination."""
    results: list[dict] = []
    page = 1
    per_page = min(GITHUB_PER_PAGE, max_results)

    while len(results) < max_results:
        for attempt in range(MAX_RETRIES):
            resp = await client.get(
                f"{GITHUB_API_BASE}/search/repositories",
                params={
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            if resp.status_code == 403:
                # Rate limited
                remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                if remaining == 0:
                    logger.warning(
                        "Rate limited, pausing %ds", RATE_LIMIT_PAUSE_SECONDS
                    )
                    await asyncio.sleep(RATE_LIMIT_PAUSE_SECONDS)
                    continue
            resp.raise_for_status()
            break
        else:
            logger.error("Failed after %d retries for query: %s", MAX_RETRIES, query)
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        results.extend(items)
        total = data.get("total_count", 0)
        if len(results) >= total or len(results) >= max_results:
            break
        page += 1

    return results[:max_results]


async def discover_repos(
    token: str | None = None,
    queries: list[str] | None = None,
    max_per_query: int = GITHUB_MAX_RESULTS_PER_QUERY,
) -> list[MCPServer]:
    """Discover MCP server repos from GitHub Search API.

    Returns deduplicated list of MCPServer objects with basic metadata.
    """
    if queries is None:
        queries = GITHUB_SEARCH_QUERIES

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen: set[str] = set()
    servers: list[MCPServer] = []

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        for query in queries:
            logger.info("Searching: %s", query)
            items = await _search_repos(client, query, max_results=max_per_query)
            before = len(servers)
            for item in items:
                full_name = item["full_name"]
                if full_name in seen:
                    continue
                seen.add(full_name)
                servers.append(MCPServer.from_github_api(item))
            new = len(servers) - before
            logger.info(
                "Query '%s': %d results, %d new (total: %d)",
                query, len(items), new, len(servers),
            )
            # Small delay between queries to be respectful
            await asyncio.sleep(1)

    logger.info("Total discovered: %d unique repos", len(servers))
    return servers


def discover_repos_sync(
    token: str | None = None,
    queries: list[str] | None = None,
    max_per_query: int = GITHUB_MAX_RESULTS_PER_QUERY,
) -> list[MCPServer]:
    """Synchronous wrapper around discover_repos."""
    return asyncio.run(
        discover_repos(token=token, queries=queries, max_per_query=max_per_query)
    )
