# 模块概述：深度研究核心流程（research）

## 来源
PRD.md §1 概述, §3 UC-003 ~ UC-009, §4 FR-003 ~ FR-021

## 做什么
- 研究计划生成（基于用户选择模板 + 3-5 个 Sub-agent 拆分）
- 研究计划多轮讨论修改（Human-in-the-loop，LangGraph interrupt()）
- Sub-agent 并行执行（MCP 搜索 + ≤4 轮循环 + URL 去重）
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
| 编排框架 | LangGraph StateGraph（全流程统一编排） | tech-decision.md 决策4（V1.1.0 迭代） |
| LLM 集成 | LiteLLM | tech-decision.md 决策5 |
| MCP Client | mcp Python SDK v1.x | tech-decision.md 决策1 + research-report.md 模块1 |
| 搜索源 | Brave Search MCP (Docker) | research-report.md 模块2 |
| 实时推送 | FastAPI StreamingResponse + SSE | tech-decision.md 决策7 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async | tech-decision.md 决策2 |
| Checkpointer | PostgresSaver（复用现有 PostgreSQL） | tech-decision.md 决策4 |
| 前端通信 | REST API + SSE | tech-decision.md 决策3, 决策7 |

## 决策分类（引用调研报告）
| 组件 | 决策 | 说明 |
|---|---|---|
| LiteLLM | ✅ 直接复用 | 统一 LLM 协议 + 成本追踪 |
| mcp Python SDK | ✅ 直接复用 | MCP Client |
| Brave Search MCP | ✅ 直接复用 | Docker 容器，通过 HTTP→MCP 通信 |
| LangGraph | ✅ 已确认（V1.1.0 迁移） | StateGraph 全流程编排 + Send API 并行 + interrupt() human-in-the-loop + PostgresSaver checkpoint |
| URL 去重 | ❌ 自行开发 | Python set/dict 内置 |

## 迭代记录
- **V1.0.0**：纯 asyncio 实现（exec_engine.py），185 测试通过，端到端验证成功
- **V1.1.0（本次迭代）**：迁移到 LangGraph 全流程编排，引入 PostgresSaver checkpoint + interrupt() human-in-the-loop + Send API 并行分发
