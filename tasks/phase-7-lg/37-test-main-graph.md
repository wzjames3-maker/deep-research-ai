# Task 37: Main Graph 测试 (TDD RED)

## 对应 Spec
- specs/research/04-business-rules.md RULE-RES-004, RULE-RES-008, RULE-RES-009
- specs/research/06-acceptance.md AC-RES-025, AC-RES-026, AC-RES-027
- specs/research/07-tech-constraints.md §LangGraph 架构约束

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md RULE-RES-004, 008, 009
- specs/research/06-acceptance.md AC-RES-025, 026, 027
- specs/research/07-tech-constraints.md §LangGraph 架构约束（StateGraph 结构图）
- src/services/graph_state.py（Task 34 产出）
- src/services/sub_agent_graph.py（Task 38 产出 — mock 掉，此任务只需接口）

## 输出文件
- `tests/unit/test_research_graph.py`（Main graph 测试）

## 前置任务
- Task 34（State Schema 定义可用）
- Task 36（Sub-agent subgraph 测试参考）

## 实现要求

### 测试用 MemorySaver（非 PostgresSaver）做 unit test

```python
from langgraph.checkpoint.memory import MemorySaver
from src.services.research_graph import compile_research_graph

checkpointer = MemorySaver()
graph = compile_research_graph(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "test-1", "db_session_factory": mock_factory}}
```

### 测试用例

1. **test_plan_generation_to_interrupt**: invoke → 运行到 human_review interrupt → 验证 state 有 plan, status='draft'
2. **test_resume_with_confirm**: 从 interrupt resume with {"action":"confirm"} → 验证 dispatch 启动 → 验证 aggregate 结果
3. **test_resume_with_revise**: 从 interrupt resume with {"action":"revise","feedback":"加一个竞品对比"} → 验证 plan_revision 执行 → 验证回到 interrupt
4. **test_resume_revise_then_confirm**: revise → interrupt → confirm → 完整流程跑通
5. **test_send_api_parallel**: confirm → dispatch → 验证 3 个 Sub-agent 并行执行 → 验证 sub_agent_results 长度 = 3
6. **test_check_cancel_routes_to_partial_aggregate**: cancel_requested=True → check_cancel → 路由到 partial_aggregate
7. **test_check_cancel_normal_routes_to_aggregate**: cancel_requested=False → check_cancel → 路由到 aggregate
8. **test_all_sub_agents_failed**: 所有 sub-agent 返回 failed → aggregate → status='failed', report=None
9. **test_partial_failure_aggregate**: 2 completed + 1 failed → aggregate → status='completed', report 含 2 个结果
10. **test_checkpoint_recovery**: invoke 到一半中断 → 新 graph 实例（同 thread_id）→ ainvoke(None) → 从 checkpoint 恢复
11. **test_state_reducer_accumulates**: Send API 返回多个 sub_agent_results → 验证 reducer 累加而非覆盖
12. **test_cancel_requested_persisted_in_checkpoint**: update_state cancel_requested=True → 新 graph 实例恢复 → 验证 cancel_requested 仍为 True

### Mock 策略
- mock `llm_service.generate_plan/revise_plan/aggregate_report` 返回固定值
- mock `MCPSearchClient.search` 返回固定搜索结果
- mock `db_session_factory` 返回 test DB session
- Sub-agent subgraph 可用真实编译版（如 Task 36 已完成）或 mock

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 34 State Schema 可 import
- [ ] MemorySaver 可用（langgraph 已安装）

### TDD RED 验证
- [ ] 所有 12 个测试能运行（import 成功，无语法错误）
- [ ] 所有 12 个测试 **失败**（因为 research_graph.py 尚未实现）
- [ ] 失败原因是 `ImportError` 或 `NotImplementedError`，不是语法错误

### 代码质量
- [ ] 每个 test 用例有独立的 thread_id（避免 checkpoint 串扰）
- [ ] Mock 对象不泄露到其他测试（使用 fixture 隔离）
- [ ] 使用 `pytest.mark.asyncio` 标记 async 测试

### 通过判定
全部 RED（能运行但失败）→ 任务 Done，进入 Task 38
