# 边界情况与异常处理

## 来源
PRD.md §3 UC-003 ~ UC-009 异常流程 + feasibility.md 风险清单 + 技术判断

---

## EC-RES-001: LLM 计划生成超时

- **场景**: 主 Agent 生成研究计划超时（>30 秒）
- **处理**: 返回 500 PLAN_GENERATION_FAILED，status 保持 'draft'
- **日志**: WARNING 含 topic 信息
- **缓解**: 用户可重试；若连续 3 次失败，建议简化主题

---

## EC-RES-002: MCP Server 不可用

- **场景**: Brave Search MCP 容器宕机/网络不通/API Key 失效
- **处理**:
  1. Sub-agent 调用 MCP 失败 → 捕获异常
  2. 若该 Sub-agent 是**首个**失败的（第 1 轮第 1 次搜索即失败）→ 标记 `failed`，继续执行其他 Sub-agent
  3. 若所有 Sub-agent 均失败 → 返回 `error` SSE 事件，status='failed'（RULE-RES-008）
- **日志**: ERROR 级别，含 MCP 错误详情

---

## EC-RES-003: 计划修改超限

- **场景**: 用户修改计划超过 10 轮
- **处理**: 返回 400 TOO_MANY_REVISIONS
- **日志**: INFO 级别

---

## EC-RES-004: 所有 Sub-agent 全部失败

- **场景**: 所有 Sub-agent 返回 `failed`（MCP 全宕、结果全空等）
- **处理**:
  1. status='failed'
  2. error_message='所有搜索源均未返回有效信息，请检查 MCP Server 状态后重试'
  3. 不生成报告
- **引用**: PRD UC-006 异常流程

---

## EC-RES-005: 并发研究冲突

- **场景**: 用户已有进行中的研究，再次发起新研究
- **处理**: 返回 409 RESEARCH_IN_PROGRESS
- **日志**: INFO 级别

---

## EC-RES-006: 报告超长

- **场景**: 汇总 Agent 生成的报告超过 50,000 字符
- **处理**:
  1. 截断至 50,000 字符
  2. 在截断处插入提示 `...(报告因长度限制已截断)`
  3. 原始完整报告不保存（截断后的为正式版本）
- **引用**: PRD NFR-010

---

## EC-RES-007: 搜索返回 0 结果

- **场景**: MCP 搜索返回空列表（无匹配结果）
- **处理**: 若 `round < 2` → LLM 自动调整搜索词再试；若 `round = 2` 仍无结果 → 输出 `findings = "未找到相关信息"`，标记为 `completed`（非 failed）
- **注意**: "无结果"不等于"失败"——信息不足本身也是研究发现

---

## EC-RES-008: 10 秒内中断且无结果

- **场景**: 用户在点击"确认计划"后 10 秒内点击"停止"，此时无任何 Sub-agent 返回有效数据
- **处理**: status='cancelled'，不生成报告，不调用汇总 Agent
- **引用**: PRD UC-005 异常流程

---

## EC-RES-009: LLM API Rate Limit

- **场景**: 3-5 个 Sub-agent 并行调用 LLM 触发 API 速率限制
- **处理**: LiteLLM 内置指数退避重试（最多 3 次）；若 3 次后仍失败 → 该 Sub-agent 降级为串行延迟执行，按剩余 capacity 逐个排队
- **引用**: feasibility.md R-004 风险

---

## EC-RES-010: 汇总 Agent 收到部分失败数据

- **场景**: 3 个 Sub-agent 中 1 个 failed，2 个 completed
- **处理**: 汇总 Agent 仅聚合 2 个 completed 的结果，报告中标注"共 3 个子课题，其中 1 个子课题（名称）未能完成"
- **status**: `completed`（部分完成仍算完成）

---

## EC-RES-011: SSE 连接中断

- **场景**: 用户在监控过程中网络断开/刷新页面
- **处理**:
  1. 服务端检测到连接关闭（客户端断开）→ 继续执行研究，不终止
  2. 前端重连（EventSource 原生重连机制或手动重连）→ 通过 API-RES-005 拉取最终报告
  3. 若 status='running' → 前端重新建立 SSE 连接继续接收更新

---

## EC-RES-012: 数据库写入失败

- **场景**: 研究执行过程中 PostgreSQL 连接丢失
- **处理**:
  1. 重试 3 次（指数退避）
  2. 若仍失败 → 终止所有 Sub-agent，status='failed', error_message='数据库连接异常'
  3. 已写入数据不回滚（保留部分结果）
