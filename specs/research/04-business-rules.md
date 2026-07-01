# 业务规则

## 来源
PRD.md §3 UC-003 ~ UC-009 + §5 NFR-008 ~ NFR-013

---

## RULE-RES-001: 单用户并发限制

- **触发**: 发起新研究（API-RES-001）
- **规则**: 检查当前用户是否存在 `status IN ('running')` 的研究
  > `confirmed` 为瞬态（不持久化），无需检查
- **违反**: 返回 409 RESEARCH_IN_PROGRESS
- **引用**: PRD NFR-008

---

## RULE-RES-002: 模板拆分策略

- **触发**: 生成研究计划（REQ-RES-001）
- **规则**: 根据 `template` 参数指导主 Agent 以不同策略拆分 3-5 个 Sub-agent:

| 模板 | 拆分策略 |
|---|---|
| tech_research | 技术原理 → 生态与社区 → 竞品对比 → 应用场景 → 发展趋势 |
| competitive_analysis | 市场定位 → 产品矩阵 → 定价策略 → 用户口碑 → 优劣势对比 |
| literature_review | 经典理论 → 近年进展 → 争议与讨论 → 研究空白 → 方法论评估 |
| custom | 主 Agent 自由拆分 3-5 个角度 |

- **输出约束**:
  - Sub-agent 数量: 3-5 个（含）
  - 每个 Sub-agent 包含: `name`, `goal`, `searchDirection`
  - `searchDirection` 用于指导首轮搜索关键词

---

## RULE-RES-003: 计划修改轮次限制

- **触发**: 每次调用 API-RES-002
- **规则**: 最多 10 轮修改
- **违反**: 返回 400 TOO_MANY_REVISIONS，建议确认当前计划或重新发起研究
- **引用**: PRD UC-004 异常流程

---

## RULE-RES-004: Sub-agent 分发策略

- **触发**: 计划确认（API-RES-003）
- **规则**:
   1. 状态转移: `draft` → `running`（`confirmed` 为瞬态，V1 不持久化。confirm API 直接将 `draft` 写入 `running`；SSE `plan_confirm` 事件推送时短暂携带 `confirmed` 状态通知前端，但不写入数据库）
   2. 并行启动所有 Sub-agent：通过 LangGraph **Send API** fan-out，每个 Sub-agent 对应一个独立的 Subgraph
   3. 每个 Sub-agent 独立运行，互不影响（Subgraph 隔离状态）
   4. 任一 Sub-agent 失败不阻塞其他 Sub-agent（Send API + `return_exceptions` 语义）
- **超时**: 单个 Sub-agent 最长 3 分钟（含 LLM 调用 + MCP 搜索），通过 `asyncio.timeout()` 包裹 Subgraph 节点
- **实现**: `dispatch_node` 使用 `[Send("sub_agent_graph", {agent_def: sa}) for sa in plan]` 列表，StateGraph 自动并行执行
- **State Reducer**: `sub_agent_results` 字段使用 `Annotated[list[dict], operator.add]` reducer，确保并行结果累加而非覆盖

---

## RULE-RES-005: Sub-agent 搜索循环

- **触发**: REQ-RES-005
- **规则**:
   1. 每一轮：调用 MCP 搜索 → 读取结果 → LLM 评估信息充足性
   2. 评估标准：LLM 判断已获取的信息是否足够回答子课题（返回 `sufficient: true/false` + 新搜索词）
   3. 若 `sufficient=false` 且 `round < 4` → 生成新搜索词，进入下一轮
   4. 若 `sufficient=true` 或 `round = 4` → 输出研究发现
- **硬限制**: 每个 Sub-agent 最多 4 轮循环（NFR-012）
- **实现**: Sub-agent Subgraph 内部使用 conditional edge `route_after_analyze`：检查 `state.sufficient` 和 `state.rounds_completed`，决定回到 `search` 节点还是进入 `END`
- **引用**: PRD NFR-012

