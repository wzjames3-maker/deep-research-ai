# 验收标准

## 来源
REQ-RES-001 ~ 017 + RULE-RES-001 ~ 011 + EC-RES-001 ~ 012

---

## AC-RES-001: 正常发起研究 (REQ-RES-001, RULE-RES-001)

- **Given**: 已登录用户, 无进行中的研究
- **When**: POST `/api/v1/research/new` `{ "topic": "React 19 新特性", "template": "tech_research" }`
- **Then**:
  - [ ] HTTP 201
  - [ ] response.plan.subAgents 数量 ∈ [3, 5]
  - [ ] 每个 subAgent 含 name, goal, searchDirection
  - [ ] 数据库 Research 记录 status='draft', template='tech_research'
  - [ ] plan_json 非空

---

## AC-RES-002: 并发研究被拒绝 (RULE-RES-001, EC-RES-005)

- **Given**: 用户已有 status='running' 的研究
- **When**: 再次 POST `/api/v1/research/new`
- **Then**:
  - [ ] HTTP 409 RESEARCH_IN_PROGRESS

---

## AC-RES-003: 修改计划 (REQ-RES-002)

- **Given**: 已创建 status='draft' 的研究
- **When**: POST `/api/v1/research/{id}/plan/revise` `{ "feedback": "增加一个对比竞品的子任务" }`
- **Then**:
  - [ ] HTTP 200
  - [ ] 返回更新后的 subAgents
  - [ ] planRound 递增
  - [ ] 数据库 ResearchPlanFeedback 新增 1 条记录

---

## AC-RES-004: 修改第 11 次被拒绝 (RULE-RES-003, EC-RES-003)

- **Given**: 已修改 10 轮
- **When**: 第 11 次 POST revise
- **Then**: HTTP 400 TOO_MANY_REVISIONS

---

## AC-RES-005: 确认计划 (REQ-RES-003)

- **Given**: status='draft' 的研究
- **When**: POST `/api/v1/research/{id}/plan/confirm`
- **Then**:
  - [ ] HTTP 200, response.status='running'
  - [ ] response.streamUrl 指向正确的 SSE 端点
  - [ ] 数据库 status='running', started_at 已设置

---

## AC-RES-006: 草稿模式恢复 (REQ-RES-012)

- **Given**: status='draft' 的研究（用户直接关闭页面后回来）
- **When**: GET `/api/v1/research/{id}` 或从历史列表进入
- **Then**:
  - [ ] 展示"草稿"标识
  - [ ] 允许返回到计划修改界面

---

## AC-RES-007: SSE 进度流 (REQ-RES-006)

- **Given**: 已确认的研究开始执行
- **When**: 连接 `GET /api/v1/research/{id}/stream`
- **Then**:
  - [ ] Content-Type = text/event-stream
  - [ ] 收到 `sub_agent_start` 事件（每个 Sub-agent 一个）
  - [ ] 收到 `sub_agent_round` 事件
  - [ ] 收到 `sub_agent_complete` 或 `sub_agent_fail` 事件
  - [ ] 收到 `report_complete` 事件（含完整 Markdown 报告）
  - [ ] 每 15 秒收到 `heartbeat` 事件

---

## AC-RES-008: URL 去重生效 (RULE-RES-006, REQ-RES-014)

- **Given**: Sub-agent 第 1 轮搜索返回 URLs: [A, B, C]
- **When**: 第 2 轮搜索返回 URLs: [B, D, E]
- **Then**: 仅 D, E 作为新结果输入 LLM，B 被去重跳过

---

## AC-RES-009: 4 轮循环硬限制 (RULE-RES-005)

- **Given**: Sub-agent 执行中
- **When**: 完成 4 轮搜索
- **Then**:
  - [ ] 第 5 轮不再发起
  - [ ] SubAgentResult.rounds_completed = 4
  - [ ] 状态变为 completed 并输出 findings

---

