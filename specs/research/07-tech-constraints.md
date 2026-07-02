# 技术约束

## 架构级约束（引用 tech-decision.md）

| 决策 | 引用 |
|---|---|
| 后端语言 | Python 3.12+ | tech-decision.md 决策1 |
| Web 框架 | FastAPI | tech-decision.md 决策1 |
| AI 编排 | LangGraph StateGraph（全流程统一编排） | tech-decision.md 决策4 |
| Checkpointer | PostgresSaver（复用现有 PostgreSQL） | tech-decision.md 决策4 |
| LLM 集成 | LiteLLM (OpenAI 协议兼容) | tech-decision.md 决策5 |
| MCP Client | mcp Python SDK v1.x | tech-decision.md 决策1 |
| 搜索源 | Brave Search MCP (Docker) | research-report.md 模块2 |
| 实时推送 | FastAPI StreamingResponse + SSE | tech-decision.md 决策7 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async | tech-decision.md 决策2 |
| 部署 | Docker Compose | tech-decision.md 决策8 |

## 实现级选型

| 类别 | 包名 | 版本 | 理由 |
|---|---|---|---|
| LLM 统一层 | `litellm` | ^1.x | 100+ 厂商 OpenAI 协议兼容 + 成本追踪 |
| MCP Client | `mcp[cli]` | ^1.28 | 官方 Python SDK |
| Agent 编排 | `langgraph` | ^0.2 | StateGraph + Send API + interrupt + checkpointer |
| Checkpointer | `langgraph-checkpoint-postgres` | ^2.0 | PostgresSaver 持久化 checkpoint |
| 异步 HTTP | `httpx` | ^0.27.0 | Async HTTP client（用于 MCP HTTP 通信） |
| 数据校验 | `pydantic` | ^2.x | FastAPI 内置 |
| 定时任务 | `asyncio` | stdlib | 无需额外库（heartbeat、超时） |

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_MODEL` | 否 | 模型名，默认 `gpt-4o` |
| `LLM_API_BASE` | 否 | API Base URL（默认 OpenAI 官方） |
| `LLM_TIMEOUT` | 否 | LLM 单次调用超时（秒），默认 60 |
| `BRAVE_API_KEY` | 是 | Brave Search API Key |
| `BRAVE_MCP_URL` | 是 | Brave Search MCP 容器地址（如 `http://brave-search:8080/mcp`） |
| `MCP_TIMEOUT` | 否 | MCP 单次调用超时（秒），默认 30 |
| `SUB_AGENT_TIMEOUT` | 否 | Sub-agent 总超时（秒），默认 300 |

## 性能要求

| 指标 | 目标 | 备注 |
|---|---|---|
| 计划生成耗时 | P95 < 15秒 | NFR-001 |
| 完整研究链路 | 5-10 分钟 | NFR-002（取决于并行度和搜索速度） |
| SSE 推送延迟 | < 1 秒 | NFR-003 |
| 单次 Token 基线 | ≤ ¥5 | NFR-011（待 POC-004 验证） |

## LangGraph 架构约束

### StateGraph 结构

```
START
  │
  ▼
plan_generation          ← LLM 生成 3-5 Sub-agent 定义
  │
  ▼
human_review             ← interrupt() 暂停，等待用户操作
  │                       resume with {"action":"confirm"} 或 {"action":"revise","feedback":"..."}
  │
  ▼
route_after_review       ← conditional edge
  │           │
  │ revise    │ confirm
  ▼           ▼
plan_revision    dispatch           ← Send API fan-out: [Send("sub_agent_graph", {agent_def: sa}) for sa in plan]
  │               │
  │               ▼
  │       ┌──────────────────────────────┐
  │       │  Sub-agent Subgraph (×N 并行)  │
  │       │                              │
  │       │  search → dedup → analyze    │
  │       │            ▲         │       │
  │       │            └─ insufficient ──┘
  │       │                      sufficient → END
  │       └──────────────────────┬───────┘
  │                              │
  └──→ human_review (回环)       │
                                 ▼
                         check_cancel       ← conditional edge
                          │         │
                    normal│         │cancelled
                          ▼         ▼
                    aggregate   partial_aggregate
                          │         │
                          ▼         ▼
                         END       END
```

### State 定义

- State 使用 `TypedDict`（非 Pydantic BaseModel，因 LangGraph 要求 TypedDict + Annotated reducer）
- `sub_agent_results` 字段必须声明 `Annotated[list[dict], operator.add]` reducer，确保 Send API 并行结果累加而非覆盖
- `_action` 字段用于 `route_after_review` conditional edge 路由判定

