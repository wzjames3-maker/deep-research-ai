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
| 基础设施 | `langgraph` + `langgraph-checkpoint-postgres` 已安装 | 🔄 V1.1.0 迭代 |
| 基础设施 | PostgresSaver `setup()` 已执行 | 🔄 V1.1.0 迭代 |

## 后置依赖

| 依赖方模块 | 依赖内容 | 使用方式 |
|---|---|---|
| frontend | Research API 端点 | 调用 API-RES-001 ~ 010（接口不变） |
| frontend | SSE 流端点 | `GET /api/v1/research/{id}/stream`（接口不变） |

## 对外接口

### Graph Node 函数（V1.1.0 新增）

| 接口 | 类型 | 用途 |
|---|---|---|
| `plan_generation_node(state, config) -> dict` | async function | 主 Agent 生成研究计划（LLM 调用 + DB 写入） |
| `human_review_node(state) -> dict` | async function | interrupt() 暂停，等待用户确认/修改 |
| `plan_revision_node(state, config) -> dict` | async function | 基于用户反馈修改计划（LLM 调用 + DB 更新） |
| `dispatch_node(state) -> list[Send]` | async function | Send API fan-out 到 Sub-agent Subgraph |
| `sub_agent_graph` | CompiledGraph | Sub-agent 搜索循环（search → dedup → analyze → conditional） |
| `check_cancel_node(state) -> str` | function | Conditional edge: 路由到 aggregate 或 partial_aggregate |
| `aggregate_node(state, config) -> dict` | async function | 全量报告汇总（LLM 调用 + DB 写入） |
| `partial_aggregate_node(state, config) -> dict` | async function | 部分报告汇总或直接标记 cancelled |
| `compile_research_graph() -> CompiledGraph` | function | 组装所有节点和边，编译 main graph |

### API 层调用接口（V1.1.0 更新）

| 接口 | 类型 | 用途 |
|---|---|---|
| `start_research_graph(...)` → `graph.ainvoke({...}, config)` | async | 运行到 interrupt → 返回 plan（POST /new，同步等待） |
| `resume_research_graph(action='revise')` → `graph.ainvoke(Command(resume={...}), config)` | async | Resume → plan_revision → 回到 interrupt → 返回新 plan（POST /revise，同步等待） |
| `run_research(...)` → `graph.ainvoke(Command(resume={"action":"confirm"}), config)` | async (background) | Resume → dispatch → aggregate（POST /confirm，`asyncio.create_task` 后台执行） |
| `recover_research(...)` → `graph.ainvoke(None, config)` | async (background) | 崩溃恢复：从 checkpoint 恢复（app 启动时调用） |
| `cancel_execution(research_id)` → `graph.aupdate_state(config, {"cancel_requested": True})` + `asyncio.Event.set()` | async | Hybrid 取消：持久化 + 实时信号（POST /cancel） |
| `checkpointer.adelete_thread(thread_id)` | async | 清理 checkpoint 数据（DELETE /{id}） |

### 保留接口

| 接口 | 类型 | 用途 |
|---|---|---|
| `stream_research_progress(research_id, queue)` | FastAPI Route | SSE 端点（不变） |
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
| `checkpoints` | TABLE | langgraph-checkpoint-postgres（自管理） |
| `checkpoint_blobs` | TABLE | langgraph-checkpoint-postgres（自管理） |
| `checkpoint_writes` | TABLE | langgraph-checkpoint-postgres（自管理） |
