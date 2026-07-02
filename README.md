# DeepResearch Agent — 自动化深度研究智能体

> 将 1-2 小时的研究工作压缩到 5-10 分钟，输出系统化的 Markdown 研究报告。

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

## ✨ 项目简介

DeepResearch Agent 是一个基于 LangGraph 编排的多 Agent 深度研究助手。用户输入研究主题后，主 Agent 自动拆解为 3-5 个子研究方向，各 Sub-agent 并行通过搜索引擎采集信息，最终汇总生成结构化的 Markdown 研究报告。

**核心流程：** 输入主题 → LLM 生成研究计划 → 用户审核/修改（interrupt） → Sub-agent 并行搜索（Send API） → 汇总报告

### V1.1.0 更新（2026-07）

- 🆕 **LangGraph 全流程编排** — 从纯 asyncio 迁移到 LangGraph StateGraph
- 🆕 **PostgresSaver checkpoint** — Graph state 持久化，支持崩溃恢复
- 🆕 **interrupt() Human-in-the-loop** — Plan 阶段原生中断/恢复
- 🆕 **Send API 并行分发** — Sub-agent 原生并行执行
- ✅ 224 测试通过（+39 新增 graph tests）

## 🏗️ 架构

```
┌──────────────────────────────────────────────────┐
│                  Docker Compose                    │
│                                                    │
│  ┌─────────┐   ┌───────────┐   ┌──────────────┐   │
│  │  Nginx   │   │  FastAPI   │   │ PostgreSQL 16│   │
│  │ (React   │◄──┤  Server    ├──┤  + checkpoint│   │
│  │  SPA +   │   │(LangGraph +│   └──────────────┘   │
│  │  反代)   │   │ LiteLLM +  │                      │
│  └─────────┘   │ MCP Client)│                      │
│                └─────┬──────┘                      │
│                      │                             │
│  ┌───────────────────▼──────────────────────┐     │
│  │     Brave Search MCP Container           │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │    LLM API (OpenAI 协议兼容)              │     │
│  │    OpenAI / DeepSeek / Claude / Gemini   │     │
│  └──────────────────────────────────────────┘     │
└──────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 后端
- **Python 3.12 + FastAPI** — 异步 API 框架
- **LangGraph StateGraph** — Agent 全流程编排（Plan → interrupt → Send API → Aggregate）
- **PostgresSaver** — Graph checkpoint 持久化（复用 PostgreSQL）
- **SQLAlchemy 2.0 (async) + Alembic** — ORM 与数据库迁移
- **PostgreSQL 16** — 主数据库 + LangGraph checkpoint 表
- **LiteLLM** — 统一 LLM 接口层，兼容 100+ 厂商
- **MCP Protocol (mcp SDK)** — 搜索源标准化接入
- **python-jose + bcrypt** — JWT 认证 + 密码加密
- **SSE (sse-starlette)** — 实时进度推送
- **structlog** — 结构化日志

### 前端
- **React 19 + TypeScript** — UI 框架
- **Vite 8** — 构建工具
- **Tailwind CSS 4 + shadcn/ui** — 样式与组件库
- **react-markdown + remark-gfm** — Markdown 报告渲染
- **Axios** — HTTP 客户端（含 JWT 自动刷新拦截器）
- **react-router-dom 7** — 路由管理

### 基础设施
- **Docker Compose** — 一键编排（Nginx + App + DB + Brave MCP）
- **Nginx** — SPA 托管 + 反向代理 + SSE 代理

## 🚀 快速开始

### 前置条件

- Docker + Docker Compose
- Brave Search API Key（[免费获取](https://brave.com/search/api/)）
- LLM API Key（OpenAI / DeepSeek / 任何 OpenAI 协议兼容的厂商）

### 部署步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/wzjames3-maker/deep-research-ai.git
   cd deep-research-ai
   ```

2. **配置环境变量**

   ```bash
   cp .env.example .env
   ```

   编辑 `.env`，填写以下必要项：

   | 变量 | 说明 |
   |---|---|
   | `POSTGRES_PASSWORD` | 数据库密码 |
   | `JWT_SECRET` | JWT 签名密钥（≥32 字符，`openssl rand -hex 32` 生成） |
   | `LLM_API_KEY` | LLM 厂商的 API Key |
   | `LLM_API_BASE` | LLM API 地址（默认 OpenAI） |
   | `LLM_MODEL` | 模型名称（如 `gpt-4o`、`deepseek-chat`） |
   | `BRAVE_API_KEY` | Brave Search API Key |

