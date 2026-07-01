# 边界情况与异常处理

## 来源
PRD 用例异常流程 + 技术判断

---

## EC-FE-001: 网络不可用

- **场景**: 用户断网后操作
- **处理**:
  - API 请求失败 → 展示 toast "网络连接异常，请检查网络后重试"
  - 不自动重试（避免重复提交敏感操作）
  - SSE 断连 → 展示"连接中断"提示，EventSource 自动重连

---

## EC-FE-002: API 返回 5xx

- **场景**: 服务端内部错误
- **处理**:
  - 展示 toast "服务暂时不可用，请稍后重试"
  - 不自动重试
  - 按钮恢复可用状态

---

## EC-FE-003: SSE 事件顺序乱序

- **场景**: 网络延迟导致事件到达顺序不对（如 sub_agent_complete 比 sub_agent_start 先到）
- **处理**:
  - 前端根据每个 `subAgentId` 维护独立状态机，仅接受合法状态转移
  - 非法转移（如 pending → completed 跳过 running）→ 忽略该事件并记录 console.warn

---

## EC-FE-004: 报告页展示时 research 仍为 running

- **场景**: SSE report_complete 事件丢失，用户通过 URL 直接访问报告页
- **处理**:
  - GET `/api/v1/research/{id}` → 若 status != 'completed' → 工作台自动切换到对应视图（如 running→ProgressDashboard），无需页面跳转

---

## EC-FE-005: 修改计划时后端返回 403

- **场景**: 用户尝试修改不属于自己的研究
- **处理**: 展示 "无权操作" 并跳转到 `/dashboard`

---

## EC-FE-006: 长时间无 SSE 事件

- **场景**: 超过 60 秒无任何 SSE 事件（非 heartbeat）
- **处理**:
  - 展示 "执行时间较长，请耐心等待..." 提示
  - 若超 5 分钟仍无事件 → 展示 "研究可能遇到问题，是否终止？"

---

## EC-FE-007: 浏览器不支持 EventSource

- **场景**: 极老浏览器
- **处理**: 降级为轮询模式（每 3 秒 GET 一次状态，但 V1 不做，仅记录）

---

## EC-FE-008: Report Markdown 渲染性能问题

- **场景**: 报告超过 50,000 字符的 Markdown 渲染
- **处理**:
  - 使用 `React.lazy` + `Suspense` 延迟渲染报告 Tab
  - 纯文本 Tab 无需 react-markdown，避免性能问题
  - 后端已截断至 50,000 字符（NFR-010）
