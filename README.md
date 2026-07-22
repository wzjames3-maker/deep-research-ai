<div align="center">

# 🔬 DeepResearch Agent

**将 1-2 小时的研究工作压缩到 5-10 分钟**

输入研究主题，AI 自动拆解子方向、并行搜索、汇总生成结构化 Markdown 研究报告。

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## ✨ 核心流程

```
输入主题 → LLM 生成研究计划 → 用户审核/修改（interrupt）
         → Sub-agent 并行搜索（Send API） → 汇总报告
```

### V1.1.0 亮点（2026-07）

- 🆕 **LangGraph 全流程编排** — 从纯 asyncio 迁移到 StateGraph
- 🆕 **PostgresSaver checkpoint** — Graph state 持久化，崩溃恢复
- 🆕 **interrupt() Human-in-the-loop** — Plan 阶段原生中断/恢复
- 🆕 **Send API 并行分发** — Sub-agent 原生并行执行
- ✅ 224 测试通过（+39 新增 graph tests）

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                      Docker Compose                      │
│                                                         │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────┐   │
│  │  Nginx   │   │   FastAPI    │   │ PostgreSQL 16 │   │
│  │ (React   │◄──┤   Server     ├──┤  + checkpoint │   │
│  │  SPA +   │   │ (LangGraph + │   └───────────────┘   │
│  │  反代)   │   │ LiteLLM +    │                       │
│  └──────────┘   │ MCP Client)  │                       │
│                 └──────┬───────┘                       │
│                        │                               │
│  ┌─────────────────────▼─────────────────────────┐     │
│  │        Brave Search MCP Container             │     │
│  └───────────────────────────────────────────────┘     │
│                                                         │
│  ┌───────────────────────────────────────────────┐     │
│  │     LLM API (OpenAI 协议兼容)                 │     │
│  │     OpenAI / DeepSeek / Claude / Gemini       │     │
│  └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + FastAPI + LangGraph StateGraph |
| 持久化 | PostgreSQL 16 + PostgresSaver checkpoint |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| LLM | LiteLLM（兼容 100+ 厂商） |
| 搜索 | MCP Protocol + Brave Search |
| 认证 | JWT (python-jose) + bcrypt |
| 实时 | SSE (sse-starlette) |
| 前端 | React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + shadcn/ui |
| 部署 | Docker Compose + Nginx |

## 🚀 快速开始

### 前置条件

- Docker + Docker Compose
- [Brave Search API Key](https://brave.com/search/api/)（免费）
- LLM API Key（OpenAI / DeepSeek / 任何 OpenAI 协议兼容厂商）

### 部署

```bash
git clone https://github.com/wzjames3-maker/deep-research-ai.git
cd deep-research-ai

cp .env.example .env
# 编辑 .env 填写: POSTGRES_PASSWORD, JWT_SECRET, LLM_API_KEY, BRAVE_API_KEY

cd frontend && npm install && npm run build && cd ..

docker compose up -d
```

打开 `http://localhost` 即可使用。

### 本地开发

```bash
# 后端
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev
```

## 🎯 核心功能

| 模块 | 能力 |
|------|------|
| 研究模板 | 技术调研 / 竞品分析 / 论文综述 / 自定义 |
| 计划生成 | 主 Agent 自动拆分 3-5 个 Sub-agent 方向 |
| 计划修改 | 多轮对话式修改（最多 10 轮），interrupt() 实现 |
| 并行执行 | Send API fan-out，每个 Sub-agent 最多 2 轮搜索 |
| 实时进度 | SSE 推送 8 种事件类型 |
| 中断恢复 | 中途停止保留已完成结果，生成部分报告 |
| 崩溃恢复 | PostgresSaver checkpoint，服务重启后断点续跑 |
| 研究报告 | 三 Tab 视图 + Markdown 渲染 + 引用溯源 |
| 历史管理 | 草稿保存、软删除、Token 消耗统计 |

## 📊 性能指标

| 指标 | 目标 |
|------|------|
| 研究计划生成 | P95 < 15s |
| 完整研究链路 | 5-10 分钟 |
| SSE 推送延迟 | < 1s |
| API 响应（非 LLM） | P99 < 200ms |
| 单次研究 Token 成本 | ≤ ¥5 |

## 🧪 测试

```bash
# 全部测试（224 tests）
docker compose exec app pytest

# Graph 单元测试（39 tests）
docker compose exec app pytest tests/unit/

# 集成测试（52 tests）
docker compose exec app pytest tests/integration/
```

## 📋 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| **V1.1.0** | 2026-07 | LangGraph 迁移：StateGraph + PostgresSaver + interrupt() + Send API |
| **V1.0.0** | 2026-06 | 初始发布：FastAPI + asyncio + Brave MCP + 前端工作台 |

## 📄 License

MIT © [wzjames3-maker](https://github.com/wzjames3-maker)

---

<div align="center">

**让 AI 替你做完深度研究，你只管提问。**

Star ⭐ if this saves your research time!

</div>
