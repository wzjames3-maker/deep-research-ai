# 技术约束

## 架构级约束（引用 tech-decision.md）

| 决策 | 引用 |
|---|---|
| 后端语言 | Python 3.12+ | tech-decision.md 决策1 |
| Web 框架 | FastAPI | tech-decision.md 决策1 |
| AI 编排 | LangGraph（首选）/ asyncio（降级） | tech-decision.md 决策4 |
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
| 异步 HTTP | `httpx` | ^0.27.0 | Async HTTP client（用于 MCP HTTP 通信） |
| 数据校验 | `pydantic` | ^2.x | FastAPI 内置 |
| 定时任务 | `asyncio` | stdlib | 无需额外库（heartbeat、超时） |

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_MODEL` | 否 | 模型名，默认 `gpt-4o` |
| `LLM_API_BASE` | 否 | API Base URL（默认 OpenAI 官方） |
| `BRAVE_API_KEY` | 是 | Brave Search API Key |
| `BRAVE_MCP_URL` | 是 | Brave Search MCP 容器地址（如 `http://brave-search:8080/mcp`） |
| `MCP_TIMEOUT` | 否 | MCP 单次调用超时（秒），默认 30 |
| `SUB_AGENT_TIMEOUT` | 否 | Sub-agent 总超时（秒），默认 180 |

## 性能要求

| 指标 | 目标 | 备注 |
|---|---|---|
| 计划生成耗时 | P95 < 15秒 | NFR-001 |
| 完整研究链路 | 5-10 分钟 | NFR-002（取决于并行度和搜索速度） |
| SSE 推送延迟 | < 1 秒 | NFR-003 |
| 单次 Token 基线 | ≤ ¥5 | NFR-011（待 POC-004 验证） |

## LangGraph 特定约束（若采用）

- LangGraph version ≥ 1.0
- State 定义使用 Pydantic BaseModel
- Checkpointer 使用 `SqliteSaver` 或 `PostgresSaver`（与已有 PostgreSQL 复用）
- Subgraph 模式用于 Sub-agent 并行：每个 Sub-agent 是独立的 CompiledGraph，由主 Graph 通过 `Send` API 分发

## asyncio 降级约束（若降级）

- 使用 `asyncio.TaskGroup`（Python 3.11+）管理并发 Sub-agent
- 使用 `asyncio.wait_for()` 实现超时
- 使用 `asyncio.Queue` 收集 Sub-agent 结果反馈给 SSE

## 禁止使用

- 禁止在 Sub-agent 循环中使用 `time.sleep()` 阻塞事件循环
- 禁止裸 `try/except` 捕获所有异常（需显式捕获具体异常类型）
- 禁止向 LLM 发送超过 100k token 的上下文
