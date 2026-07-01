# 开源生态调研报告

## 调研范围

基于 PRD.md 中的功能需求，按 12 个模块分别调研开源方案：

| # | PRD 需求 | 模块 |
|---|---|---|
| 1 | FR-017 | MCP Client/SDK — 后端与 MCP Server 通信 |
| 2 | FR-017 | MCP Search Server — Web 搜索数据源 |
| 3 | FR-003, 004, 007 | AI Agent 编排框架 — 主 Agent 拆分 + Sub-agent 执行 |
| 4 | 通用 | Web 框架 — 后端 API Server |
| 5 | FR-001, 002 | 用户认证与会话管理 |
| 6 | NFR-005 | 数据库 ORM — PostgreSQL 持久化 |
| 7 | 通用 | 前端框架 — SPA 结构化工作台 |
| 8 | FR-008 | SSE / 实时通信 — 执行进度推送 |
| 9 | FR-011 | Markdown 渲染 — 报告展示 |
| 10 | 通用 | CSS / UI 组件库 — 仪表盘 UI |
| 11 | FR-018 | URL 去重 |
| 12 | NFR-007 | Docker / 部署 |

---

## 模块 1：MCP Client/SDK（FR-017）

### 搜索关键词
"mcp python sdk", "model context protocol client", "fastmcp"

### 候选方案

#### 方案 A: mcp（官方 Python SDK）
- GitHub: https://github.com/modelcontextprotocol/python-sdk
- PyPI: `mcp` (v1.28.1 stable)
- Star: 23.5k | Fork: 3.6k | 许可证: MIT
- 最近 commit: 2026-06（非常活跃，周更频率）
- Python ≥ 3.10
- 功能匹配度: ★★★★★ 完整 MCP 协议实现（Client + Server），支持 stdio / SSE / Streamable HTTP
- 代码质量: 生产级，文档详尽，SDK 内置 FastMCP 快速开发模式
- 备注: v2 在 Alpha（2026H2 stable），v1.x 维护模式持续接收安全补丁
- 决策: ✅ 直接复用
- 引入方式: `pip install "mcp[cli]"`

#### 方案 B: mcp（TypeScript SDK）
- GitHub: https://github.com/modelcontextprotocol/typescript-sdk
- 语言不同，不考虑

### 最终决策
**选择 mcp Python SDK v1.x**（`pip install "mcp[cli]"`）
理由：官方 SDK、Python 原生、协议完整覆盖、社区活跃。

---

## 模块 2：MCP Search Server（FR-017 数据源）

### 搜索关键词
"mcp server web search", "brave search mcp", "tavily mcp"

### 候选方案

#### 方案 A: Brave Search MCP Server
- GitHub: https://github.com/brave/brave-search-mcp-server
- Star: 1.2k | Fork: 181 | 许可证: MIT
- 最近 commit: 2026-06（活跃） | 发布 97 个 Release（v2.0.85）
- 语言: TypeScript（通过 npx 或 Docker 运行）
- 功能: Web/News/Video/Image 搜索 + LLM Context（AI 摘要）+ Summarizer
- 部署: `docker run mcp/brave-search` 或 `npx @brave/brave-search-mcp-server`
- API Key: Brave Search API（免费 tier 2,000 query/mo）
- 决策: ✅ 直接复用
- 引入方式: Docker 容器 + MCP HTTP transport

#### 方案 B: Tavily MCP Server
- GitHub: https://github.com/tavily-ai/tavily-mcp
- Star: 2.2k | Fork: 277 | 许可证: MIT
- 语言: JavaScript/TypeScript（npx 运行）
- 功能: Search + Extract + Map + Crawl
- 特色: 提供 Remote MCP 模式（无需本地部署，直接 HTTP + API Key）
- 付费: 免费 1,000 API calls/mo，深度研究需付费 Pro
- 决策: 🔧 适配复用（可作为备用搜索源）
- 引入方式: Remote MCP URL `https://mcp.tavily.com/mcp/`

#### 方案 C: SearXNG（自部署元搜索）
- 非 MCP 原生，需要自写 MCP Server 适配层
- 优点: 免费、隐私、无 API Key、多搜索引擎聚合
- 缺点: 需要自部署 + 维护
- 决策: 📝 参考实现（v1 暂不采用，可作为 v2 降本方案）

