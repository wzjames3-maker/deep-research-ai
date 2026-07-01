# Task 36: Sub-agent Subgraph 测试（TDD RED）

## 对应 Spec
- specs/research/04-business-rules.md RULE-RES-005（搜索循环）, RULE-RES-006（URL 去重）, RULE-RES-007（超时）
- specs/research/06-acceptance.md AC-RES-008, 009
- specs/research/07-tech-constraints.md（Sub-agent Subgraph 结构）

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md RULE-RES-005~007
- specs/research/06-acceptance.md AC-RES-008, 009
- specs/research/07-tech-constraints.md（SubAgentState 定义）
- src/services/graph_state.py（State 定义）
- src/services/mcp_client.py（MCPSearchClient, 已有）
- src/services/llm_service.py（sub_agent_search, 已有）

## 输出文件
- `tests/unit/test_sub_agent_graph.py`（NEW）

## 前置任务
- Task 33（langgraph 已安装）
- Task 34（graph_state.py 已定义）

## 实现要求

### 测试用例（全部应为 RED — 失败但能运行）

1. **test_search_to_analyze_flow**: search → dedup → analyze 正常流程
2. **test_sufficient_true_ends_loop**: LLM 返回 sufficient=true → conditional edge 路由到 END
3. **test_sufficient_false_loops_back**: LLM 返回 sufficient=false & rounds<2 → 路由回 search
4. **test_rounds_limit_2**: rounds_completed=2 → 强制进入 END（NFR-012 硬限制）
5. **test_url_dedup_across_rounds**: 第 1 轮 URL [A,B,C]，第 2 轮 [B,D,E] → 仅 D,E 输入 LLM
6. **test_mcp_search_failure_marks_failed**: MCP 搜索异常 → status='failed'
7. **test_timeout_marks_failed**: asyncio.timeout 触发 → status='failed'
8. **test_cancel_signal_stops_loop**: asyncio.Event set → 循环中断，status='cancelled'

### 测试 setup
- 使用 MemorySaver（非 PostgresSaver）做 unit test
- Mock MCPSearchClient.search 和 llm_service.sub_agent_search
- 使用 `async with` 创建独立 DB session（与现有 conftest 一致）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 34 graph_state.py 可导入
- [ ] tests/conftest.py 的 fixtures 可用

### AC 验收（TDD RED 阶段）
- [ ] 8 个测试用例已编写
- [ ] 所有测试运行失败（RED）— 因 sub_agent_graph 尚未实现
- [ ] 测试能正常运行（import 无误，只是 assert 失败）

### 通过判定
全部 ✅ → 任务 Done（RED），进入 Task 38（GREEN）