---

## RULE-RES-006: URL 去重

- **触发**: 每次搜索完成后
- **规则**:
   1. 维护已访问 URL 集合（存储在 `SubAgentResult.visited_urls` JSONB 字段中，同时缓存在 SubAgentState）
   2. 新搜索结果的 URL 先做规范化处理（去除 query string、trailing slash）
   3. 与集合中 URL 做精确匹配
   4. 已存在的 URL 跳过（不作为 LLM 上下文输入）
- **注意**: V1 不做语义去重（O-005 已确认），仅 URL 级别去重

---

## RULE-RES-007: Sub-agent 超时处理

- **触发**: Sub-agent 单次执行超过 3 分钟
- **规则**:
   1. 标记该 Sub-agent 为 `failed`
   2. 其他 Sub-agent 继续执行
   3. SSE 推送 `sub_agent_fail` 事件
- **实现**: Subgraph 节点用 `asyncio.timeout(settings.SUB_AGENT_TIMEOUT)` 包裹，`TimeoutError` 捕获后设置 `state.status = "failed"`

---

## RULE-RES-008: 汇总 Agent 策略

- **触发**: 所有 Sub-agent 完成（completed/failed/cancelled）
- **规则**:
   1. 若至少 1 个 Sub-agent 为 `completed` → 汇总所有 completed 的结果生成报告
   2. 若所有 Sub-agent 均为 `failed` → 拒绝生成报告，status='failed', error_message='所有搜索源均未返回有效信息'
   3. 报告结构：
      - 研究计划摘要（research plan recap）
      - 各 Sub-agent 详细发现（每个一节，含原始来源链接）
      - 综合结论（synthesis & key findings）
   4. 报告最大长度: 50,000 中文字符（NFR-010），超长截断
- **实现**: `check_cancel` conditional edge 路由到 `aggregate` 或 `partial_aggregate` 节点；`aggregate` 节点调用 `llm_service.aggregate_report()`
- **引用**: PRD UC-006 异常流程, NFR-010

---

## RULE-RES-009: 中断处理

- **触发**: 用户调用 API-RES-008
- **规则**:
   1. 终止所有运行中的 Sub-agent
   2. 若 10 秒内且无任何 Sub-agent 有有效结果 → 不生成报告，status='cancelled'
   3. 若已有部分结果 → 基于已有结果生成部分报告
- **实现**: Hybrid 取消机制
   - **持久化层**: `graph.aupdate_state(config, {"cancel_requested": True})` 写入 checkpoint（用于崩溃恢复后感知取消）
   - **实时信号层**: 保留 `asyncio.Event` 模块级信号（Sub-agent 每轮搜索前检查，实现快速中断）
   - **路由**: `check_cancel` conditional edge 检测 `state.cancel_requested`，若为 True 路由到 `partial_aggregate`，否则路由到 `aggregate`
- **引用**: PRD UC-005

---

## RULE-RES-010: 软删除

- **触发**: API-RES-009
- **规则**:
   1. 设置 `Research.deleted_at = NOW()`
   2. 不物理删除 SubAgentResult 和 ResearchPlanFeedback 记录
   3. 所有查询默认加 `WHERE deleted_at IS NULL`
   4. 同时清理 LangGraph checkpoint 数据（`checkpointer.adelete_thread(thread_id)`），避免孤立 checkpoint 残留
- **引用**: PRD UC-009

---

## RULE-RES-011: Token 消耗统计

- **触发**: 每次 LLM 调用（LiteLLM callback）
- **规则**:
   1. 记录该次调用消耗的 input_tokens + output_tokens
   2. 实时累加到 `Research.total_tokens`
   3. Sub-agent 维度的消耗隔离记录到 `SubAgentResult.token_used`
- **实现**: 各 graph node 调用 `llm_service` 函数后获取返回的 token 数，写入 state 和 DB
