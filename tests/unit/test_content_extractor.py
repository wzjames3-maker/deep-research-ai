"""Unit tests for src.services.content_extractor.

Tests cover:
- Successful extraction from HTML
- Extraction failure fallback to snippet
- Concurrency limiting
- Content truncation to max_chars
- Empty results list handling
- Feature flag disable
- extract_node integration with sub_agent_graph
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.mcp_client import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(url: str = "https://example.com", title: str = "Test", snippet: str = "snippet") -> SearchResult:
    return SearchResult(url=url, title=title, snippet=snippet)


SAMPLE_HTML = """
<html><head><title>Test Page</title></head>
<body>
<article>
<h1>Important Research Finding</h1>
<p>This is a comprehensive paragraph with enough text to pass the minimum
length threshold that trafilatura requires for extraction. It contains
important data points and factual information about the research topic
that would be very useful for the LLM to analyze in depth.</p>
<p>Another paragraph with additional context and details that further
enrich the content available for analysis by the research agent system.</p>
</article>
</body></html>
"""


# ---------------------------------------------------------------------------
# Unit tests for extract_urls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_urls_success():
    """Successful extraction should populate extracted_content."""
    from src.services.content_extractor import extract_urls

    results = [_make_result()]

    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("src.services.content_extractor.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client

        extraction_results = await extract_urls(results, max_concurrent=2, timeout=5, max_chars=8000)

    assert len(extraction_results) == 1
    assert extraction_results[0].content is not None
    assert results[0].extracted_content != ""
    assert "Important Research Finding" in results[0].extracted_content


@pytest.mark.asyncio
async def test_extract_urls_http_failure():
    """HTTP failure should leave extracted_content empty, not raise."""
    from src.services.content_extractor import extract_urls

    results = [_make_result()]

    with patch("src.services.content_extractor.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("403 Forbidden"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client

        extraction_results = await extract_urls(results, max_concurrent=2, timeout=5, max_chars=8000)

    assert len(extraction_results) == 1
    assert extraction_results[0].content is None
    assert extraction_results[0].error is not None
    assert results[0].extracted_content == ""  # unchanged


@pytest.mark.asyncio
async def test_extract_urls_truncation():
    """Content exceeding max_chars should be truncated."""
    from src.services.content_extractor import extract_urls

    results = [_make_result()]
    # Build HTML with lots of text
    long_text = "This is a sentence with enough words. " * 200
    long_html = f"<html><body><article><p>{long_text}</p></article></body></html>"

    mock_response = MagicMock()
    mock_response.text = long_html
    mock_response.raise_for_status = MagicMock()

    with patch("src.services.content_extractor.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client

        extraction_results = await extract_urls(results, max_concurrent=2, timeout=5, max_chars=200)

    assert len(extraction_results) == 1
    assert extraction_results[0].content is not None
    assert len(extraction_results[0].content) <= 200


@pytest.mark.asyncio
async def test_extract_urls_empty_list():
    """Empty results list should return immediately."""
    from src.services.content_extractor import extract_urls

    extraction_results = await extract_urls([])
    assert extraction_results == []


@pytest.mark.asyncio
async def test_extract_urls_multiple():
    """Multiple URLs should all be processed."""
    from src.services.content_extractor import extract_urls

    results = [
        _make_result(url="https://a.com", title="A"),
        _make_result(url="https://b.com", title="B"),
        _make_result(url="https://c.com", title="C"),
    ]

    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("src.services.content_extractor.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client

        extraction_results = await extract_urls(results, max_concurrent=5, timeout=5, max_chars=8000)

    assert len(extraction_results) == 3
    assert all(r.content is not None for r in extraction_results)
    assert all(r.extracted_content != "" for r in results)


# ---------------------------------------------------------------------------
# Integration tests for extract_node in sub_agent_graph
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_node_skips_with_mock_llm():
    """extract_node should be a no-op when _llm_service_override is set (tests)."""
    from src.services.sub_agent_graph import extract_node, _llm_service_override  # noqa: F401

    # When using mock LLM (tests), extract_node should return {}
    # We need to temporarily set the override
    import src.services.sub_agent_graph as sag
    original = sag._llm_service_override
    sag._llm_service_override = MagicMock()

    try:
        result = await extract_node(
            {
                "research_id": "test-id",
                "search_results": [_make_result()],
                "topic": "test",
                "search_direction": "test",
                "visited_urls": [],
                "findings": "",
                "rounds_completed": 0,
                "sufficient": False,
                "token_used": 0,
                "status": "running",
                "has_error": False,
                "agent_def": {"name": "test"},
                "filter_tokens": 0,
            },
            MagicMock(),
        )
        assert result == {}
    finally:
        sag._llm_service_override = original
