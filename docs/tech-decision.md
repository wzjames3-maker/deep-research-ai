# 技术选型决策

## 输入
- PRD.md（冻结版）
- research-report.md（调研结论）
- feasibility.md（风险参考）

---

## 决策项 1：后端语言与框架

### 候选
| 方案 | 优点 | 缺点 | 调研约束 |
|---|---|---|---|
| Python + FastAPI | Async 原生、MCP SDK (Python) 最成熟、LangGraph 原生 Python、LLM 生态最强 | GIL 单核限制、运行时较 Node 重 | MCP SDK、LangGraph 均为 Python first |
| Node.js + Express/Fastify | 生态丰富、前后端统一语言、MCP TS SDK 可用 | LLM 编排生态弱于 Python、LangGraph 无 JS 版 | MCP TS SDK 仅备选 |

### 决策：Python 3.12 + FastAPI
### 理由
1. **调研强约束**：MCP Python SDK（23.5k ★）是最成熟的 MCP 实现，LangGraph 原生 Python，两者直接决定后端语言
2. PRD 性能需求 P99 < 200ms，FastAPI + asyncio 完全满足（生产级已有 Spotify/Netflix 等验证）
3. NFR-009 要求 OpenAI Chat Completion 协议兼容，Python 生态（openai 官方 SDK + LiteLLM 多厂商适配）最完善
### 风险：Python GIL 可能限制并行 Sub-agent 请求
### 缓解：Sub-agent 调用 LLM 为 IO 密集型（网络请求），asyncio 非阻塞；必要时 `ThreadPoolExecutor` 处理 CPU 密集型任务

---

## 决策项 2：数据库

### 候选
| 方案 | 优点 | 缺点 |
|---|---|---|
| PostgreSQL 16 | 强 ACID、JSONB 半结构化、全文搜索 | 运维稍复杂于 SQLite |
| MongoDB | Schema 灵活 | 事务弱、PRD 有用户认证等关系型数据 |

### 决策：PostgreSQL 16
### 理由：用户认证（注册唯一性约束）、研究历史（结构化关系）、软删除（deleted_at 时间戳）、NFR-005 已明确
### 风险：无
### 缓解：无

---

## 决策项 3：前端框架与构建工具

### 候选
| 方案 | 优点 | 缺点 | 调研约束 |
|---|---|---|---|
| React 18+ + TypeScript + Vite | 生态最丰富、SSE 集成成熟、react-markdown 可用 | 包体较大 | react-markdown、shadcn/ui 均为 React first |
| Vue 3 | 轻量、学习曲线低 | react-markdown 等关键库无 Vue 版 | 不满足 |

### 决策：React 18+ + TypeScript + Vite
### 理由
1. **调研强约束**：react-markdown（报告渲染）必须是 React，shadcn/ui（仪表盘 UI）React first
2. Vite 构建速度远超 Webpack，HMR 开发体验好
3. TypeScript 保证类型安全（前/后端共享 API 类型）
### 风险：无
### 缓解：无

---

## 决策项 4：AI Agent 编排

### 候选
| 方案 | 优点 | 缺点 | 调研约束 |
|---|---|---|---|
| LangGraph | Subgraph 天然支持主→子模式、State 管理、Human-in-the-loop、Checkpoint 断点续传 | 学习曲线中高、抽象层可能过重 | 调研推荐首选 |
| 纯 Python asyncio 编排 | 完全自主可控、零框架学习成本 | 自行实现状态管理/重试/超时/错误恢复 | ~~降级备选~~（已废弃） |