3. **构建前端**

   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. **一键启动**

   ```bash
   docker compose up -d
   ```

5. **访问应用**

   打开 `http://localhost`（端口由 `NGINX_PORT` 控制，默认 80）

### 本地开发

**后端：**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev  # 默认 http://localhost:5173
```

## 📋 核心功能

### 用户认证
- 账号密码注册/登录（bcrypt 加密）
- JWT Token 认证 + 自动刷新
- 连续 5 次登录失败锁定账户 15 分钟
- SSE 流式连接采用 Ticket 认证机制

### 研究流程
- **研究模板**：技术调研 / 竞品分析 / 论文综述 / 自定义
- **计划生成**：主 Agent（LLM）自动拆分为 3-5 个 Sub-agent 研究方向
- **计划修改**：支持多轮对话式修改（最多 10 轮），LangGraph interrupt() 实现
- **并行执行**：LangGraph Send API fan-out，Sub-agent 并行搜索，每个最多 2 轮
- **实时进度**：SSE 推送 8 种事件类型（计划确认、执行状态、结果摘要等）
- **中断恢复**：支持中途停止，保留已完成结果并生成部分报告
- **URL 去重**：跨 Sub-agent 搜索结果自动去重
- **崩溃恢复**：PostgresSaver checkpoint 持久化，服务重启后从断点恢复

### 研究报告
- 三 Tab 视图：研究计划 / Sub-agent 结果 / 汇总报告
- Markdown 渲染 + 引用溯源
- 一键复制报告全文

### 历史管理
- 研究历史列表（按时间倒序）
- 草稿保存与恢复
- 软删除（二次确认）
- Token 消耗统计仪表盘

## 📁 项目结构

```
.
├── src/                        # 后端源码
│   ├── api/                    # API 路由层
│   │   ├── auth/               # 认证模块（注册/登录/刷新）
│   │   └── research/           # 研究模块（计划/执行/报告/历史）
│   ├── models/                 # 数据模型（User, Research, SubAgentResult）
│   ├── repos/                  # 数据访问层
│   ├── services/               # 业务逻辑层
│   │   ├── research_graph.py    # LangGraph 主 Graph 节点
│   │   ├── sub_agent_graph.py   # Sub-agent Subgraph
│   │   ├── graph_state.py       # ResearchState + SubAgentState
│   │   ├── checkpointer.py      # PostgresSaver 单例
│   │   ├── llm_service.py       # LLM 调用（LiteLLM）
│   │   ├── mcp_client.py        # MCP 协议客户端
│   │   ├── exec_engine.py       # Graph 调用包装器（thin wrapper）
│   │   ├── sse_manager.py       # SSE 推送管理
│   │   └── prompts.py           # Agent 提示词模板
│   ├── middleware/             # 中间件（Auth, CORS, RateLimiter）
│   ├── utils/                  # 工具（JWT, bcrypt, logging, ticket_store）
│   ├── config.py               # 配置管理
│   └── main.py                 # 应用入口
├── frontend/                   # 前端源码
│   ├── src/
│   │   ├── api/                # API 客户端
│   │   ├── components/         # UI 组件（Research/, ui/）
│   │   ├── pages/              # 页面（Login, Register, Dashboard, NewResearch, Workbench, History）
│   │   ├── contexts/           # React Context（Auth）
│   │   ├── hooks/              # 自定义 Hooks（useAuth, useSSE）
│   │   └── types/              # TypeScript 类型定义
│   └── vite.config.ts
├── alembic/                    # 数据库迁移
├── tests/                      # 测试
│   ├── test_auth_*.py          # 认证模块测试
│   ├── test_research_*.py      # 研究模块测试
│   ├── unit/                   # Graph 单元测试（39 tests）
│   └── integration/            # 集成测试（52 tests）
├── specs/                      # 施工图纸
│   ├── auth/                   # 认证模块规格
│   ├── research/               # 研究模块规格
│   └── frontend/               # 前端规格
├── tasks/                      # 分阶段任务文档
│   ├── phase-1/                # 基础设施
│   ├── phase-2/                # 认证模块
│   ├── phase-3/                # 研究核心
│   ├── phase-4/                # 研究 API
│   ├── phase-5/                # 前端 UI
│   ├── phase-6/                # 联调上线
│   └── phase-7-lg/             # LangGraph 迁移
├── docs/                       # 项目文档
│   ├── PRD.md                  # 产品需求文档
│   ├── tech-decision.md        # 技术选型决策
│   ├── feasibility.md          # 可行性分析
│   ├── research-report.md      # 调研报告
│   ├── integration-report.md   # 集成验收报告 V1.0.0
│   └── integration-report-v1.1.md # 集成验收报告 V1.1.0
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 后端镜像
├── Dockerfile.nginx            # Nginx 镜像
├── Dockerfile.brave-mcp        # Brave MCP 镜像
├── nginx.conf                  # Nginx 配置
├── requirements.txt            # Python 依赖
├── pytest.ini                  # 测试配置
└── .env.example                # 环境变量模板
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL 连接串 |
| `POSTGRES_USER` | `deepresearch` | 数据库用户 |
| `POSTGRES_PASSWORD` | — | 数据库密码 |
| `POSTGRES_DB` | `deepresearch` | 数据库名 |
| `JWT_SECRET` | — | JWT 签名密钥（≥32 字符） |
| `JWT_EXPIRES_IN` | `86400` | Token 有效期（秒） |
| `JWT_REMEMBER_ME_EXPIRES_IN` | `604800` | 记住我有效期（秒） |
| `BCRYPT_ROUNDS` | `12` | bcrypt 加密轮数 |
| `LLM_API_KEY` | — | LLM API Key |
| `LLM_API_BASE` | `https://api.openai.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `gpt-4o` | 模型名称 |
| `LLM_TIMEOUT` | `30` | LLM 请求超时（秒） |
| `BRAVE_API_KEY` | — | Brave Search API Key |
| `BRAVE_MCP_URL` | `http://brave-mcp:3000` | Brave MCP 服务地址 |
| `MCP_TIMEOUT` | `30` | MCP 请求超时（秒） |
| `SUB_AGENT_TIMEOUT` | `180` | Sub-agent 执行超时（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `APP_PORT` | `8001` | 后端端口 |
| `NGINX_PORT` | `80` | Nginx 端口 |
| `DB_PORT` | `5432` | 数据库端口 |
| `BRAVE_MCP_PORT` | `3000` | Brave MCP 端口 |

