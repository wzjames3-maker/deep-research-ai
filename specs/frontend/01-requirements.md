# 功能需求

## 来源
PRD.md §4 FR-001 ~ FR-021 中前端相关的需求

## 需求清单

| Spec 需求 ID | PRD 来源 | 描述 | 优先级 |
|---|---|---|---|
| REQ-FE-001 | FR-001, FR-002 | 登录/注册页面 | P0 |
| REQ-FE-002 | FR-003, FR-021 | 新建研究表单（主题 + 模板选择） | P0 |
| REQ-FE-003 | FR-004, FR-005, FR-008, FR-010, FR-011 | 研究主工作台（路由 `/research/{id}`，状态驱动视图） | P0 |
| REQ-FE-004 | FR-008 | 实时进度仪表盘（SSE 消费，工作台子视图） | P0 |
| REQ-FE-005 | FR-010, FR-011 | Markdown 报告查看（Tab 切换，工作台子视图） | P0 |
| REQ-FE-006 | FR-012 | 引用溯源（点击跳转原始来源） | P1 |
| REQ-FE-007 | FR-013 | 报告复制（纯文本/Markdown） | P1 |
| REQ-FE-008 | FR-014 | 研究历史列表 | P0 |
| REQ-FE-009 | FR-015 | 历史记录软删除 UI | P1 |
| REQ-FE-010 | FR-019 | Token 消耗仪表盘（在 `/dashboard`） | P1 |
| REQ-FE-011 | FR-009 | 中断研究按钮（工作台内） | P1 |

---

## REQ-FE-001: 登录/注册页面

- **页面**: `/login`, `/register`
- **功能**: 账号 + 密码输入、记住我、表单校验、错误提示、成功后跳 `/dashboard`
- **覆盖**: API-AUTH-001, API-AUTH-002

## REQ-FE-002: 新建研究表单

- **页面**: `/research/new`
- **功能**: 主题输入 + 模板选择 → 调用 API-RES-001 → 跳转 `/research/{id}`
- **覆盖**: API-RES-001

## REQ-FE-003: 研究主工作台

- **页面**: `/research/{id}`（单一路由，状态驱动）
- **Hydration**: 页面加载时调用 `GET /api/v1/research/{id}`，根据 `research.status` 渲染对应子视图：

| status | 子视图 | 说明 |
|---|---|---|
| draft / confirmed | PlanPanel | 计划展示（卡片）+ 聊天修改（多轮对话）+ 确认按钮 |
| running | ProgressDashboard | SSE 连接 + Sub-agent 实时状态卡片 + 停止按钮 |
| completed | ReportView | 3 Tab：研究计划 / Sub-agent 结果 / 研究汇总 |
| failed / cancelled | ErrorView | 错误信息 / 终止提示 + 重试或返回按钮 |

- **视图切换动画**: status 变化时使用 CSS transition（如 fade/slide），保持工作台沉浸感
- **覆盖**: GET /api/v1/research/{id}, API-RES-002, API-RES-003, API-RES-004

## REQ-FE-004: 实时进度仪表盘

- **工作台子视图**: status='running' 时渲染
- **功能**: SSE 连接、Sub-agent 状态卡片（pending/running/completed/failed）、搜索轮次、停止按钮
- **SSE 重连**: EventSource 断线自动重连（重新获取 ticket）
- **覆盖**: API-RES-004, API-AUTH-006, API-RES-008

## REQ-FE-005: Markdown 报告查看

- **工作台子视图**: status='completed' 时渲染
- **功能**: 3 个 Tab（研究计划 / Sub-agent 结果 / 研究汇总），react-markdown 渲染
- **覆盖**: API-RES-006
