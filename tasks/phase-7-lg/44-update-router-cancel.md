# Task 44: 更新 router.py cancel (update_state) + delete (checkpoint 清理)

## 对应 Spec
- specs/research/03-api-contract.md API-RES-008 (cancel), API-RES-009 (delete)
- specs/research/04-business-rules.md RULE-RES-009, RULE-RES-010

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-008, API-RES-009
- specs/research/04-business-rules.md RULE-RES-009, 010
- src/api/research/router.py（当前实现）
- src/services/exec_engine.py（Task 42: cancel_execution — hybrid 实现）
- src/services/research_graph.py（get_research_graph）
- src/services/checkpointer.py（get_checkpointer）

## 输出文件
- `src/api/research/router.py`（更新 cancel_research + delete_research）

## 前置任务
- Task 42（exec_engine cancel_execution 已改为 hybrid）
- Task 41（graph 已编译）

## 实现要求

### cancel_research（API-RES-008）

当前实现已使用 `cancel_execution()`，Task 42 中 `cancel_execution` 内部已改为 hybrid：
- asyncio.Event 实时信号
- graph.aupdate_state 持久化

**router.py 改动最小** — 只需确保 import 正确：

```python
# 保留现有 import
from src.services.exec_engine import cancel_signals, cancel_execution

# cancel_research 函数体基本不变
# cancel_execution 内部已包含 update_state 调用
# 等待引擎响应逻辑不变（3s 轮询）
```

**需验证的点**:
- `cancel_execution(research_id)` 同时设置 asyncio.Event + update_state
- 等待引擎响应的 3s 轮询逻辑仍然有效（graph 检测到 cancel 后会更新 DB status）
- `cancel_signals.pop(research_id, None)` 清理不变

### delete_research（API-RES-009）

追加 checkpoint 清理：

```python
@router.delete("/{research_id}", response_model=DeleteResponse)
async def delete_research(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    # 现有逻辑不变
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != current_user.id:
        raise ForbiddenError("无权操作该研究")

    research.soft_delete()
    await db.commit()

    # V1.1.0 新增: 清理 LangGraph checkpoint 数据
    try:
        from src.services.checkpointer import get_checkpointer
        checkpointer = get_checkpointer()
        await checkpointer.adelete_thread(str(research_id))
    except Exception as e:
        logger.warning("checkpoint_cleanup_failed", research_id=str(research_id), error=str(e))

    return {"deleted": True}
```

### 不改动的路由
- `create_research` — 已在 Task 43 更新 service_plan
- `revise_plan` — 已在 Task 43 更新 service_plan
- `confirm_plan` — 已在 Task 43 更新 service_plan
- `stream_research` — SSE 端点不变
- `get_research_detail` / `get_report` / `get_history` / `get_token_stats` — 纯 DB 查询，不变

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 42 cancel_execution 已改为 hybrid
- [ ] Task 41 graph 已编译

### 功能验证
- [ ] POST /cancel → asyncio.Event + update_state 同时触发
- [ ] POST /cancel → 3s 内 status 变为 'cancelled'（如有部分结果则生成部分报告）
- [ ] POST /cancel 重复 → 400 INVALID_STATUS
- [ ] DELETE /{id} → 软删除 + checkpoint 清理
- [ ] checkpoint 清理失败不影响软删除（warning log, 不报错）

### 代码质量
- [ ] import 清晰（无未使用的 import）
- [ ] checkpoint 清理有 try/except（不阻塞删除操作）
- [ ] cancel_signals 清理在 finally 中

### 通过判定
全部 ✅ → 任务 Done，进入 Task 45
