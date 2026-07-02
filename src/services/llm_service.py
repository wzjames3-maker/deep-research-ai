import asyncio
import json
import time
import litellm
import structlog
from src.config import settings
from src.services.prompts import (
    PLAN_GENERATION_PROMPT,
    PLAN_REVISION_PROMPT,
    SUB_AGENT_SEARCH_PROMPT,
    AGGREGATE_PROMPT,
    RELEVANCE_FILTER_PROMPT,
    QUERY_EXPANSION_PROMPT,
)
from src.errors import PlanGenerationFailedError, PlanGenerationTimeoutError

logger = structlog.get_logger()

litellm.drop_params = True

LLM_MAX_RETRIES = 3
LLM_RETRY_DELAYS = [1.0, 2.0, 4.0]


def _is_retryable(exc: Exception) -> bool:
    """Check if an LLM error is transient and worth retrying."""
    if isinstance(exc, (litellm.exceptions.AuthenticationError, litellm.exceptions.BadRequestError)):
        return False
    return True


def _log_usage(prompt: str, response_text: str, duration_ms: float, usage: dict | None = None) -> None:
    logger.info(
        "llm_call",
        prompt_len=len(prompt),
        response_len=len(response_text),
        duration_ms=round(duration_ms, 2),
        input_tokens=usage.get("prompt_tokens") if usage else None,
        output_tokens=usage.get("completion_tokens") if usage else None,
        total_tokens=usage.get("total_tokens") if usage else None,
    )


def _extract_usage(response) -> int:
    """Extract total token count from LLM response."""
    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        # Try direct attribute first, then dict representation
        if hasattr(usage, "total_tokens") and usage.total_tokens:
            return usage.total_tokens
        if hasattr(usage, "dict"):
            d = usage.dict()
            return d.get("total_tokens", 0) or 0
    return 0


