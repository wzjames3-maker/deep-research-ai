"""Content extraction service for fetching full page text from URLs.

Uses trafilatura for HTML → text extraction with:
- Async HTTP fetching via httpx
- Concurrency control via asyncio.Semaphore
- Graceful fallback to original snippet on failure
"""

import asyncio
import time
from dataclasses import dataclass

import httpx
import structlog

from src.config import settings
from src.services.mcp_client import SearchResult

logger = structlog.get_logger()

# Browser-like User-Agent to reduce blocking
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


@dataclass
class ExtractionResult:
    url: str
    content: str | None  # None = extraction failed
    error: str | None = None


async def _fetch_html(url: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> tuple[str, str | None]:
    """Fetch HTML for a single URL. Returns (html, error_or_none)."""
    async with semaphore:
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            return resp.text, None
        except Exception as e:
            return "", str(e)


def _extract_text(html: str) -> str | None:
    """Extract main text from HTML using trafilatura. Returns None on failure."""
    try:
        import trafilatura
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        if text and len(text.strip()) > 50:
            return text.strip()
        return None
    except Exception:
        return None


async def extract_urls(
    results: list[SearchResult],
    max_concurrent: int | None = None,
    timeout: float | None = None,
    max_chars: int | None = None,
) -> list[ExtractionResult]:
    """Extract full page text for a list of SearchResult items.

    Modifies each SearchResult's `extracted_content` field in-place.
    Returns a list of ExtractionResult for logging/monitoring.

    Args:
        results: Search results to extract content from
        max_concurrent: Max parallel fetches (default from config)
        timeout: Per-request timeout in seconds (default from config)
        max_chars: Max characters to keep per page (default from config)

    Returns:
        List of ExtractionResult
    """
    if not results:
        return []

    max_concurrent = max_concurrent or settings.CONTENT_FETCH_MAX_CONCURRENT
    timeout = timeout or settings.CONTENT_FETCH_TIMEOUT
    max_chars = max_chars or settings.CONTENT_FETCH_MAX_CHARS
    semaphore = asyncio.Semaphore(max_concurrent)

    start = time.time()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=max_concurrent + 2),
    ) as client:
        # Fetch all HTML concurrently
        html_tasks = [_fetch_html(r.url, client, semaphore) for r in results]
        html_results = await asyncio.gather(*html_tasks)

    # Extract text from each HTML (CPU-bound, but fast enough)
    extraction_results: list[ExtractionResult] = []
    success_count = 0
    fail_count = 0

    for search_result, (html, fetch_error) in zip(results, html_results):
        if fetch_error:
            extraction_results.append(ExtractionResult(
                url=search_result.url, content=None, error=fetch_error,
            ))
            fail_count += 1
            continue

        text = _extract_text(html)
        if text is None:
            extraction_results.append(ExtractionResult(
                url=search_result.url, content=None, error="trafilatura_extract_empty",
            ))
            fail_count += 1
            continue

        # Truncate to max_chars
        truncated = text[:max_chars] if len(text) > max_chars else text
        search_result.extracted_content = truncated
        extraction_results.append(ExtractionResult(
            url=search_result.url, content=truncated,
        ))
        success_count += 1

    duration_ms = (time.time() - start) * 1000
    logger.info(
        "content_extraction_complete",
        total=len(results),
        success=success_count,
        failed=fail_count,
        duration_ms=round(duration_ms, 2),
    )

    return extraction_results
