# Task 47: Graph 专项测试

## 对应 Spec
- specs/research/06-acceptance.md AC-RES-025, AC-RES-026, AC-RES-027
- specs/research/05-edge-cases.md EC-RES-013, EC-RES-014

## 输入文件（Agent 需读取）
- specs/research/06-acceptance.md AC-RES-025, 026, 027
- specs/research/05-edge-cases.md EC-RES-013, 014
- src/services/research_graph.py（compile_research_graph）
- src/services/checkpointer.py（get_checkpointer）
- tests/unit/test_sub_agent_graph.py（Task 36）
- tests/unit/test_research_graph.py（Task 37）

## 输出文件
- `tests/unit/test_graph_checkpoint.py`（checkpoint 恢复测试）
- `tests/unit/test_graph_interrupt.py`（interrupt + resume 测试）
- `tests/unit/test_graph_cancel.py`（hybrid 取消测试）

## 前置任务
- Task 41（main graph 已编译）
- Task 46（现有测试已适配）

## 实现要求

### test_graph_checkpoint.py

```python
# AC-RES-025: Checkpoint 恢复

async def test_checkpoint_recovery_after_crash():
    """Graph crashed mid-execution → new instance recovers from checkpoint."""
    # 1. 用 MemorySaver 创建 graph
    # 2. invoke 到 dispatch 后（sub-agent 执行中）
    # 3. 模拟崩溃：丢弃 graph 实例
    # 4. 新建 graph 实例（同 checkpointer + thread_id）
    # 5. ainvoke(None, config) → 从 checkpoint 恢复
    # 6. 验证最终状态正确（sub-agent 完成 + 报告生成）

async def test_checkpoint_preserves_completed_sub_agents():
    """Checkpoint preserves completed sub-agent results."""
    # 1. invoke 到 2/3 sub-agent 完成
    # 2. 模拟崩溃
    # 3. 恢复 → 验证已完成的 2 个 sub-agent 结果保留

async def test_checkpoint_recovery_with_cancel():
    """Recovery after crash with cancel_requested=True → partial_aggregate."""
    # 1. invoke 到 sub-agent 执行中
    # 2. update_state(cancel_requested=True)
    # 3. 模拟崩溃
    # 4. 恢复 → 验证路由到 partial_aggregate
```

### test_graph_interrupt.py

```python
# AC-RES-026: Interrupt → Resume 流程

async def test_interrupt_returns_plan():
    """Graph runs to interrupt → returns plan in state."""
    # invoke → 验证 graph 在 human_review 暂停
    # 验证 state 有 plan, plan_round, status='draft'

async def test_resume_with_confirm():
    """Resume with confirm → dispatch → aggregate."""
    # interrupt → Command(resume={"action":"confirm"}) → 验证 dispatch + aggregate

async def test_resume_with_revise():
    """Resume with revise → plan_revision → back to interrupt."""
    # interrupt → Command(resume={"action":"revise","feedback":"..."}) → 验证 plan 变更
    # → 验证 graph 再次在 human_review 暂停

async def test_multiple_revise_rounds():
    """Multiple revise rounds → each returns updated plan."""
    # revise → interrupt → revise → interrupt → confirm → complete

async def test_revise_exceeds_max_rounds():
    """Revise exceeds 10 rounds → error."""
    # 10 次 revise → 第 11 次 → 验证错误处理
```

### test_graph_cancel.py

```python
# AC-RES-027: Hybrid 取消机制

async def test_cancel_sets_asyncio_event():
    """cancel_execution sets asyncio.Event."""
    # cancel_execution(research_id)
    # 验证 cancel_signals[research_id].is_set() == True

async def test_cancel_updates_graph_state():
    """cancel_execution calls graph.aupdate_state."""
    # mock graph.aupdate_state
    # cancel_execution(research_id)
    # 验证 aupdate_state 被调用 with {"cancel_requested": True}

async def test_cancel_routes_to_partial_aggregate():
    """cancel_requested=True → check_cancel routes to partial_aggregate."""
    # 设置 state.cancel_requested=True
    # 验证 check_cancel(state) == "partial_aggregate"

async def test_cancel_with_no_results():
    """Cancel with no completed sub-agents → status='cancelled', no report."""
    # 所有 sub-agent pending → cancel → 验证无报告

async def test_cancel_with_partial_results():
    """Cancel with some completed → partial report."""
    # 2 completed + 1 running → cancel → 验证部分报告

async def test_cancel_persisted_in_checkpoint():
    """Cancel flag persists in checkpoint after crash."""
    # update_state(cancel_requested=True) → 模拟崩溃 → 恢复 → 验证 cancel_requested 仍 True
```

### EC-RES-014: Checkpoint 清理测试

```python
async def test_delete_cleans_checkpoint():
    """DELETE /research/{id} → checkpointer.adelete_thread called."""
    # DELETE 请求 → 验证 adelete_thread 被调用 with str(research_id)

async def test_delete_checkpoint_failure_doesnt_block():
    """Checkpoint cleanup failure doesn't block soft delete."""
    # mock adelete_thread → raise Exception
    # 验证 DELETE 仍返回 200
    # 验证 deleted_at 已设置
```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 41 main graph 已编译
- [ ] Task 46 现有测试已适配

### AC 验收
- [ ] AC-RES-025: checkpoint 恢复测试 pass
- [ ] AC-RES-026: interrupt → resume 流程测试 pass
- [ ] AC-RES-027: hybrid 取消机制测试 pass
- [ ] EC-RES-013: 崩溃恢复测试 pass
- [ ] EC-RES-014: checkpoint 清理测试 pass

### 代码质量
- [ ] 每个测试用例有独立 thread_id
- [ ] 使用 MemorySaver（不依赖 PostgresSaver）
- [ ] Mock 对象在 fixture 中隔离
- [ ] 无测试间状态泄露

### 通过判定
全部 ✅ → 任务 Done，进入 Task 48
