# 模块概述：前端工作台（frontend）

## 来源
PRD.md §1 概述, §3 UC-003 ~ UC-009

## 做什么
- 用户注册/登录页面
- 新建研究页面（主题输入 + 模板选择）
- 研究计划展示与多轮修改面板
- 实时进度仪表盘（SSE 消费）
- Markdown 报告查看（含 Tab：计划/子结果/汇总）
- 研究历史列表
- Token 消耗仪表盘

## 不做什么
- ❌ 不做响应式移动端适配（V1 仅桌面 Web 端）
- ❌ 不做 PDF 导出（O-004）
- ❌ 不做团队协作界面

## 技术栈
| 类别 | 选择 | 引用 |
|---|---|---|
| 框架 | React 18+ + TypeScript | tech-decision.md 决策3 |
| 构建 | Vite 6 | research-report.md 模块7 |
| CSS | Tailwind CSS 4 + shadcn/ui | research-report.md 模块10 |
| Markdown | react-markdown + remark-gfm | research-report.md 模块9 |
| 实时通信 | EventSource (浏览器原生 SSE) | tech-decision.md 决策7 |
| HTTP | fetch API / axios | standard |

## 决策分类
| 组件 | 决策 | 说明 |
|---|---|---|
| react-markdown | ✅ 直接复用 | Markdown 报告渲染 |
| shadcn/ui | ✅ 直接复用 | UI 组件库（Card/Tabs/Dialog 等） |
| Tailwind CSS | ✅ 直接复用 | 工具类 CSS 框架 |
| SSE (EventSource) | ✅ 直接复用 | 浏览器原生 API |

## 页面路由

> **设计原则**: 研究主工作台使用**单一路由** `/research/{id}`，根据 `research.status` 自动切换内部视图，避免页面跳转割裂工作台体验。

| 路由 | 页面 | 认证 |
|---|---|---|
| `/login` | 登录页 | 不需要 |
| `/register` | 注册页 | 不需要 |
| `/dashboard` | 仪表盘（新研究入口 + 最近历史 + Token 统计） | 需要 |
| `/research/new` | 新建研究（主题 + 模板选择） | 需要 |
| `/research/{id}` | **研究主工作台**（状态驱动视图切换） | 需要 |
| `/research/history` | 研究历史列表 | 需要 |

### `/research/{id}` 工作台状态映射

> **注意**: `confirmed` 为瞬态（V1 不持久化到数据库），前端仅在 SSE `plan_confirm` 事件中接收到该状态。实际 `GET /api/v1/research/{id}` 不会返回 `confirmed`，但前端仍需处理该状态以支持 SSE 事件驱动视图切换。

```
GET /api/v1/research/{id} → research.status
  ├─ 'draft'     → 渲染 PlanPanel（计划展示 + 聊天修改 + 确认按钮）
  ├─ 'confirmed' → 渲染 PlanPanel（展示已确认计划，等待 SSE 推送状态；注：该状态来自 SSE 事件，非 GET 响应）
  ├─ 'running'   → 渲染 ProgressDashboard（SSE 连接 + Sub-agent 状态卡片）
  ├─ 'completed' → 渲染 ReportView（Tab: 计划 / Sub-agent结果 / 汇总）
  ├─ 'failed'    → 渲染错误提示 + 重试按钮
  └─ 'cancelled' → 渲染部分报告（如有）或 已终止提示
```

**工作流**: 用户在所有阶段看到的是同一个页面 URL，视图丝滑切换：
1. 新建研究 → `POST /new` → 获得 researchId → 跳转 `/research/{id}`
2. `/research/{id}` 首次加载 → `GET /api/v1/research/{id}` → status='draft' → 渲染计划面板
3. 用户修改计划 → 同步等待 → 面板更新 → 点击确认 → status='running' → 渲染进度面板
4. SSE 收到 report_complete → status='completed' → 渲染报告视图
5. 用户刷新页面 → `GET /api/v1/research/{id}` → 根据当前 status 恢复对应视图