## AC-RES-010: 所有 Sub-agent 失败 (EC-RES-004, RULE-RES-008)

- **Given**: 3 个 Sub-agent 全部执行失败
- **When**: 汇总阶段
- **Then**:
  - [ ] Research.status='failed'
  - [ ] error_message='所有搜索源均未返回有效信息...'
  - [ ] report_markdown 为 NULL
  - [ ] SSE 推送 `error` 事件

---

## AC-RES-011: 部分 Sub-agent 失败 (EC-RES-010)

- **Given**: 3 个 Sub-agent，2 个 completed，1 个 failed
- **When**: 汇总阶段
- **Then**:
  - [ ] Research.status='completed'
  - [ ] report_markdown 包含 2 个 completed 的结果
  - [ ] 报告中标注第 3 个子课题未能完成

---

## AC-RES-012: 用户中断 — 10 秒内无结果 (EC-RES-008, RULE-RES-009)

- **Given**: 研究刚确认，无任何 Sub-agent 返回结果
- **When**: 用户在 10 秒内 POST cancel
- **Then**:
  - [ ] status='cancelled'
  - [ ] report_markdown 为 NULL
  - [ ] 不调用汇总 Agent

---

## AC-RES-013: 用户中断 — 已有部分结果 (RULE-RES-009)

- **Given**: 2 个 Sub-agent 已完成，1 个 running
- **When**: 用户 POST cancel
- **Then**:
  - [ ] status='cancelled'
  - [ ] report_markdown 基于已完成的 2 个子结果生成部分报告
  - [ ] 第 3 个 SubAgentResult.status='cancelled'

---

## AC-RES-014: 查看完整报告 (REQ-RES-008)

- **Given**: status='completed' 的研究
- **When**: GET `/api/v1/research/{id}/report`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.reportMarkdown 非空
  - [ ] response.subAgentResults 数组长度 = 原计划 subAgents 数量
  - [ ] 每个 subAgentResult 含 findings 和 visitedUrls

---

## AC-RES-015: 软删除 (RULE-RES-010, REQ-RES-011)

- **Given**: 任意状态的研究
- **When**: DELETE `/api/v1/research/{id}`
- **Then**:
  - [ ] HTTP 200
  - [ ] 数据库 deleted_at 已设置（非 NULL）
  - [ ] 再次 GET /history 不返回该记录
  - [ ] 数据库记录未被物理删除

---

## AC-RES-016: Token 累计统计 (RULE-RES-011, REQ-RES-015)

- **Given**: 研究完成后
- **When**: GET `/api/v1/research/{id}/report`
- **Then**:
  - [ ] totalTokens > 0
  - [ ] totalTokens = SUM(SubAgentResult.token_used)
  - [ ] 可通过 `/api/v1/research/stats/tokens` 汇总查看

---

## AC-RES-017: 研究报告复制 (REQ-RES-017)

- **Given**: 已完成的报告
- **When**: 前端提供复制按钮
- **Then**:
  - [ ] 可复制为纯文本
  - [ ] 可复制为 Markdown 源码

---

## AC-RES-018: 重新研究 (REQ-RES-016)

- **Given**: 已完成的研究
- **When**: 点击"重新研究"
- **Then**:
  - [ ] 跳转到新建页面
  - [ ] topic 预填为原研究主题

---

## AC-RES-019: LLM 计划生成超时 (EC-RES-001)

- **Given**: LLM 响应超时 (>30 秒)
- **When**: POST `/api/v1/research/new`
- **Then**:
  - [ ] HTTP 500 PLAN_GENERATION_FAILED
  - [ ] 数据库 Research status 仍为 'draft'
  - [ ] 用户可立即重试

---

## AC-RES-020: 报告超长截断 (EC-RES-006)

- **Given**: 汇总 Agent 生成报告 52,000 字符
- **When**: 报告写入
- **Then**:
  - [ ] report_markdown 长度 ≤ 50,000 字符
  - [ ] 截断处包含 `...(报告因长度限制已截断)` 提示