### 最终决策
**主选 Brave Search MCP Server**（Docker 部署），**备用 Tavily MCP**（Remote 模式）
理由：Brave 提供 LLM Context 优化输出（`brave_llm_context`），特别适合 Agent 场景。Tavily 的 extract/crawl 可作为深度分析补充。

---

## 模块 3：AI Agent 编排框架（FR-003, 004, 007, 021）

### 搜索关键词
"langgraph multi agent", "crewai", "agent orchestration framework python"

### 候选方案

#### 方案 A: LangGraph
- GitHub: https://github.com/langchain-ai/langgraph
- Star: 36k | Fork: 6k | 许可证: MIT
- 最近 commit: 2026-06（极度活跃，549 个 Release）
- 语言: Python 99.6%
- 核心能力: StateGraph（有向图编排）、Subgraph（天生支持主→子模式）、Human-in-the-loop、Durable execution（断点续传）
- 功能匹配度: ★★★★☆ 天然适配 DAG 编排（主 Agent → N 个 Sub-agent → 汇总），Subgraph 完美切合架构
- 学习成本: 中高（需要理解 State/Tool/Node/Subgraph 概念）
- 生态: LangSmith 可观测性 + LangChain 集成 + Deep Agents（高级封装）
- 引入方式: `pip install langgraph`

#### 方案 B: CrewAI
- GitHub: https://github.com/crewAIInc/crewAI
- Star: 54.5k | Fork: 7.6k | 许可证: MIT
- 最近 commit: 2026-06（活跃，210 个 Release）
- 语言: Python
- 核心能力: Role-based Agent（研究员、分析师等角色）+ Crew（团队）+ YAML 配置
- 功能匹配度: ★★★☆☆ 适合预定义角色的协作模式，但本项目是 主→Sub-agent 的固定拆分流，CrewAI 的"角色定义"抽象可能过重
- 优点: 上手快、YAML 配置直观、社区大
- 缺点: 偏重 role-playing 范式，不适合精确控制的 Plan→Execute→Aggregate 流程
- 决策: 📝 参考实现

#### 方案 C: 纯手写编排（Python asyncio + 自定义 State Machine）
- 功能匹配度: ★★★★★ 完全自定义，零学习成本（框架层面）
- 代码量: 需要自行实现状态管理、重试、超时、错误恢复
- 风险: 重复造轮子，但架构简单（主→并行 Sub-agent→汇总）
- 决策: 📝 参考实现（作为 LangGraph 的降级备选方案）

### 最终决策
**LangGraph 作为首选框架**，但如果 LangGraph 的 StateGraph 抽象过重，**降级为纯手写编排**。
理由：本项目的架构是固定的 DAG（主 Agent → 3-5 Sub-agent 并行 → 汇总 Agent），LangGraph 的 Subgraph 天然支持，且提供 State 管理、Checkpoint、Human-in-the-loop 等生产级能力。但如果开发中觉得 LangGraph 概念负担过重，纯 asyncio 编排足够应对。

---

## 模块 4：Web 框架 — 后端（通用）

### 搜索关键词
"fastapi vs flask vs django", "python async web framework", "sse fastapi"

### 候选方案

#### 方案 A: FastAPI
- GitHub: https://github.com/fastapi/fastapi
- Star: 86k | 许可证: MIT
- Python ≥ 3.8，原生 async/await
- 功能: 自动 OpenAPI docs、Pydantic 验证、SSE/StreamingResponse 原生支持、依赖注入
- 与 MCP SDK 配合: 可通过 ASGI Mount 直接挂载 MCP Server
- 引入方式: `pip install fastapi uvicorn`

#### 方案 B: Flask + Quart（async）
- 不推荐——生态已向 FastAPI 倾斜

#### 方案 C: Django + DRF
- 过重，不适合 Agent 类微服务

### 最终决策
**选择 FastAPI**（`pip install fastapi uvicorn`）
理由：Python async 优先、SSE 原生支持、与 mcp SDK ASGI 挂载兼容、Pydantic 自动校验、社区第一选择。

---

## 模块 5：用户认证（FR-001, 002）

### 搜索关键词
"fastapi jwt auth", "fastapi users", "python oauth2"

### 候选方案

#### 方案 A: FastAPI 内置 OAuth2 + python-jose + passlib + bcrypt
- FastAPI 官方教程推荐，轻量，无额外框架耦合
- 功能: JWT 签发/校验、bcrypt 密码哈希、OAuth2 Bearer 认证
- 引入方式: `pip install python-jose[cryptography] passlib[bcrypt]`
- 决策: ✅ 直接复用

