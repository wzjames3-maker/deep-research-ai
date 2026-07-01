# 模块概述：深度研究核心流程（research）

## 来源
PRD.md §1 概述, §3 UC-003 ~ UC-009, §4 FR-003 ~ FR-021

## 做什么
- 研究计划生成（基于用户选择模板 + 3-5 个 Sub-agent 拆分）
- 研究计划多轮讨论修改（Human-in-the-loop）
- Sub-agent 并行执行（MCP 搜索 + ≤2 轮循环 + URL 去重）
- 执行进度实时推送（SSE）
- Sub-agent 结果汇总与 Markdown 报告生成
- 研究历史持久化与软删除
- Token 消耗统计

## 不做什么
- ❌ 不做实时新闻/热点追踪
- ❌ 不做 PDF 导出（O-004: V1 仅 Markdown 复制）
- ❌ 不做团队协作/分享
- ❌ 不做自定义模板编辑（V1 使用固定模板枚举）

## 技术栈
| 类别 | 选择 | 引用 |
|---|---|---|
| 编排框架 | LangGraph（首选）/ 纯 asyncio（降级） | tech-decision.md 决策4 |
| LLM 集成 | LiteLLM | tech-decision.md 决策5 |
| MCP Client | mcp Python SDK v1.x | tech-decision.md 决策1 + research-report.md 模块1 |
| 搜索源 | Brave Search MCP (Docker) | research-report.md 模块2 |
| 实时推送 | FastAPI StreamingResponse + SSE | tech-decision.md 决策7 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async | tech-decision.md 决策2 |
| 前端通信 | REST API + SSE | tech-decision.md 决策3, 决策7 |

## 决策分类（引用调研报告）
| 组件 | 决策 | 说明 |
|---|---|---|
| LiteLLM | ✅ 直接复用 | 统一 LLM 协议 + 成本追踪 |
| mcp Python SDK | ✅ 直接复用 | MCP Client |
| Brave Search MCP | ✅ 直接复用 | Docker 容器，通过 HTTP→MCP 通信 |
| LangGraph | ✅ 直接复用（首选） | Subgraph 编排 |
| 纯 asyncio 编排 | ❌ 自行开发（降级备选） | 若 LangGraph 受挫则手写 |
| URL 去重 | ❌ 自行开发 | Python set/dict 内置 |
