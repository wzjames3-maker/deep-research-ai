# Task 38: Sub-agent Subgraph 实现 (TDD GREEN)

## 对应 Spec
- specs/research/04-business-rules.md RULE-RES-005, RULE-RES-006, RULE-RES-007
- specs/research/07-tech-constraints.md §StateGraph 结构, §State 定义

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md RULE-RES-005, 006, 007
- specs/research/07-tech-constraints.md §LangGraph 架构约束
- src/services/graph_state.py（Task 34 产出: SubAgentState）
- src/services/mcp_client.py（MCPSearchClient, _normalize_url）
- src/services/llm_service.py（sub_agent_search）
- src/services/sse_manager.py（sse_manager.push_event）
- src/repos/sub_agent_result_repo.py
- src/config.py（SUB_AGENT_TIMEOUT）
- tests/unit/test_sub_agent_graph.py（Task 36 产出: RED 测试）

## 输出文件
- `src/services/sub_agent_graph.py`（Sub-agent Subgraph 实现）

## 前置任务
- Task 33（langgraph 已安装）
- Task 34（SubAgentState 定义可用）
- Task 36（RED 测试存在）

## 实现要求

### Sub-agent Subgraph 结构

```
START
  │
  ▼
init_node          ← 初始化 SubAgentState: status='running', visited_urls=[], findings=''
  │
  ▼
search_node        ← MCP 搜索（MCPSearchClient.search）
  │
  ▼
dedup_node         ← URL 规范化 + 去重（_normalize_url + visited_urls set）
  │
  ▼
analyze_node       ← LLM 分析（llm_service.sub_agent_search）
  │                  → 更新 findings, sufficient, new_keywords, rounds_completed
  │                  → 推送 SSE: sub_agent_round
  │
  ▼
route_after_analyze  ← conditional edge
  │     │
  │     ├─ sufficient=true OR rounds>=2 → complete_node
  │     └─ sufficient=false AND rounds<2 → search_node (回环)
  │
  ▼
complete_node      ← 更新 DB (SubAgentResult), 推送 SSE: sub_agent_complete / sub_agent_fail
  │
  ▼
END
```

### 各节点实现

```python
# src/services/sub_agent_graph.py

from langgraph.graph import StateGraph, END
from typing import TypedDict
import asyncio
from datetime import datetime, timezone

from src.config import settings
from src.services.mcp_client import MCPSearchClient, SearchResult, _normalize_url
from src.services import llm_service
from src.services.sse_manager import sse_manager
from src.repos.sub_agent_result_repo import SubAgentResultRepository
from src.services.graph_state import SubAgentState

async def init_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Initialize sub-agent: mark running, push SSE start event."""
    # 获取 db_session_factory from config
    # 更新 SubAgentResult.status = 'running'
    # 推送 SSE: sub_agent_start
    return {"status": "running", "visited_urls": [], "findings": "", "rounds_completed": 0, "token_used": 0}

async def search_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Call MCP search with current search_direction."""
    # 检查 cancel（asyncio.Event）
    # 调用 MCPSearchClient.search(state["search_direction"])
    # 返回 {"search_results": results}
    ...

async def dedup_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """URL dedup: normalize + filter against visited_urls."""
    # _normalize_url + visited_urls set
    # 返回 {"new_results": filtered, "visited_urls": updated_set}
    ...

async def analyze_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """LLM analysis: assess sufficiency, extract findings."""
    # 调用 llm_service.sub_agent_search(findings, results, direction, topic)
    # 更新 findings, sufficient, new_keywords, rounds_completed
    # 推送 SSE: sub_agent_round
    # 返回 updated fields
    ...

def route_after_analyze(state: SubAgentState) -> str:
    """Conditional edge: route to complete or back to search."""
    if state.get("sufficient", True) or state.get("rounds_completed", 0) >= 2:
        return "complete"
    return "search"

async def complete_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Update DB with final results, push SSE complete/fail event."""
    # 检查 cancel → status='cancelled'
    # 检查 has_error → status='failed'
    # 否则 → status='completed'
    # 更新 SubAgentResult: findings_text, visited_urls, rounds_completed, token_used, completed_at
    # 推送 SSE: sub_agent_complete 或 sub_agent_fail
    # 返回 {"status": final_status}
    ...

def compile_sub_agent_graph():
    """Compile the sub-agent subgraph."""
    builder = StateGraph(SubAgentState)
    builder.add_node("init", init_node)
    builder.add_node("search", search_node)
    builder.add_node("dedup", dedup_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("complete", complete_node)

    builder.set_entry_point("init")
    builder.add_edge("init", "search")
    builder.add_edge("search", "dedup")
    builder.add_edge("dedup", "analyze")
    builder.add_conditional_edges("analyze", route_after_analyze)
    builder.add_edge("complete", END)

    return builder.compile()
```

### 超时处理
- `search_node` 用 `asyncio.timeout(settings.SUB_AGENT_TIMEOUT)` 包裹整个搜索+分析循环
- `TimeoutError` → 设置 `has_error=True`, 跳到 `complete_node`

### SSE 事件
- `init_node`: 推送 `sub_agent_start`（subAgentId, name, goal, status='running'）
- `analyze_node`: 推送 `sub_agent_round`（subAgentId, round, searchQuery）
- `complete_node`: 推送 `sub_agent_complete` 或 `sub_agent_fail`（subAgentId, name, status, roundsUsed, preview, tokenUsed）

### Cancel 检查
- `search_node` 开头检查 `asyncio.Event`（从模块级 `cancel_signals` dict 获取）
- 若已取消 → 直接跳到 `complete_node`，设置 `status='cancelled'`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 33 langgraph 已安装
- [ ] Task 34 SubAgentState 可 import
- [ ] Task 36 RED 测试存在

### TDD GREEN 验证
- [ ] Task 36 的所有测试 GREEN（pass）
- [ ] test_search_to_dedup_to_analyze: 基本流程通过
- [ ] test_sufficient_true_to_end: sufficient=true → 直接 complete
- [ ] test_insufficient_false_loops_back: sufficient=false → 回 search
- [ ] test_hard_limit_rounds_2: rounds=2 → 强制 complete
- [ ] test_url_dedup_across_rounds: 跨轮去重生效
- [ ] test_timeout_marks_failed: 超时 → status='failed'
- [ ] test_cancel_checks_before_search: 取消 → status='cancelled'

### 代码质量
- [ ] 无裸 try/except（显式捕获具体异常）
- [ ] 无 time.sleep()
- [ ] DB session 通过 config 注入，不放入 state
- [ ] asyncio.Event 从模块级 cancel_signals 获取（不放入 state）
- [ ] SSE 事件格式与 specs/research/03-api-contract.md 一致

### 通过判定
全部 GREEN → 任务 Done，进入 Task 39