#### 方案 B: FastAPI Users
- GitHub: https://github.com/fastapi-users/fastapi-users
- 功能: 完整用户管理系统（注册/登录/密码重置/邮箱验证）
- 过重，本项目仅需简单的 JWT 账号密码登录
- 决策: ❌ 不必要

### 最终决策
**FastAPI OAuth2 + python-jose + passlib + bcrypt**
理由：需求简单（账号/密码注册/登录/JWT），FastAPI 官方方案足够，无需引入全功能用户管理框架。

---

## 模块 6：数据库 ORM（NFR-005）

### 搜索关键词
"sqlalchemy 2.0 async", "python postgresql orm", "asyncpg"

### 候选方案

#### 方案 A: SQLAlchemy 2.0（async 模式）
- GitHub: https://github.com/sqlalchemy/sqlalchemy
- Star: 11.9k | Fork: 1.7k | 许可证: MIT
- Python 100%，1.2M+ 项目使用
- 2.0 引入原生 async/await（基于 asyncpg 驱动）
- 功能: ORM + Core SQL 双模式、Migration（Alembic）、连接池、声明式模型
- 引入方式: `pip install sqlalchemy[asyncio] asyncpg alembic`

#### 方案 B: Prisma（Python Client）
- Node.js 生态原生，Python 为社区移植，不推荐核心数据层依赖

#### 方案 C: 纯 asyncpg（无 ORM）
- 最轻量，但缺少 Migration 和声明式模型

### 最终决策
**选择 SQLAlchemy 2.0 async + Alembic**（`pip install sqlalchemy[asyncio] asyncpg alembic`）
理由：Python 生态 ORM 标准、2.0 async 模式成熟、Alembic Migration 完善、PostgreSQL 支持最佳。

---

## 模块 7：前端框架（通用）

### 搜索关键词
"react dashboard framework", "vite react typescript"

### 候选方案

#### 方案 A: React 18/19 + TypeScript + Vite
- 生态最丰富，SSE/EventSource 集成成熟
- react-markdown 直接复用
- 引入方式: `npm create vite@latest -- --template react-ts`

#### 方案 B: Next.js
- SSR/SSG 能力，但本项目是纯 SPA（无 SEO 需求），Next.js 引入不必要的复杂度
- 决策: ❌ 不必要

#### 方案 C: Vue 3 / Svelte
- 生态中 react-markdown 等关键库的 React 版本更成熟
- 决策: 📝 备选

### 最终决策
**选择 React 18+ + TypeScript + Vite**
理由：生态最成熟、结构化仪表盘组件选择多、SSE/EventSource 集成简单、react-markdown 直接可用。

---

## 模块 8：SSE / 实时通信（FR-008）

### 搜索关键词
"fastapi sse streaming", "server sent events react", "fastapi event source"

### 候选方案

#### 方案 A: FastAPI StreamingResponse + 原生 SSE
- FastAPI 原生支持 `StreamingResponse` 输出 `text/event-stream`
- 前端: `EventSource` API（浏览器原生，无需 npm 包）
- 优点: 零依赖、单向推送（服务端→客户端）完美匹配 Sub-agent 状态推送场景
- 决策: ✅ 直接复用

#### 方案 B: WebSocket（Socket.IO）
- 适用于双向通信，但本项目只需服务端→客户端推送进度
- 决策: ❌ 过重

### 最终决策
**FastAPI StreamingResponse（SSE）+ 浏览器原生 EventSource**
理由：精确匹配单向推送场景、零额外依赖、POC-001 已验证 Nginx + SSE 可行性。

---

## 模块 9：Markdown 渲染（FR-011）

### 搜索关键词
"react markdown renderer", "react-markdown vs marked"

### 候选方案

#### 方案 A: react-markdown
- GitHub: https://github.com/remarkjs/react-markdown
- Star: 15.8k | Fork: 922 | 许可证: MIT
- React 原生组件、安全（无 XSS）、支持 remark/rehype 插件生态
- 功能: 自定义 Components（覆盖 h1-h6/code/table 等）、GFM 插件（表格/任务列表/删除线）
- 引入方式: `npm install react-markdown remark-gfm`
- 决策: ✅ 直接复用

#### 方案 B: marked + dangerouslySetInnerHTML
- 不安全，不推荐

