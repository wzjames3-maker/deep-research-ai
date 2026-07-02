# Task 48: 集成测试（端到端 + 崩溃恢复）

## 对应 Spec
- specs/research/06-acceptance.md 全部 AC
- specs/research/05-edge-cases.md EC-RES-013, 014

## 输入文件（Agent 需读取）
- specs/research/06-acceptance.md（全部 AC）
- specs/research/03-api-contract.md（全部 API）
- tests/integration/test_research_flow.py（现有集成测试）
- src/services/research_graph.py
- src/services/checkpointer.py
- docker-compose.yml

## 输出文件
- `tests/integration/test_langgraph_e2e.py`（LangGraph 端到端测试）
- `tests/integration/test_crash_recovery.py`（崩溃恢复测试）
- `docs/integration-report-v1.1.md`（集成验收报告 V1.1.0）

## 前置任务
- Task 46（现有测试已适配）
- Task 47（graph 专项测试已 pass）

## 实现要求

### test_langgraph_e2e.py — 端到端流程

使用真实 PostgresSaver（非 MemorySaver），在 Docker 容器内运行：

```python
# 测试完整流程: 创建 → 修改 → 确认 → SSE → 报告

async def test_full_flow_with_langgraph():
    """Complete research flow using LangGraph orchestration."""
    # 1. POST /new → 验证 201 + plan (3-5 sub-agents)
    # 2. POST /revise → 验证 200 + 更新 plan
    # 3. POST /confirm → 验证 200 + status='running'
    # 4. GET /stream → 收集 SSE 事件
    # 5. 验证 SSE 事件序列: plan_confirm → sub_agent_start → sub_agent_round → sub_agent_complete → report_complete
    # 6. GET /report → 验证 200 + reportMarkdown 非空
    # 7. 验证 totalTokens > 0

async def test_cancel_with_partial_results_e2e():
    """Cancel during execution with partial results."""
    # 1. POST /new + /confirm
    # 2. 等待部分 sub-agent 完成
    # 3. POST /cancel
    # 4. 验证 status='cancelled'
    # 5. GET /report → 验证部分报告

async def test_parallel_sub_agent_execution():
    """Verify sub-agents execute in parallel (not serial)."""
    # 1. POST /new + /confirm
    # 2. 记录 sub_agent_start 事件的时间戳
    # 3. 验证 N 个 sub_agent_start 事件的时间差 < 2s（并行启动）

async def test_all_sub_agents_fail():
    """All sub-agents fail → status='failed', no report."""
    # mock MCP search 失败
    # 验证 status='failed', report=NULL, SSE error 事件
```

### test_crash_recovery.py — 崩溃恢复

```python
async def test_crash_recovery_sub_agent_mid_execution():
    """App crashes during sub-agent execution → recover from checkpoint."""
    # 1. POST /new + /confirm → 等待 sub-agent 执行中
    # 2. 记录当前 checkpoint 状态
    # 3. 模拟崩溃：重启 app 容器（或调用 recover_research）
    # 4. 验证 graph 从 checkpoint 恢复
    # 5. 验证最终生成报告

async def test_crash_recovery_plan_phase():
    """App crashes during plan phase (interrupt) → recover."""
    # 1. POST /new → graph 到 interrupt 暂停
    # 2. 重启 app
    # 3. 验证 graph 仍在 interrupt（可通过 resume 继续）
    # 4. POST /confirm → 正常执行

async def test_cancel_persists_across_crash():
    """Cancel flag persists across crash → recovery routes to partial_aggregate."""
    # 1. POST /new + /confirm → sub-agent 执行中
    # 2. POST /cancel → update_state(cancel_requested=True)
    # 3. 模拟崩溃
    # 4. 恢复 → 验证 partial_aggregate 执行
```

### 集成验收报告

`docs/integration-report-v1.1.md` 应包含:
- 测试环境（Docker Compose, LangGraph, PostgresSaver）
- 测试结果（全部 pass/fail 明细）
- 端到端流程验证记录
- 崩溃恢复验证记录
- 性能数据（与 V1.0.0 asyncio 对比）
- 已知问题

### 运行方式

```bash
# 在 Docker 容器内运行
docker compose --project-name deepresearch exec app python -m pytest tests/integration/ -v

# 端到端手动验证
docker compose --project-name deepresearch exec app python -c "
import asyncio
from tests.integration.test_langgraph_e2e import test_full_flow_with_langgraph
asyncio.run(test_full_flow_with_langgraph())
"
```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 46 现有 185 测试全 pass
- [ ] Task 47 graph 专项测试全 pass
- [ ] Docker Compose 服务全部 healthy
- [ ] PostgresSaver setup() 已执行

### AC 全量验收
- [ ] AC-RES-001 ~ 024: 原有 AC 全部 pass
- [ ] AC-RES-025: checkpoint 恢复 pass
- [ ] AC-RES-026: interrupt → resume 流程 pass
- [ ] AC-RES-027: hybrid 取消机制 pass

### 端到端验证
- [ ] 完整流程: new → revise → confirm → SSE → report → 全链路 pass
- [ ] 崩溃恢复: kill → restart → recover → 完成
- [ ] 并行执行: 3-5 sub-agent 并行（SSE 事件时间戳验证）
- [ ] 取消: cancel → partial report / no report

### 性能验证
- [ ] 完整研究链路耗时 5-10 分钟（NFR-002）
- [ ] SSE 推送延迟 < 1s（NFR-003）
- [ ] 计划生成 P95 < 15s（NFR-001）

### 交付物
- [ ] `docs/integration-report-v1.1.md` 生成
- [ ] 所有测试 pass（185 原有 + 新增 graph 测试 + 集成测试）

### 通过判定
全部 ✅ → 迁移完成，V1.1.0 可交付
