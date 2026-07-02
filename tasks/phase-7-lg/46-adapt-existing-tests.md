# Task 46: 现有 185 测试适配 LangGraph

## 对应 Spec
- specs/research/06-acceptance.md 全部 AC（API 契约不变，测试需适配底层实现）

## 输入文件（Agent 需读取）
- tests/conftest.py（fixture 定义）
- tests/unit/test_research_plan.py（plan API 测试）
- tests/unit/test_research_exec.py（执行引擎测试）
- tests/unit/test_research_cancel.py（取消测试）
- tests/integration/test_research_flow.py（集成测试）
- 所有 tests/ 下的测试文件（需全量扫描适配）
- src/services/exec_engine.py（Task 42: 新接口）
- src/api/research/service_plan.py（Task 43: 新实现）

## 输出文件
- `tests/conftest.py`（更新 fixture）
- 各测试文件（适配 graph mock 或使用 MemorySaver）

## 前置任务
- Task 42（exec_engine 已重写）
- Task 43（service_plan 已更新）
- Task 44（router 已更新）

## 实现要求

### 适配策略

核心原则：**API 契约不变 → 大部分 API 层测试不需要改**。需要改的是：
1. 直接调用 `exec_engine` 内部函数的测试
2. 使用 `cancel_signals` / `check_cancelled` 的测试
3. mock `llm_service` 的方式可能需要调整

### conftest.py 更新

```python
# 新增 fixture: graph checkpointer for testing
@pytest_asyncio.fixture(scope="session")
async def test_checkpointer():
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()

# 新增 fixture: compiled graph with MemorySaver
@pytest_asyncio.fixture(scope="session")
async def test_graph(test_checkpointer):
    from src.services.research_graph import compile_research_graph
    return compile_research_graph(checkpointer=test_checkpointer)
```

### 测试适配清单

| 测试文件 | 改动类型 | 说明 |
|---|---|---|
| `test_research_plan.py` | 小改 | mock `start_research_graph` / `resume_research_graph` 代替直接 mock `llm_service.generate_plan` |
| `test_research_exec.py` | **大改** | exec_engine 内部函数变了，需要适配 graph 调用 |
| `test_research_cancel.py` | 中改 | `cancel_execution` 接口不变，但内部多了 `update_state` 调用，需 mock graph |
| `test_research_report.py` | 不改 | 纯 DB 查询 |
| `test_research_history.py` | 不改 | 纯 DB 查询 |
| `test_auth_*.py` | 不改 | auth 模块不受影响 |
| `test_rate_limiter.py` | 不改 | |
| `test_mcp_client.py` | 不改 | |
| `test_llm_service.py` | 不改 | |
| `integration/test_research_flow.py` | 中改 | 可能需要用 MemorySaver 代替 PostgresSaver |

### Mock 策略

对于 API 层测试（FastAPI TestClient）:
- mock `start_research_graph` → 返回固定 plan + research_id
- mock `resume_research_graph` → 返回固定 plan
- mock `run_research` → 不实际执行 graph

对于 graph 单元测试:
- 使用 MemorySaver（不需要 PostgresSaver）
- mock `llm_service` 函数
- mock `MCPSearchClient.search`

### 预期结果
- 原有 185 测试中的 ~150 不需要改（auth, report, history, mcp, llm, rate_limiter 等）
- ~35 测试需要适配（research plan, exec, cancel, integration）
- 适配后全部 185 + 新增测试（Task 36, 37, 47）应全 pass

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 42 exec_engine 已重写
- [ ] Task 43 service_plan 已更新
- [ ] Task 44 router 已更新

### 功能验证
- [ ] `pytest tests/ -q` 全部 pass（0 fail）
- [ ] 原有 185 测试中未改动的 ~150 测试仍 pass
- [ ] 改动的 ~35 测试适配后 pass
- [ ] 无 import error
- [ ] 无 fixture 冲突

### 代码质量
- [ ] conftest.py 新增 fixture 不影响其他测试
- [ ] mock 对象在 fixture 中定义（不泄露）
- [ ] 使用 `monkeypatch` 或 `unittest.mock.patch` 而非全局修改

### 通过判定
全部 ✅ → 任务 Done，进入 Task 47
