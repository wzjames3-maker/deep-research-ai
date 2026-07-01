# Task 40: Dispatch + Aggregate + check_cancel 节点实现

## 对应 Spec
- specs/research/04-business-rules.md RULE-RES-004, RULE-RES-008, RULE-RES-009
- specs/research/07-tech-constraints.md §Send API, §Hybrid 取消机制

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md RULE-RES-004, 008, 009
- specs/research/07-tech-constraints.md §Send API, §Hybrid 取消机制
- src/services/sub_agent_graph.py（Task 38: compile_sub_agent_graph）
- src/services/llm_service.py（aggregate_report）
- src/services/sse_manager.py
- src/repos/research_repo.py
- src/repos/sub_agent_result_repo.py
- src/services/graph_state.py（ResearchState）
- src/services/exec_engine.py（cancel_signals, check_cancelled — 保留 asyncio.Event）

## 输出文件
- `src/services/research_graph.py`（追加: dispatch_node, check_cancel, aggregate_node, partial_aggregate_node）

## 前置任务
- Task 38（Sub-agent subgraph 已编译）
- Task 39（plan 节点已实现）

## 实现要求

### dispatch_node（Send API fan-out）

```python
from langgraph.types import Send

async def dispatch_node(state: ResearchState) -> list[Send]:
    """Fan-out to sub-agent subgraphs using Send API."""
    plan = state["plan"]
    research_id = state["research_id"]
    topic = state["topic"]

    # 推送 SSE: plan_confirm
    await sse_manager.push_event(
        research_id, "plan_confirm",
        {"status": "confirmed", "researchId": str(research_id)},
    )

    # Send API: 每个 sub-agent 对应一个 Send
    sends = []
    for sa_def in plan:
        send = Send("sub_agent_graph", {
            "research_id": research_id,
            "topic": topic,
            "agent_def": sa_def,
            "search_direction": sa_def.get("searchDirection", ""),
            "visited_urls": [],
            "findings": "",
            "rounds_completed": 0,
            "sufficient": False,
            "token_used": 0,
            "status": "pending",
            "has_error": False,
        })
        sends.append(send)

    return sends
```

### check_cancel（conditional edge）

```python
def check_cancel(state: ResearchState) -> str:
    """Route to aggregate or partial_aggregate based on cancel_requested."""
    if state.get("cancel_requested", False):
        return "partial_aggregate"
    return "aggregate"
```

### aggregate_node

```python
async def aggregate_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Aggregate all sub-agent results into final report."""
    db_factory = config["configurable"]["db_session_factory"]
    research_id = state["research_id"]

    # 查询所有 SubAgentResult
    # RULE-RES-008:
    #   - 全部 failed → status='failed', SSE error, 无报告
    #   - 部分 failed → 继续汇总
    #   - 至少 1 completed → 生成报告

    # 推送 SSE: aggregation_start
    # 调用 llm_service.aggregate_report(topic, plan, findings)
    # 截断 50000 字符
    # 更新 Research: report_markdown, total_tokens, status='completed', completed_at
    # 推送 SSE: report_complete
    ...
```

### partial_aggregate_node

```python
async def partial_aggregate_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Handle cancellation: partial report or bare cancel."""
    db_factory = config["configurable"]["db_session_factory"]
    research_id = state["research_id"]

    # RULE-RES-009:
    #   - 无 completed sub-agent → status='cancelled', 无报告, SSE error
    #   - 有 completed sub-agent → 生成部分报告, status='cancelled'
    #   - 推送 SSE: aggregation_start (如有部分报告)
    #   - 推送 SSE: report_complete (status='cancelled')
    ...
```

### Sub-agent Subgraph 集成

在 main graph 中添加 sub_agent_graph 作为 node:

```python
compiled_sub_agent_graph = compile_sub_agent_graph()

# 在 builder 中:
builder.add_node("sub_agent_graph", compiled_sub_agent_graph)
```

### SSE 事件
- `dispatch_node`: 推送 `plan_confirm`
- `aggregate_node`: 推送 `aggregation_start` → `report_complete`
- `partial_aggregate_node`: 推送 `aggregation_start`（如有）→ `report_complete`（status='cancelled'）或 `error`（无结果）

### Cancel 信号检查
- `dispatch_node` 不检查 cancel（刚确认计划，不会立即取消）
- Sub-agent subgraph 内部检查（Task 38 已实现）
- `check_cancel` 读取 `state.cancel_requested`（由 `update_state` 设置）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 38 sub_agent_graph 已编译
- [ ] Task 39 plan 节点已实现

### 功能验证
- [ ] dispatch_node: 返回 list[Send]，数量 = len(plan)
- [ ] dispatch_node: SSE plan_confirm 推送
- [ ] check_cancel: cancel_requested=False → 'aggregate'
- [ ] check_cancel: cancel_requested=True → 'partial_aggregate'
- [ ] aggregate_node: 全 failed → status='failed', SSE error
- [ ] aggregate_node: 部分 failed → status='completed', 报告含成功结果
- [ ] aggregate_node: 全 completed → status='completed', 完整报告
- [ ] aggregate_node: 报告 > 50000 字符 → 截断
- [ ] partial_aggregate_node: 无 completed → status='cancelled', 无报告
- [ ] partial_aggregate_node: 有 completed → 部分报告, status='cancelled'

### 代码质量
- [ ] DB session 通过 config 注入
- [ ] SSE 事件格式与 03-api-contract.md 一致
- [ ] total_tokens 累加正确（sub_agent tokens + report tokens）
- [ ] 无裸 try/except

### 通过判定
全部 ✅ → 任务 Done，进入 Task 41