```python
class ResearchState(TypedDict):
    research_id: UUID
    user_id: UUID
    topic: str
    template: str
    plan: list[dict]
    plan_round: int
    feedback: str | None
    _action: str | None            # interrupt resume 值: "confirm" | "revise"
    sub_agent_results: Annotated[list[dict], operator.add]
    cancel_requested: bool
    report_markdown: str
    total_tokens: int
    status: str
    error_message: str | None
```

### SubAgentState 定义（Sub-agent Subgraph 专用）

```python
class SubAgentState(TypedDict):
    research_id: UUID
    topic: str
    agent_def: dict                  # {name, goal, searchDirection}
    search_direction: str            # 当前搜索方向（可能跨轮变化）
    visited_urls: list[str]          # 已访问 URL（去重用）
    findings: str                    # 累积的研究发现
    rounds_completed: int            # 已完成的搜索轮次
    sufficient: bool                 # LLM 判断信息是否充足
    token_used: int                  # 本 Sub-agent 消耗的 token
    status: str                      # pending, running, completed, failed, cancelled
    has_error: bool                  # 是否遇到错误
    search_results: list             # 最近一轮搜索结果（临时字段，不持久化）
```

### Send API 并行分发

- `dispatch_node` 返回 `Send` 列表，StateGraph 自动并行执行所有 Sub-agent Subgraph
- 每个 `Send` 携带独立的 `SubAgentState`（包含 agent_def、research_id、topic）
- Sub-agent Subgraph 编译为独立的 `CompiledGraph`，由 main graph 调用

### interrupt() Human-in-the-loop

- `human_review_node` 调用 `interrupt()` 暂停 graph 执行
- **从 interrupt 恢复**: `graph.ainvoke(Command(resume={...}), config)` — 传入 resume 值指定操作
  - resume 值 `{"action": "confirm"}` → 路由到 dispatch
  - resume 值 `{"action": "revise", "feedback": "..."}` → 路由到 plan_revision
- **崩溃恢复**（非 interrupt 场景）: `graph.ainvoke(None, config)` — 从 checkpoint 恢复继续执行（仅用于 app 重启后恢复 status='running' 的研究）
- `human_review_node` 返回 `{"_action": resume_value["action"], "feedback": resume_value.get("feedback")}`，`_action` 字段用于 `route_after_review` conditional edge
- thread_id = `str(research_id)`，用于 checkpoint 定位

### PostgresSaver Checkpointer

- 使用 `AsyncPostgresSaver`（`from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver`）— 与 app 异步架构一致
- 若当前版本不支持 async，降级为同步 `PostgresSaver` + `run_in_executor` 包装
- 使用 `AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)` 初始化
- 应用启动时调用 `await checkpointer.setup()` 创建 checkpoint 表（`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`）
- 这些表由 PostgresSaver 自管理，不归 Alembic migration
- 与业务表共存在同一个 PostgreSQL 数据库，表名不冲突
- thread_id = `str(research_id)`

### RunnableConfig 注入

- DB session factory 和其他不可序列化的对象通过 `RunnableConfig` 注入，不放入 State（避免 checkpoint 序列化失败）
- 配置方式：
  ```python
  config = {
      "configurable": {
          "thread_id": str(research_id),
          "db_session_factory": db_session_factory,
      }
  }
  ```
- 各 node 函数签名：`async def node(state: ResearchState, config: RunnableConfig) -> dict`

### Hybrid 取消机制

- **持久化层**: `graph.aupdate_state(config, {"cancel_requested": True})` — 写入 checkpoint，崩溃恢复后仍可感知取消
- **实时信号层**: 保留 `asyncio.Event` 模块级信号 — Sub-agent 每轮搜索前检查，实现快速中断（无需等待 graph checkpoint 同步）
- 两者共存：`update_state` 用于持久化，`asyncio.Event` 用于实时

### Checkpoint 清理

- 软删除研究时（RULE-RES-010），同时调用 `checkpointer.adelete_thread(thread_id)` 清理对应的 checkpoint 数据
- 避免用户创建研究后不确认（abandoned draft）导致 checkpoint 永久残留

## 禁止使用

- 禁止在 Sub-agent 循环中使用 `time.sleep()` 阻塞事件循环
- 禁止裸 `try/except` 捕获所有异常（需显式捕获具体异常类型）
- 禁止向 LLM 发送超过 100k token 的上下文
- 禁止在 State 中放入不可序列化的对象（DB session、asyncio.Event 等）——必须通过 RunnableConfig 注入
- 禁止使用 `asyncio.gather()` 替代 Send API（Send API 是 LangGraph 的原生并行分发方式）