## 🧪 测试

```bash
# 运行全部测试（224 tests）
docker compose --project-name deepresearch exec app pytest

# 运行 Graph 单元测试（39 tests）
docker compose --project-name deepresearch exec app pytest tests/unit/

# 运行集成测试（52 tests）
docker compose --project-name deepresearch exec app pytest tests/integration/
```

## 🔧 API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/auth/register` | 用户注册 |
| `POST` | `/api/v1/auth/login` | 用户登录 |
| `GET` | `/api/v1/auth/me` | 获取当前用户信息 |
| `POST` | `/api/v1/auth/refresh` | 刷新 JWT Token |
| `POST` | `/api/v1/auth/ticket` | 签发 SSE Ticket |
| `POST` | `/api/v1/research/new` | 发起新研究 |
| `POST` | `/api/v1/research/{id}/plan/revise` | 修改研究计划 |
| `POST` | `/api/v1/research/{id}/plan/confirm` | 确认计划并开始执行 |
| `GET` | `/api/v1/research/{id}/stream?ticket=` | SSE 实时进度流 |
| `GET` | `/api/v1/research/{id}` | 研究详情 |
| `GET` | `/api/v1/research/{id}/report` | 研究报告 |
| `GET` | `/api/v1/research/history` | 研究历史列表 |
| `POST` | `/api/v1/research/{id}/cancel` | 中断研究 |
| `DELETE` | `/api/v1/research/{id}` | 软删除研究 |
| `GET` | `/api/v1/research/stats/tokens` | Token 消耗统计 |

## 📊 性能指标

| 指标 | 目标 |
|---|---|
| 研究计划生成 | P95 < 15s |
| 完整研究链路 | 5-10 分钟 |
| SSE 推送延迟 | < 1s |
| API 响应时间（非 LLM） | P99 < 200ms |
| 单次研究 Token 成本 | ≤ ¥5 |

## 📝 License

MIT

## 📋 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| **V1.1.0** | 2026-07 | LangGraph 迁移：StateGraph 全流程编排 + PostgresSaver checkpoint + interrupt() + Send API |
| **V1.0.0** | 2026-06 | 初始发布：FastAPI + 纯 asyncio 编排 + Brave MCP + 前端工作台 |

详见 [CHANGELOG.md](CHANGELOG.md)