### 决策：LangGraph（全流程统一编排）
### 理由
1. 本项目的核心执行模式（主 Agent → 3-5 Sub-agent 并行 → 汇总）天然对应 LangGraph 的 StateGraph + Send API
2. UC-004 多轮讨论修改需要 Human-in-the-loop → LangGraph 的 `interrupt()` 机制直接支持
3. 长期运行研究的崩溃恢复 → LangGraph 的 `PostgresSaver` checkpointer 内置持久化
4. 全流程（Plan → Review → Execute → Aggregate）统一为一个 StateGraph，通过 `interrupt()` 实现同步 API 返回
5. V1 已用纯 asyncio 验证核心链路（185 测试通过、端到端跑通），现正式迁移到 LangGraph
### ~~风险~~：已消除 — asyncio 验证阶段已证明核心链路可行，迁移风险可控
### ~~缓解~~：已执行完毕 — M2 阶段 asyncio 验证已完成
### 迭代记录
- **V1.0.0**：纯 asyncio 实现（exec_engine.py），185 测试通过，端到端验证成功
- **V1.1.0（本次迭代）**：迁移到 LangGraph 全流程编排，引入 PostgresSaver checkpoint + interrupt() human-in-the-loop

---

## 决策项 5：LLM 集成层

### 候选
| 方案 | 优点 | 缺点 |
|---|---|---|
| LiteLLM | 统一 OpenAI 协议接口、支持 100+ 厂商、成本追踪、速率限制内置 | 额外依赖 |
| 纯 openai SDK | 官方支持、无额外抽象 | 绑死 OpenAI，无法切换厂商 |

### 决策：LiteLLM（SDK 模式，嵌入 FastAPI 进程内）
### 理由
1. NFR-009 要求 OpenAI Chat Completion 协议兼容（而非限定 OpenAI），LiteLLM 提供统一协议层
2. POC-004 Token 消耗基线测算 → LiteLLM 内置 `cost` 回调可实时统计 Token 消耗
3. 后续如需切换到 DeepSeek/Claude/Gemini 等厂商，仅需改 MODEL 环境变量
### 风险：LiteLLM 库版本升级可能引入 breaking changes
### 缓解：`requirements.txt` 锁定精确版本号

---

## 决策项 6：用户认证

### 候选
| 方案 | 优点 | 缺点 |
|---|---|---|
| JWT (python-jose + passlib + bcrypt) | 无状态、FastAPI 原生支持、轻量 | Token 无法主动撤销（除非加黑名单） |
| Session + Redis | 可主动撤销、服务端控制 | 需要额外 Redis 依赖 |

### 决策：JWT（python-jose + passlib + bcrypt）
### 理由
1. 无状态架构，Docker 自托管无需额外 Redis
2. FastAPI 的 `OAuth2PasswordBearer` 原生集成
3. PRD UC-002 明确 JWT，O-003 明确 V1 无需邮箱（仅账号+密码注册）
### 风险：JWT 无法主动撤销（登出后 Token 仍有效直到过期）
### 缓解：JWT 有效期 24 小时（rememberMe=true 时 7 天）+ /refresh 接口用于续期；如后续需要立即撤销，加数据库 Token 黑名单表

---

## 决策项 7：实时通信

### 候选
| 方案 | 优点 | 缺点 |
|---|---|---|
| SSE (Server-Sent Events) | 单向推送（服务端→客户端）、浏览器原生 EventSource、HTTP 兼容 | 不支持客户端→服务端推送 |
| WebSocket | 双向通信、低延迟 | 重连逻辑复杂、Nginx 需额外配置 |

### 决策：SSE (FastAPI StreamingResponse + EventSource)
### 理由
1. 本项目的实时通信是单向的（推送 Sub-agent 状态到前端），SSE 精确匹配
2. 浏览器原生支持 `EventSource`，前端零依赖
3. Nginx 反向代理兼容性好（仅需关闭缓冲）
4. POC-001 验证通过
### 风险：Nginx 代理缓冲导致消息延迟累积
### 缓解：Nginx 配置 `proxy_buffering off` + `X-Accel-Buffering: no`

---

## 决策项 8：部署方案

### 候选
| 方案 | 优点 | 缺点 |
|---|---|---|
| Docker Compose | 单机自托管、一键启动、NFR-007 明确要求 | 单点故障、无自动扩缩 |
| K8s | 高可用、自动扩缩 | 运维复杂度高、PRD 用户量过万但非峰值并发 |

