import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
import structlog
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from mcp.types import CallToolResult

from src.config import settings

logger = structlog.get_logger()


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    extracted_content: str = ""  # Full page text from content extractor


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", "", ""))


class MCPSearchClient:
    def __init__(self, mcp_endpoint: str):
        self.mcp_endpoint = mcp_endpoint

    async def _call_brave_tool(
        self, query: str, max_results: int = 5, max_retries: int = 2
    ) -> list[SearchResult]:
        import asyncio

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                async with streamablehttp_client(self.mcp_endpoint) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        result = await session.call_tool(
                            "brave_search",
                            arguments={"query": query, "count": max_results},
                        )

                        return _parse_search_results(result)
            except Exception as e:
                last_error = e
                logger.warning(
                    "mcp_brave_retry",
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(e),
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * attempt)  # 简单退避

        raise last_error  # type: ignore[misc]

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        start = time.time()
        try:
            results = await self._call_brave_tool(query, max_results)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.warning("mcp_search_brave_failed", error=str(e), duration_ms=round(duration_ms, 2))

            if settings.TAVILY_API_KEY:
                logger.info("mcp_search_fallback_tavily")
                tavily_ok = False
                for tavily_attempt in range(2):  # P1-4: Tavily 也重试 1 次
                    try:
                        results = await self._call_tavily_search(query, max_results)
                        tavily_ok = True
                        break
                    except Exception as e2:
                        last_tavily_error = e2
                        logger.warning(
                            "mcp_search_tavily_retry",
                            attempt=tavily_attempt + 1,
                            error=str(e2),
                        )
                        if tavily_attempt < 1:
                            import asyncio
                            await asyncio.sleep(0.5)
                if not tavily_ok:
                    duration_ms = (time.time() - start) * 1000
                    logger.error("mcp_search_tavily_failed", error=str(last_tavily_error), duration_ms=round(duration_ms, 2))
                    raise last_tavily_error
            else:
                raise

        duration_ms = (time.time() - start) * 1000
        logger.info("mcp_search", query=query, results_count=len(results), duration_ms=round(duration_ms, 2))
        return results

    async def _call_tavily_search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        import httpx
        async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                },
            )
            response.raise_for_status()
            data = response.json()
            return [
                SearchResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                )
                for r in data.get("results", [])
            ]

    async def search_multi_round(
        self,
        directions: list[str],
        existing_urls: set[str],
        max_rounds: int = 2,
        max_results: int = 5,
    ) -> list[list[SearchResult]]:
        visited_urls: set[str] = {_normalize_url(u) for u in existing_urls}
        all_rounds: list[list[SearchResult]] = []

        for round_idx in range(max_rounds):
            if round_idx >= len(directions):
                break

            direction = directions[round_idx]
            try:
                raw_results = await self.search(direction, max_results=max_results)
            except Exception:
                logger.warning("mcp_round_failed", round=round_idx + 1, direction=direction)
                break

            new_results = []
            for r in raw_results:
                normalized = _normalize_url(r.url)
                if normalized not in visited_urls:
                    visited_urls.add(normalized)
                    new_results.append(r)

            logger.info(
                "mcp_round_dedup",
                round=round_idx + 1,
                raw_count=len(raw_results),
                new_count=len(new_results),
            )
            all_rounds.append(new_results)

        return all_rounds


def _parse_search_results(result: CallToolResult) -> list[SearchResult]:
    results: list[SearchResult] = []
    for content_item in result.content:
        if hasattr(content_item, "text"):
            try:
                data = json.loads(content_item.text)
                if isinstance(data, dict) and "web" in data:
                    web = data["web"]
                    if isinstance(web, dict) and "results" in web:
                        for item in web["results"]:
                            results.append(SearchResult(
                                url=item.get("url", ""),
                                title=item.get("title", ""),
                                snippet=item.get("description", ""),
                            ))
                    elif isinstance(web, list):
                        for item in web:
                            if isinstance(item, dict):
                                results.append(SearchResult(
                                    url=item.get("url", ""),
                                    title=item.get("title", ""),
                                    snippet=item.get("description", ""),
                                ))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            results.append(SearchResult(
                                url=item.get("url", item.get("link", "")),
                                title=item.get("title", ""),
                                snippet=item.get("description", item.get("snippet", "")),
                            ))
            except (json.JSONDecodeError, TypeError):
                continue
    return results
