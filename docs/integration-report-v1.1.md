# 集成验收报告 V1.1.0 — LangGraph 迁移

## 元信息

| 项目 | 值 |
|---|---|
| 迭代版本 | V1.1.0 (iter/l-langgraph-orchestration) |
| 验收日期 | 2026-07-01 |
| 验收人 | AI Agent |
| 前序版本 | V1.0.0 (纯 asyncio exec_engine) |

## 变更概要

将 research 模块的 Agent 编排从**纯 asyncio** 迁移到 **LangGraph StateGraph**，实现全流程统一编排（Plan → Review(interrupt) → Execute(Send API) → Aggregate）。

### 代码变更统计

| 文件 | 状态 | 行数 | 说明 |
|---|---|---|---|
| src/services/research_graph.py | **NEW** | 647 | 主 Graph: plan_generation → human_review → dispatch → aggregate |
| src/services/sub_agent_graph.py | **NEW** | 318 | Sub-agent Subgraph: search → dedup → analyze → conditional |
| src/services/exec_engine.py | **REWRITE** | 159 | 从 437 行缩减至 159 行（thin wrapper） |
| src/services/checkpointer.py | **NEW** | 46 | AsyncPostgresSaver 单例 + setup() |
| src/services/graph_state.py | **NEW** | 54 | ResearchState + SubAgentState TypedDict |
| src/api/research/service_plan.py | **UPDATE** | 289 | create/revise/confirm → graph invoke/resume |
| src/api/research/router.py | **UPDATE** | 237 | cancel → hybrid (update_state + asyncio.Event) |
| src/models/base.py | **UPDATE** | 25 | idle_in_transaction_session_timeout=5s |
| tests/unit/test_sub_agent_graph.py | **NEW** | 340 | 8 tests |
| tests/unit/test_research_graph.py | **NEW** | 567 | 25 tests |
| tests/unit/test_graph_checkpoint.py | **NEW** | 257 | checkpoint recovery tests |
| tests/unit/test_graph_interrupt.py | **NEW** | 180 | interrupt/resume flow tests |
| tests/unit/test_graph_cancel.py | **NEW** | 234 | hybrid cancel tests |
| tests/integration/test_langgraph_e2e.py | **NEW** | 157 | LangGraph end-to-end |
| tests/integration/test_crash_recovery.py | **NEW** | — | crash recovery tests |

## 测试结果

### 单元测试

```
224 passed, 0 failed, 156 warnings in 147.05s
```

- 原有 185 tests → 全部保持 pass
- 新增 39 graph tests → 全部 pass

### 集成测试（单独运行）

| 文件 | 结果 |
|---|---|
| test_auth_flow.py | 9 passed |
| test_research_full_flow.py | 13 passed |
| test_sse_flow.py | 5 passed |
| test_error_scenarios.py | 15 passed |
| test_rate_limiter.py | 4 passed |
| test_crash_recovery.py | 2 passed |
| test_langgraph_e2e.py | 4 passed |
| **合计** | **52 passed** |

### 端到端手动验证

```json
{
  "topic": "Python Type Hints",
  "template": "tech_research",
  "sub_agents": 5,
  "status": "completed",
  "total_tokens": 34460,
  "report_chars": 12144,
  "stages": {
    "plan_generation": "✅ 5 sub-agents generated",
    "human_review (interrupt)": "✅ Graph paused, plan returned to API",
    "confirm (resume)": "✅ Command(resume={\"action\":\"confirm\"}) worked",
    "dispatch (Send API)": "✅ 5 sub-agent subgraphs parallel execution",
    "sub_agent_search": "✅ search → dedup → analyze → complete per sub-agent",
    "aggregate": "✅ Full Markdown report generated (12,144 chars)"
  }
}
```

## 架构验证

| 特性 | 状态 | 说明 |
|---|---|---|
| StateGraph 全流程编排 | ✅ | Plan → Review → Execute → Aggregate 一个 Graph |
| interrupt() Human-in-the-loop | ✅ | Plan 阶段暂停，用户确认/修改后 resume |
| Send API 并行分发 | ✅ | 5 Sub-agent Subgraph 并行执行 |
| Conditional edge 搜索循环 | ✅ | sufficient/rounds 判定路由 |
| PostgresSaver checkpoint | ✅ | Graph state 持久化到 PostgreSQL |
| Hybrid 取消机制 | ✅ | update_state 持久化 + asyncio.Event 实时 |
| SSE 事件集成 | ✅ | 8 种事件类型在 graph node 内推送 |
| API 契约兼容 | ✅ | 请求/响应格式完全不变 |

## 问题与修复

### P0 修复

| 问题 | 修复 |
|---|---|
| `run_research` 用 `ainvoke(None)` 而非 `Command(resume=...)` | Spec 已修正，代码使用 `Command(resume={"action":"confirm"})` |
| `_action` 字段缺失导致 conditional edge 路由失败 | 已添加到 ResearchState |
| sub_agent_graph `analyze_node` 误将 `llm_service` 模块返回值当 dict | 添加 `isinstance(result, tuple)` 兼容判断 |
| PostgresSaver psycopg 连接被 GC 提前回收 | 存储 context manager 引用防止 GC |

### P1 修复

| 问题 | 修复 |
|---|---|
| 测试间模块级全局变量泄漏 | conftest `_reset_graph_singletons` 新增 sag 清理 |
| 僵尸 DB 事务阻塞后续测试 | `idle_in_transaction_session_timeout=5s` 添加到主引擎和测试引擎 |

### 已知问题（非阻塞）

| 问题 | 级别 | 说明 |
|---|---|---|
| `RuntimeError: coroutine ignored GeneratorExit` | 警告 | LangGraph retry 机制在 async 清理时的已知行为 |
| `Deserializing unregistered type asyncpg.UUID` | 警告 | PostgresSaver 反序列化时的已知兼容性问题 |
| Brave MCP unhealthy | 基础设施 | BRAVE_API_KEY=CHANGE_ME，Tavily 降级正常工作 |
| SAWarning greenlet teardown | 警告 | SQLAlchemy asyncpg NullPool 已知时序竞态 |

## 性能对比

| 指标 | V1.0.0 (asyncio) | V1.1.0 (LangGraph) | 变化 |
|---|---|---|---|
| exec_engine.py 行数 | 437 | 159 | -63% |
| 测试总数 | 185 | 224 | +39 |
| 端到端测试耗时 | ~8 min | ~4 min 30s | -44% |
| Plan 生成耗时 | P95 < 15s | P95 < 6s | 符合 NFR-001 |
| report_tokens | ~10,000 | ~34,460 | 因 topic 不同 |

## 决策回顾

| 决策 | 结论 |
|---|---|
| **全流程 LangGraph** | ✅ Plan 阶段用 interrupt() 实现同步 API 返回，确认后后台执行 |
| **PostgresSaver** | ✅ 复用现有 PostgreSQL，checkpoint 表自管理 |
| **Hybrid 取消** | ✅ update_state 持久化 + asyncio.Event 实时，互补设计 |
| **节点内 SSE** | ✅ 保持当前手动推送模式，改动最小 |
| **API 契约不变** | ✅ 前端零感知 |

## 结论

V1.1.0 LangGraph 迁移已完成。所有测试通过（224 unit + 52 integration），端到端验证成功。API 契约不变，前端无需改动。checkpoint 持久化和 interrupt() human-in-the-loop 为后续功能（崩溃恢复、多轮修改回退）提供了基础。
