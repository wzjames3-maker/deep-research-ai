# 技术约束

## 架构级约束（引用 tech-decision.md）

| 决策 | 引用 |
|---|---|
| 前端框架 | React 18+ + TypeScript | tech-decision.md 决策3 |
| 构建工具 | Vite 6 | tech-decision.md 决策3 |
| CSS | Tailwind CSS 4 | tech-decision.md 决策3 |
| 实时通信 | EventSource (SSE) | tech-decision.md 决策7 |
| 部署 | Nginx 托管 SPA 静态文件 | tech-decision.md 决策8 |

## 实现级选型

| 类别 | 包名 | 版本 | 理由 |
|---|---|---|---|
| 构建 | `vite` | ^6.x | 极速 HMR |
| React | `react`, `react-dom` | ^18.x | 稳定主线 |
| 路由 | `react-router-dom` | ^7.x | React SPA 路由标准 |
| CSS | `tailwindcss` | ^4.x | 工具类 CSS |
| UI 组件 | shadcn/ui (latest) | — | 基于 Radix UI，复制源码而非 npm |
| Markdown | `react-markdown` | ^10.x | 安全渲染 |
| GFM | `remark-gfm` | ^4.x | 表格/任务列表/删除线 |
| HTTP | `axios` | ^1.x | 拦截器、错误处理 |
| Toast | `sonner` | ^2.x | 轻量 toast |

## 环境变量（Vite）

| 变量 | 必需 | 说明 |
|---|---|---|
| `VITE_API_BASE_URL` | 是 | 后端 API 地址（如 `/api/v1` 或 `http://localhost:8000/api/v1`） |

## 性能要求

- 首屏加载 (LCP): < 2 秒
- 路由切换: < 200ms
- Markdown 渲染 50,000 字符: < 1 秒（React.lazy + Suspense）

## 禁止使用

- 禁止 `dangerouslySetInnerHTML`（react-markdown 已安全）
- 禁止直接在前端存储密码（仅在表单内存中）
- 禁止使用 Class 组件（统一函数组件 + Hooks）
- 禁止 inline style（统一 Tailwind 类名）

## 路由注册顺序约束

> `react-router-dom` 中静态路由必须在动态路由之前注册，否则 `/research/history` 会被 `/research/:id` 捕获（`id = "history"`）。

注册顺序（必须严格遵守）:
```jsx
<Route path="/research/new" element={<NewResearch />} />
<Route path="/research/history" element={<ResearchHistory />} />
<Route path="/research/:id" element={<ResearchWorkspace />} />  // 动态路由必须在最后
```
