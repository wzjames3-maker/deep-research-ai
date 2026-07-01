# Task 19: 研究执行引擎 + SSE 流

## 对应 Spec
- specs/research/03-api-contract.md:
  - API-RES-004 (SSE 流端点 + 8 种 Event 类型)
- specs/research/06-acceptance.md: AC-RES-007, 008, 009, 010, 011, 021, 024
- specs/research/04-business-rules.md:
  - RULE-RES-004（Sub-agent 并行分发）
  - RULE-RES-005（Sub-agent ≤ 2 轮搜索循环）
  - RULE-RES-006（URL 去重）
  - RULE-RES-007（Sub-agent 超时处理: 3 分钟）
  - RULE-RES-008（汇总 Agent 策略）
  - RULE-RES-011（Token 消耗统计）
- docs/tech-decision.md §决策2 (LangGraph 编排)

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-004（完整 SSE event 定义）
- specs/research/04-business-rules.md RULE-RES-005~008
- specs/research/06-acceptance.md AC-RES-007~011, 024
- src/services/llm_service.py（aggregate_report, sub_agent_search）
- src/services/mcp_client.py（MCPSearchClient）
- src/utils/ticket_store.py（verify_ticket）
- src/repos/research_repo.py / sub_agent_result_repo.py
- src/config.py

## 输出文件
- `src/services/exec_engine.py`（研究执行引擎: LangGraph StateGraph）
- `src/services/sse_manager.py`（SSE 事件管理器）
- `src/api/research/router.py`（追加 GET /stream 端点）
- `src/api/research/__init__.py`

## 前置任务
- Task 18（plan confirm API 可用）
- Task 15（LLM 服务可用）
- Task 16（MCP 客户端可用）
- Task 08（ticket verify 可用）

## 实现要求

### 1. SSE 端点 (`GET /api/v1/research/{id}/stream?ticket=<ticket>`):
- 验证 ticket（30 秒有效）→ 获取 user_id
- 检查 user_id == research.user_id
- 返回 `Content-Type: text/event-stream`

### 2. 执行引擎 (`src/services/exec_engine.py`):

使用 LangGraph 构建 StateGraph。若 LangGraph 引入有问题（V1 降级路径），可用 asyncio.gather + 手动状态机等方案替代：

```
START → [Parallel: Sub-agent 1, 2, 3] → Aggregate → END
```

**LangGraph 状态定义**:
```python
class ResearchState(TypedDict):
    research_id: UUID
    topic: str
    template: str
    sub_agents: list[dict]
    sub_agent_results: dict  # {agent_id: result_state}
    status: str
```

**Sub-agent 节点**（每个独立运行）:
```
for round in [1, 2]:
    1. 调用 MCP client.search(search_direction)
    2. URL 去重（跨轮次）
    3. 若搜索结果为空:
       - round=1 → LLM 自动调整搜索词，进入下一轮
       - round=2 → 输出 findings="未找到相关信息"，标记 completed（非 failed，见 EC-RES-007）
    4. 调用 llm_service.sub_agent_search(findings, results)
       - LLM 调用若触达 API rate limit → LiteLLM 内置指数退避重试(最多3次)
       - 3次后仍失败 → Sub-agent 降级为串行延迟执行（EC-RES-009）
    5. 推 SSE: sub_agent_round
    6. 更新 DB: SubAgentResult
推 SSE: sub_agent_complete
```

**汇总节点**:
```
1. 收集所有 Sub-agent 结果
   - 全部失败 → Research.status='failed', SSE: error
   - 部分失败 → 继续汇总
2. 调用 llm_service.aggregate_report(topic, plan, results)
3. 截断到 50000 字符
4. 保存到 Research.report_markdown
5. 计算 total_tokens = SUM(token_used)
6. Research.status='completed', completed_at=now()
7. 推 SSE: report_complete
```

### 3. SSE 事件管理器 (`src/services/sse_manager.py`):
- 使用 `sse-starlette` 或手动 ASGI 实现
- 维护活跃连接字典 `{research_id: list[queue]}`
- 方法:
  - `async def connect(research_id, user_id)` → 创建队列
  - `async def push_event(research_id, event_type, data)` → 广播到所有连接
  - `async def disconnect(research_id, queue)` → 移除队列
- Heartbeat: 每 15 秒发送 `heartbeat` 事件（保活 + 检测断连）

### 4. SSE 8 种事件:
| Event | 触发时机 |
|---|---|
| `plan_confirm` | 计划确认后立即推送（可选） |
| `sub_agent_start` | 每个 Sub-agent 开始执行 |
| `sub_agent_round` | 每轮搜索开始 |
| `sub_agent_complete` | Sub-agent 成功完成 |
| `sub_agent_fail` | Sub-agent 执行失败 |
| `report_complete` | 汇总完成 |
| `error` | 顶层错误（全部失败等） |
| `heartbeat` | 每 15 秒（保活） |

### 5. 后台触发:
- Task 18 的 POST /confirm 调用后，使用 `asyncio.create_task()` 或 `BackgroundTasks` 启动执行引擎
- 执行引擎运行在独立的后台协程中

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 18 plan confirm 可用
- [ ] Task 15 LLM 服务可用
- [ ] Task 16 MCP 客户端可用
- [ ] Task 08 ticket verify 可用

### AC 验收
- [ ] AC-RES-007: SSE 连接 → 收到所有 8 种事件类型
- [ ] AC-RES-008: URL 去重生效（跨轮次过滤）
- [ ] AC-RES-009: 2 轮硬限制 → rounds_completed=2
- [ ] AC-RES-010: 全部 Sub-agent 失败 → status='failed', SSE error
- [ ] AC-RES-011: 部分失败 → status='completed', 报告含成功结果
- [ ] AC-RES-024: valid ticket → 连接成功; expired → 401; 无 ticket → 401

### 功能验收
- [ ] `curl -N "GET /stream?ticket=xxx"` → 持续接收 SSE 事件
- [ ] 每 15 秒收到 heartbeat（30 秒无新事件时）
- [ ] Sub-agent 按 plan 并发执行（不是串行）
- [ ] 报告长度 > 50000 → 截断并加提示

### 代码质量
- [ ] SSE 连接不阻塞 FastAPI 主线程（使用 BackgroundTask）
- [ ] 客户端断连 → 资源清理（队列移除）
- [ ] Sub-agent 执行有独立超时（每个 180 秒，RULE-RES-007）
- [ ] DB 写入失败时重试 3 次

### 通过判定
全部 ✅ → 任务 Done，进入 Task 20