---

## AC-RES-021: 数据库写入失败 (EC-RES-012)

- **Given**: 研究执行中，PostgreSQL 断开
- **When**: Sub-agent 尝试写入结果，重试 3 次仍失败
- **Then**:
  - [ ] Research.status = 'failed'
  - [ ] error_message = '数据库连接异常'
  - [ ] 已成功写入的 SubAgentResult 数据保留

---

## AC-RES-022: 获取研究详情 — 草稿阶段 (API-RES-005)

- **Given**: status='draft' 的研究，plan 已有 4 个 Sub-agent
- **When**: GET `/api/v1/research/{id}`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.status = "draft"
  - [ ] response.plan.subAgents.length = 4
  - [ ] response.planRound = 当前修改轮次

---

## AC-RES-023: 获取研究详情 — 执行中 (API-RES-005)

- **Given**: status='running' 的研究，2 个 Sub-agent 已完成
- **When**: GET `/api/v1/research/{id}`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.status = "running"
  - [ ] response.subAgentResults 含 2 条 completed 记录

---

## AC-RES-024: SSE 连接使用 Ticket (API-RES-004 + API-AUTH-006)

- **Given**: 先获取 ticket，再建立 SSE 连接
- **When**: `GET /api/v1/research/{id}/stream?ticket=<valid_ticket>`
- **Then**:
  - [ ] 连接成功，返回 text/event-stream
  - [ ] 30 秒后 ticket 过期 → 用过期 ticket 重连 → 401
- **When**: `GET /api/v1/research/{id}/stream?ticket=<invalid_ticket>`
- **Then**: 返回 401

---

## AC-RES-025: Checkpoint 恢复（EC-RES-013, V1.1.0 新增）

- **Given**: status='running' 的研究，Sub-agent 执行到一半
- **When**: 应用进程崩溃后重启，调用 `graph.ainvoke(None, config)`
- **Then**:
   - [ ] Graph 从 checkpoint 保存的位置恢复执行
   - [ ] 已完成的 Sub-agent 结果不丢失
   - [ ] 正在执行的 Sub-agent 从当前轮次重新开始
   - [ ] 最终生成完整或部分报告

---

## AC-RES-026: Interrupt → Resume 流程（V1.1.0 新增）

- **Given**: 用户 POST /new 创建研究 → graph 运行到 `human_review` interrupt() 暂停
- **When**: 用户 POST /revise，传入 feedback
- **Then**:
   - [ ] `graph.ainvoke(Command(resume={"action":"revise","feedback":...}), config)` 执行
   - [ ] `plan_revision_node` 调用 LLM 修改计划
   - [ ] Graph 回到 `human_review` interrupt() 暂停
   - [ ] API 返回更新后的 plan
- **When**: 用户 POST /confirm
- **Then**:
   - [ ] `graph.ainvoke(Command(resume={"action":"confirm"}), config)` 执行
   - [ ] `dispatch_node` 通过 Send API 并行启动所有 Sub-agent
   - [ ] API 返回 `{status: "running", streamUrl: "..."}`

---

## AC-RES-027: Hybrid 取消机制（RULE-RES-009, V1.1.0 新增）

- **Given**: 研究执行中，3 个 Sub-agent 正在运行
- **When**: 用户 POST /cancel
- **Then**:
   - [ ] `graph.aupdate_state(config, {"cancel_requested": True})` 写入 checkpoint
   - [ ] `asyncio.Event` 实时信号立即通知 Sub-agent
   - [ ] Sub-agent 在当前搜索轮次结束后检查到取消信号 → 退出
   - [ ] `check_cancel` conditional edge 路由到 `partial_aggregate`
   - [ ] 已完成的 Sub-agent 结果保留 → 生成部分报告
   - [ ] 若崩溃恢复后发现 `cancel_requested=True` → 仍路由到 `partial_aggregate`