### 决策：Docker Compose（包含 API Server + Nginx(Frontend) + PostgreSQL + Brave Search MCP Container）
### 理由
1. NFR-007 明确要求 `docker compose up` 一键启动
2. V1 阶段用户量过万但"深度研究"为非高并发场景（NFR-008 单用户同时最多 1 个）
3. 无硬性 Deadline，后续可按需迁移到 K8s
### 风险：单点故障
### 缓解：PostgreSQL 定期 pg_dump 备份；V1 可接受非高可用

---

## 不采用的决策项（已评估，明确不选）

| 决策项 | 评估结论 | 理由 |
|---|---|---|
| 消息队列 (RabbitMQ/Kafka) | ❌ 不需要 | Sub-agent 并发由 asyncio 处理，无异步任务解耦需求，引入 MQ 反而增加架构复杂度 |
| 缓存 (Redis/Memcached) | ❌ 不需要 | JWT 无状态认证、无热点数据缓存需求、PRD 研究链路为实时生成无需缓存 |
| ORM 选型 | ✅ 已确认 (SQLAlchemy 2.0 async) | 调研已推荐，Python ORM 标准，research-report.md 已决策 |
| 测试框架 | ⏸️ Phase 4 (07-tech-constraints) | pytest（Python 标准），属于实现级选型 |
| CI/CD 工具 | ⏸️ Phase 4 (07-tech-constraints) | 属于实现级选型 |

---

## 调研结论对技术选型的约束

| 调研结论 | 约束的技术决策 | 理由 |
|---|---|---|
| mcp Python SDK v1.x（23.5k ★） | 后端必须用 Python | MCP 协议最成熟的实现是 Python 版本 |
| LangGraph（36k ★） | AI 编排首选 LangGraph | Subgraph 天然匹配主→子 Agent 模式 |
| Brave Search MCP Server | Docker Compose 需包含 Brave MCP 容器 | 搜索源为独立 MCP Server |
| react-markdown（15.8k ★） | 前端必须用 React | React 组件，无法跨框架 |
| SQLAlchemy 2.0 async + PostgreSQL | 数据库层确认 PostgreSQL | Python ORM 标准 |
| LiteLLM | LLM 集成层选兼容方案 | 100+ 厂商 OpenAI 协议兼容 |
| FastAPI (86k ★) | 后端框架确认 FastAPI | Python 生态 API 框架首选 |
| Tailwind CSS + shadcn/ui | 前端 CSS 框架确认 | React first 组件库 |

---

## 技术架构总图

```
┌─────────────────────────────────────────────┐
│                  Docker Compose               │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Nginx    │  │  FastAPI  │  │ PostgreSQL │  │
│  │ (React    │  │  Server   │  │    16      │  │
│  │  SPA +    │◄─┤ LangGraph │──┤  +checkpt  │  │
│  │  反向代理) │  │+ LiteLLM  │  │            │  │
│  └──────────┘  │+ MCP      │  └────────────┘  │
│                │     │     │                  │
│                │   MCP    │                   │
│                │  Client  │                   │
│                └────┬─────┘                   │
│                     │                         │
│  ┌──────────────────▼──────────────────────┐  │
│  │       Brave Search MCP Container        │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │         LLM API (通过 LiteLLM SDK)        │ │
│  │   OpenAI / DeepSeek / Claude / Gemini    │ │
│  └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

各层职责：
- **Nginx**：React SPA 静态文件托管 + `/api/` 反向代理 + SSE 长连接代理
- **FastAPI Server**：Auth API + Research API + SSE 推送 + LangGraph 全流程编排（StateGraph + PostgresSaver）+ LiteLLM SDK + MCP Client
- **PostgreSQL**：用户表 + 研究历史表 + Sub-agent 结果表 + LangGraph checkpoint 表（支持软删除）
- **Brave Search MCP Container**：独立 Docker 容器，通过 HTTP→MCP 协议与 FastAPI 通信
- **LLM API**：通过 LiteLLM SDK 统一接口层调用，可切换多厂商
