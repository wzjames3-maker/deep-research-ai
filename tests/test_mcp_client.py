import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.mcp_client import (
    SearchResult,
    MCPSearchClient,
    _normalize_url,
    _parse_search_results,
)


class TestUrlNormalization:
    def test_removes_query_string(self):
        assert _normalize_url("https://example.com/page?a=1") == "https://example.com/page"

    def test_removes_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_http_scheme(self):
        assert _normalize_url("http://example.com") == "http://example.com/"

    def test_preserves_domain_case(self):
        assert _normalize_url("https://Example.COM/Path?q=1") == "https://example.com/Path"

    def test_hash_fragment(self):
        assert _normalize_url("https://example.com/page#section") == "https://example.com/page"


class TestSearchResultParsing:
    def test_parse_brave_web_results(self):
        mock_result = MagicMock()
        item = MagicMock()
        item.text = '{"web": {"results": [{"url": "https://a.com", "title": "A", "description": "DescA"}]}}'
        mock_result.content = [item]

        results = _parse_search_results(mock_result)
        assert len(results) == 1
        assert results[0].url == "https://a.com"
        assert results[0].title == "A"
        assert results[0].snippet == "DescA"

    def test_parse_empty_results(self):
        mock_result = MagicMock()
        item = MagicMock()
        item.text = '{"web": {"results": []}}'
        mock_result.content = [item]

        results = _parse_search_results(mock_result)
        assert results == []

    def test_parse_invalid_json(self):
        mock_result = MagicMock()
        item = MagicMock()
        item.text = "not json"
        mock_result.content = [item]

        results = _parse_search_results(mock_result)
        assert results == []


class TestMCPSearchClient:
    @pytest.fixture
    def client(self):
        return MCPSearchClient(mcp_endpoint="http://test:3000")

    @pytest.mark.asyncio
    async def test_search_multi_round_dedup(self, client):
        mock_results = [
            [SearchResult(url="https://a.com", title="A", snippet="S1")],
            [SearchResult(url="https://a.com", title="A", snippet="S1"),
             SearchResult(url="https://b.com", title="B", snippet="S2")],
        ]
        call_count = [0]

        async def mock_search(query, *args, **kwargs):
            result = mock_results[call_count[0]]
            call_count[0] += 1
            return result

        with patch.object(client, "search", side_effect=mock_search):
            rounds = await client.search_multi_round(
                directions=["query1", "query2"],
                existing_urls=set(),
                max_rounds=2,
            )

            assert len(rounds) == 2
            assert len(rounds[0]) == 1
            assert len(rounds[1]) == 1
            assert rounds[1][0].url == "https://b.com"

    @pytest.mark.asyncio
    async def test_search_multi_round_respects_existing_urls(self, client):
        mock_results = [
            [SearchResult(url="https://a.com", title="A", snippet="S1")]
        ]

        with patch.object(client, "search", return_value=mock_results[0]):
            rounds = await client.search_multi_round(
                directions=["query1"],
                existing_urls={"https://a.com"},
                max_rounds=1,
            )

            assert len(rounds[0]) == 0

    @pytest.mark.asyncio
    async def test_search_multi_round_empty_directions(self, client):
        with patch.object(client, "search", new_callable=AsyncMock) as mock:
            rounds = await client.search_multi_round(
                directions=[],
                existing_urls=set(),
                max_rounds=2,
            )
            assert len(rounds) == 0
            mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_url_dedup_normalizes(self, client):
        mock_results = [
            [SearchResult(url="https://a.com/page?q=1", title="T", snippet="S")],
            [SearchResult(url="https://a.com/page", title="T", snippet="S")],
        ]
        call_count = [0]

        async def mock_search(query, *args, **kwargs):
            result = [mock_results[call_count[0]]]
            call_count[0] += 1
            return result[0]

        with patch.object(client, "search", side_effect=mock_search):
            rounds = await client.search_multi_round(
                directions=["q1", "q2"],
                existing_urls=set(),
                max_rounds=2,
            )
            assert len(rounds[0]) == 1
            assert len(rounds[1]) == 0
