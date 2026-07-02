# Task 45: SSE 事件集成验证

## 对应 Spec
- specs/research/03-api-contract.md API-RES-004（8 种 SSE Event 类型）
- specs/research/06-acceptance.md AC-RES-007

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-004
- src/services/research_graph.py（所有 graph 节点）
- src/services/sub_agent_graph.py（sub-agent 节点）
- src/services/sse_manager.py
- src/api/research/router.py（SSE 端点）

## 输出文件
- 无新文件（验证任务，可能小幅修补节点内 SSE 推送代码）

## 前置任务
- Task 40（dispatch + aggregate 节点已实现）
- Task 43（service_plan 已更新）
- Task 44（router 已更新）

## 实现要求

### 验证 8 种 SSE 事件在 graph 节点中正确推送

| Event | 推送位置 | 推送节点 |
|---|---|---|
| `plan_confirm` | dispatch_node | research_graph.dispatch_node |
| `sub_agent_start` | init_node | sub_agent_graph.init_node |
| `sub_agent_round` | analyze_node | sub_agent_graph.analyze_node |
| `sub_agent_complete` | complete_node | sub_agent_graph.complete_node |
| `sub_agent_fail` | complete_node | sub_agent_graph.complete_node |
| `report_complete` | aggregate_node / partial_aggregate_node | research_graph |
| `error` | aggregate_node (all failed) / partial_aggregate_node (no results) | research_graph |
| `heartbeat` | router.py event_generator | 不在 graph 中（SSE 端点内） |

### 验证方式

1. **代码审查**: 逐个检查每个节点函数，确认 `sse_manager.push_event()` 调用存在
2. **集成测试**: 运行一次完整研究流程，通过 SSE 端点接收事件，验证事件类型和 payload 格式

### 验证清单

```python
# 验证脚本（可在 docker compose exec app python 中运行）

async def verify_sse_events():
    """Manual verification: create research → confirm → listen SSE."""
    # 1. POST /new → 获取 research_id
    # 2. POST /confirm
    # 3. GET /stream?ticket=xxx
    # 4. 收集所有 SSE 事件
    # 5. 验证事件类型和 payload
    events = []
    # ... collect events ...
    assert "plan_confirm" in [e["event"] for e in events]
    assert "sub_agent_start" in [e["event"] for e in events]
    assert "sub_agent_round" in [e["event"] for e in events]
    assert "sub_agent_complete" in [e["event"] for e in events]
    assert "report_complete" in [e["event"] for e in events]

    # 验证 payload 格式
    for e in events:
        if e["event"] == "sub_agent_start":
            assert "subAgentId" in e["data"]
            assert "name" in e["data"]
            assert "goal" in e["data"]
            assert "status" in e["data"]
        if e["event"] == "report_complete":
            assert "reportMarkdown" in e["data"]
            assert "totalTokens" in e["data"]
```

### 需要修补的常见问题

1. **research_id 在 graph state 中可能不存在**: 确保 `plan_generation_node` 写入 `research_id` 到 state
2. **sub_agent_graph 中 research_id 来源**: 从 SubAgentState 中获取（dispatch_node 传入）
3. **aggregation_start 事件**: specs 中有提到但不在 8 种事件中 — 确认是否需要推送（当前代码已推送，保持不变）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 40 dispatch + aggregate 已实现
- [ ] Task 43 service_plan 已更新
- [ ] Task 44 router 已更新

### AC 验收
- [ ] AC-RES-007: SSE 连接 → 收到所有事件类型（plan_confirm, sub_agent_start, sub_agent_round, sub_agent_complete, report_complete）
- [ ] 事件 payload 格式与 03-api-contract.md 一致
- [ ] heartbeat 每 15 秒推送（SSE 端点不变）

### 功能验收
- [ ] `curl -N "GET /stream?ticket=xxx"` → 持续接收 SSE 事件
- [ ] Sub-agent 按 plan 并行执行（SSE 事件交错而非串行）
- [ ] 报告完成 → report_complete 事件 → SSE 连接关闭

### 代码质量
- [ ] 所有 graph 节点中 sse_manager.push_event 调用的 research_id 来源明确
- [ ] SSE 事件 data dict 的 key 使用 camelCase（与前端一致）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 46