async def _call_llm_raw(system_prompt: str, user_prompt: str, timeout: int | None = None) -> tuple[str, int]:
    """Call LLM and return (raw_content, total_tokens) without JSON parsing.

    Retries up to LLM_MAX_RETRIES times on transient errors (connection, 5xx).
    Auth errors (401) and bad requests (400) fail immediately.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    start = time.time()
    effective_timeout = timeout if timeout is not None else settings.LLM_TIMEOUT

    last_exc: Exception | None = None
    for attempt in range(1 + LLM_MAX_RETRIES):
        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=messages,
                api_key=settings.LLM_API_KEY,
                api_base=settings.LLM_API_BASE,
                timeout=effective_timeout,
            )
        except litellm.exceptions.Timeout:
            duration_ms = (time.time() - start) * 1000
            logger.warning("llm_timeout", prompt_len=len(user_prompt), duration_ms=round(duration_ms, 2))
            raise PlanGenerationTimeoutError("LLM 调用超时")
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt >= LLM_MAX_RETRIES:
                break
            delay = LLM_RETRY_DELAYS[attempt]
            logger.warning(
                "llm_retry",
                attempt=attempt + 1,
                max_retries=LLM_MAX_RETRIES,
                delay=delay,
                error=str(e),
            )
            await asyncio.sleep(delay)
            continue
        break
    else:
        pass

    if last_exc is not None:
        duration_ms = (time.time() - start) * 1000
        logger.error("llm_error", error=str(last_exc), duration_ms=round(duration_ms, 2))
        if isinstance(last_exc, litellm.exceptions.Timeout):
            raise PlanGenerationTimeoutError("LLM 调用超时")
        raise PlanGenerationFailedError(f"LLM 调用失败: {last_exc}")

    duration_ms = (time.time() - start) * 1000
    content = response.choices[0].message.content if response.choices else ""
    usage = response.usage.dict() if hasattr(response, "usage") and response.usage else None
    total_tokens = _extract_usage(response)

    _log_usage(user_prompt, content, duration_ms, usage)

    return content, total_tokens


async def _call_llm(system_prompt: str, user_prompt: str) -> tuple:
    """Call LLM and return (parsed_result, total_tokens)."""
    content, total_tokens = await _call_llm_raw(system_prompt, user_prompt)
    return _extract_json_block(content), total_tokens


def _extract_json_block(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    import re
    match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def generate_plan(topic: str, template: str) -> tuple[list[dict], int]:
    """Generate a research plan. Returns (plan_list, token_used)."""
    prompt = PLAN_GENERATION_PROMPT.format(topic=topic, template=template)
    result, tokens = await _call_llm("你是一个 JSON 格式输出的研究计划生成器。", prompt)

    if isinstance(result, list):
        return result, tokens
    if isinstance(result, dict):
        return [result], tokens

    logger.warning("llm_plan_parse_fallback", topic=topic)
    return [
        {"name": "综合调研", "goal": f"对「{topic}」进行综合调研", "searchDirection": topic}
    ], tokens


async def revise_plan(topic: str, current_plan: list[dict], feedback: str) -> tuple[list[dict], int]:
    """Revise a research plan. Returns (revised_plan, token_used)."""
    prompt = PLAN_REVISION_PROMPT.format(
        topic=topic,
        current_plan=json.dumps(current_plan, ensure_ascii=False, indent=2),
        feedback=feedback,
    )
    result, tokens = await _call_llm("你是一个 JSON 格式输出的研究计划修改器。", prompt)

    if isinstance(result, list):
        return result, tokens
    if isinstance(result, dict):
        return [result], tokens

    return current_plan, tokens


async def sub_agent_search(
    findings: str,
    search_results: str,
    direction: str,
    topic: str = "",
) -> tuple[dict, int]:
    """Analyze search results. Returns (analysis_dict, token_used)."""
    prompt = SUB_AGENT_SEARCH_PROMPT.format(
        findings=findings,
        search_results=search_results,
        direction=direction,
        topic=topic or direction,
    )
    result, total_tokens = await _call_llm("你是一个 JSON 格式输出的研究分析助手。", prompt)

    if isinstance(result, dict):
        return result, total_tokens

    return {
        "findings": findings + "\n\n" + search_results,
        "sufficient": True,
        "new_search_query": "",
    }, total_tokens


async def aggregate_report(topic: str, plan: list[dict], sub_agent_findings: str) -> tuple[str, int]:
    """Generate aggregate report. Returns (markdown_report, token_used)."""
    prompt = AGGREGATE_PROMPT.format(
        plan=json.dumps(plan, ensure_ascii=False, indent=2),
        sub_agent_findings=sub_agent_findings,
        topic=topic,
    )

    content, total_tokens = await _call_llm_raw(
        "你是一个专业的 Markdown 研究报告撰写助手。", prompt,
        timeout=settings.LLM_TIMEOUT * 3,
    )

    # AC-RES-020: 截断到 50000 字符（含提示）
    truncation_msg = "\n\n...(报告因长度限制已截断)"
    max_len = 50000 - len(truncation_msg)
    if len(content) > 50000:
        content = content[:max_len] + truncation_msg

    return content, total_tokens


async def filter_relevance(
    results: list[dict],
    topic: str,
    direction: str,
    min_score: int = 5,
) -> tuple[list[dict], int]:
    """Filter search results by relevance using LLM scoring.

    Args:
        results: List of dicts with 'title', 'url', 'snippet' keys
        topic: Research topic
        direction: Search direction
        min_score: Minimum score (0-10) to keep a result

    Returns:
        (filtered_results, token_used) — only results scoring >= min_score
    """
    if not results:
        return [], 0

    # Build results text for prompt
    results_text = "\n\n".join(
        f"[{i}] {r.get('title', 'N/A')}\n"
        f"    URL: {r.get('url', '')}\n"
        f"    {r.get('snippet', '')}"
        for i, r in enumerate(results)
    )

    prompt = RELEVANCE_FILTER_PROMPT.format(
        topic=topic, direction=direction, results=results_text,
    )

    scored, total_tokens = await _call_llm(
        "你是一个 JSON 格式输出的搜索结果评估助手。", prompt,
    )

    if not isinstance(scored, list):
        logger.warning("filter_relevance_parse_failed", fallback="keep_all")
        return results, total_tokens

    # Build score map: index -> score
    score_map: dict[int, int] = {}
    for item in scored:
        if isinstance(item, dict) and "index" in item and "score" in item:
            score_map[item["index"]] = item.get("score", 0)

    # Filter: keep results with score >= min_score
    # If a result has no score (LLM didn't evaluate it), keep it
    filtered = [
        r for i, r in enumerate(results)
        if score_map.get(i, min_score) >= min_score
    ]

    logger.info(
        "filter_relevance",
        input_count=len(results),
        output_count=len(filtered),
        scores=score_map,
    )

    return filtered, total_tokens


async def expand_query(
    topic: str,
    direction: str,
) -> tuple[list[str], int]:
    """Expand a search direction into multiple query variants.

    Returns:
        (queries, token_used) — original direction + 2 variants
    """
    prompt = QUERY_EXPANSION_PROMPT.format(topic=topic, direction=direction)
    result, total_tokens = await _call_llm(
        "你是一个 JSON 格式输出的搜索策略助手。", prompt,
    )

    queries = [direction]  # Always include original

    if isinstance(result, dict) and "queries" in result:
        variants = result["queries"]
        if isinstance(variants, list):
            for q in variants[:2]:  # Max 2 variants
                if isinstance(q, str) and q.strip():
                    queries.append(q.strip())

    logger.info("expand_query", original=direction, variants=queries)
    return queries, total_tokens
