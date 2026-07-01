# 依赖关系

## 前置依赖

| 依赖模块 | 依赖内容 | 必须完成 |
|---|---|---|
| auth | `get_current_user()` FastAPI Dependency | ✅ M1 基础设施 |
| auth | `User` ORM Model | ✅ M1 基础设施 |
| 数据库 | `users` 表已创建 | ✅ M1 基础设施 |
| 数据库 | Migration 框架就绪（Alembic） | ✅ M1 基础设施 |
| 基础设施 | PostgreSQL 可用 | ✅ M1 |
| 基础设施 | Brave Search MCP 容器可访问 | ✅ M2 |
| 基础设施 | LLM API Key 可用 | ✅ M2 |

## 后置依赖

| 依赖方模块 | 依赖内容 | 使用方式 |
|---|---|---|
| frontend | Research API 端点 | 调用 API-RES-001 ~ 010 |
| frontend | SSE 流端点 | `GET /api/v1/research/{id}/stream` |

## 对外接口

| 接口 | 类型 | 用途 |
|---|---|---|
| `plan_research(topic, template) -> ResearchPlan` | Python Function | 主 Agent 生成研究计划 |
| `execute_sub_agent(agent_def, research_id) -> SubAgentResult` | Python Function | 单个 Sub-agent 执行 |
| `aggregate_results(results: list[SubAgentResult]) -> str` | Python Function | 汇总 Agent |
| `stream_research_progress(research_id, queue)` | FastAPI Route | SSE 端点 |
| Research ORM Model | SQLAlchemy Model | research 模块自身 + 未来统计模块 |

## 数据库对象

| 对象 | 类型 | 所属模块 |
|---|---|---|
| `researches` | TABLE | research |
| `sub_agent_results` | TABLE | research |
| `research_plan_feedbacks` | TABLE | research |
| `research_template` | ENUM | research |
| `research_status` | ENUM | research |
| `sub_agent_status` | ENUM | research |
