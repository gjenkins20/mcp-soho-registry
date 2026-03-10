"""Tests for the scoring engine."""

from mcp_registry.models import MCPServer
from mcp_registry.scorer import score_maturity, score_soho_relevance


class TestMaturityScorer:
    def test_high_maturity(self):
        s = MCPServer(
            name="mature-mcp", full_name="x/mature-mcp", url="",
            stars=600, last_commit="2026-03-08",
            has_tests=True, has_docs=True, license="MIT",
        )
        score = score_maturity(s)
        assert score >= 80

    def test_low_maturity(self):
        s = MCPServer(
            name="new-mcp", full_name="x/new-mcp", url="",
            stars=2, last_commit="2024-01-01",
            has_tests=False, has_docs=False, license="",
        )
        score = score_maturity(s)
        assert score <= 20

    def test_medium_maturity(self):
        s = MCPServer(
            name="mid-mcp", full_name="x/mid-mcp", url="",
            stars=50, last_commit="2026-02-01",
            has_tests=True, has_docs=False, license="Apache-2.0",
            description="A useful tool",
        )
        score = score_maturity(s)
        assert 30 <= score <= 75

    def test_score_capped_at_100(self):
        s = MCPServer(
            name="super-mcp", full_name="x/super-mcp", url="",
            stars=1000, last_commit="2026-03-09",
            has_tests=True, has_docs=True, license="MIT",
        )
        score = score_maturity(s)
        assert score <= 100


class TestSOHORelevanceScorer:
    def test_high_soho_relevance(self):
        s = MCPServer(
            name="fortigate-mcp", full_name="x/fortigate-mcp", url="",
            description="FortiGate firewall management with pip install",
            vendors=["fortinet"],
            domain_tags=["network", "security"],
            readme_text="pip install fortigate-mcp",
        )
        score = score_soho_relevance(s)
        assert score >= 80

    def test_low_soho_relevance(self):
        s = MCPServer(
            name="cloud-ai-mcp", full_name="x/cloud-ai-mcp", url="",
            description="Cloud AI model serving on AWS Lambda with GPU",
            vendors=[],
            domain_tags=[],
            readme_text="Requires NVIDIA GPU and AWS Lambda deployment",
        )
        score = score_soho_relevance(s)
        assert score <= 25

    def test_generic_vendor_moderate_relevance(self):
        s = MCPServer(
            name="docker-mcp", full_name="x/docker-mcp", url="",
            description="Docker container management",
            vendors=["docker"],
            domain_tags=["compute"],
            readme_text="pip install docker-mcp",
        )
        score = score_soho_relevance(s)
        assert 30 <= score <= 70