### 最终决策
**选择 react-markdown + remark-gfm**（`npm install react-markdown remark-gfm`）
理由：React 原生、安全、活跃维护、插件生态丰富。

---

## 模块 10：CSS / UI 组件库（通用）

### 候选方案

#### 方案 A: Tailwind CSS + shadcn/ui
- Tailwind: 实用优先的 CSS 框架
- shadcn/ui: 基于 Radix UI 的 React 组件集合（可复制源码而非 npm 依赖）
- 优点: 组件源码在项目内可定制、适合仪表盘/工作台风格、无障碍支持
- 引入方式: `npm install tailwindcss @tailwindcss/vite`

#### 方案 B: Ant Design
- 组件全但不灵活，定制成本高
- 决策: ❌ 不适合仪表盘精细控制

### 最终决策
**选择 Tailwind CSS + shadcn/ui**
理由：组件质量高、源码可定制、仪表盘风格匹配、社区热度最高。

---

## 模块 11：URL 去重（FR-018）

### 评估

| 需求 | 方案 | 复杂度 |
|---|---|---|
| URL 去重 | Python `set()` / `dict()` 内存去重 | 无额外依赖 |
| URL 规范化 | `urllib.parse` + 标准化规则 | 内置库 |

**决策**: ❌ 自行开发（零行代码量，Python 内置数据结构即可）

---

## 模块 12：Docker / 部署（NFR-007）

### 候选方案

#### Docker Compose
- 单机部署，`docker compose up` 一键启动
- 包含: API Server + Frontend (Nginx 静态文件) + PostgreSQL + Brave Search MCP Container
- 决策: ✅ 直接复用

---

## 调研结论汇总

| PRD 需求 | 决策 | 选定方案 | 引入方式 |
|---|---|---|---|
| FR-017 MCP Client | ✅ 直接复用 | mcp Python SDK v1.x | `pip install "mcp[cli]"` |
| FR-017 搜索源 | ✅ 直接复用 | Brave Search MCP Server | Docker 容器 |
| FR-017 搜索源（备用） | 🔧 适配复用 | Tavily MCP | Remote HTTP |
| FR-003/004/007 编排 | ✅ 直接复用 | LangGraph | `pip install langgraph` |
| FR-003/004/007 编排（降级） | ❌ 自行开发 | 纯 Python asyncio 编排 | 手写 |
| 后端 API | ✅ 直接复用 | FastAPI + Uvicorn | `pip install fastapi uvicorn` |
| FR-001/002 认证 | ✅ 直接复用 | FastAPI OAuth2 + python-jose + passlib + bcrypt | `pip install python-jose[cryptography] passlib[bcrypt]` |
| NFR-005 数据库 | ✅ 直接复用 | SQLAlchemy 2.0 async + Alembic + asyncpg | `pip install sqlalchemy[asyncio] asyncpg alembic` |
| 前端框架 | ✅ 直接复用 | React 18+ + TypeScript + Vite | `npm create vite@latest` |
| FR-008 SSE | ✅ 直接复用 | FastAPI StreamingResponse + EventSource | 框架内置 |
| FR-011 Markdown | ✅ 直接复用 | react-markdown + remark-gfm | `npm install react-markdown remark-gfm` |
| UI 组件 | ✅ 直接复用 | Tailwind CSS + shadcn/ui | `npm install tailwindcss @tailwindcss/vite` |
| FR-018 URL 去重 | ❌ 自行开发 | Python set/dict | 内置 |
| NFR-007 Docker | ✅ 直接复用 | Docker Compose | `docker compose up` |

**复用率**: 12/14 模块采用开源方案直接复用或适配复用，仅 Agent 编排（LangGraph 如不适用则降级手写）和 URL 去重（一行代码）为自行开发。

---

## 对后续环节的影响

- **技术选型（Phase 3.5）**: 调研结论基本锁定了技术栈方向（Python/FastAPI + React + MCP + LangGraph + PostgreSQL），Phase 3.5 仅需最终确认
- **Spec 编写（Phase 4）**: 标记为 ✅ 直接复用 的模块在 Spec 中直接引用库文档，不重复编写
- **任务拆分（Phase 6）**: 复用比例高，多数模块为"集成任务"而非"开发任务"，任务量显著减少
- **POC 验证**: POC-001（SSE）、POC-003（MCP 连通）已在调研阶段确认方案可用性
