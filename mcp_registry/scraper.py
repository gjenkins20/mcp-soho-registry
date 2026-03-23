"""GitHub Search API scraper — discover MCP server repositories."""

import httpx

SEARCH_QUERIES = [
    "mcp server in:name,description",
    "model context protocol server in:name,description",
    '"mcp" "server" tool in:readme',
]

GITHUB_API = "https://api.github.com"


async def search_github(
    token: str | None = None,
    queries: list[str] | None = None,
    max_pages: int = 3,
) -> list[dict]:
    """Search GitHub for MCP server repositories.

    Returns a deduplicated list of repo metadata dicts.
    """
    queries = queries or SEARCH_QUERIES
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen = set()
    results = []

    async with httpx.AsyncClient(
        base_url=GITHUB_API, headers=headers, timeout=30
    ) as client:
        for query in queries:
            for page in range(1, max_pages + 1):
                resp = await client.get(
                    "/search/repositories",
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 30,
                        "page": page,
                    },
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    break

                for repo in items:
                    full_name = repo["full_name"]
                    if full_name in seen:
                        continue
                    seen.add(full_name)
                    results.append(_extract_metadata(repo))

    return results


def _extract_metadata(repo: dict) -> dict:
    """Extract relevant fields from a GitHub API repo object."""
    return {
        "name": repo["name"],
        "full_name": repo["full_name"],
        "url": repo["html_url"],
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "stars": repo.get("stargazers_count", 0),
        "last_commit": repo.get("pushed_at", ""),
        "license": (repo.get("license") or {}).get("spdx_id", ""),
        "has_docs": bool(repo.get("description")),
    }
